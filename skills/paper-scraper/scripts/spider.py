#!/usr/bin/env python3
"""
Academic Paper Spider - Core crawling engine
Integrates Scrapling parser + self-learning experience memory

Usage:
    python spider.py --url "https://arxiv.org/search/?query=llm" --max-pages 10 --output papers.json
"""

import argparse
import asyncio
import json
import os
import random
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

# --- Config paths ---
SKILL_DIR = Path(__file__).parent.parent
CONFIG_FILE = SKILL_DIR / "config" / "sites.json"
LESSONS_FILE = SKILL_DIR / "experiences" / "lessons.md"
PROGRESS_DIR = SKILL_DIR / "experiences" / "progress"
PROGRESS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class Paper:
    title: str = ""
    authors: List[str] = field(default_factory=list)
    abstract: str = ""
    doi: str = ""
    url: str = ""
    pdf_url: str = ""
    year: Optional[int] = None
    venue: str = ""
    citations: Optional[int] = None
    keywords: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CrawlConfig:
    url: str = ""
    max_pages: int = 50
    min_delay: float = 2.0
    max_delay: float = 5.0
    session_type: str = "http"  # http | stealthy | dynamic
    mode: str = "auto"  # auto | search | list | detail
    output: str = "papers.json"
    resume: bool = False
    proxy: Optional[str] = None


# ============================================================================
# Experience Manager (from claude-skills pattern)
# ============================================================================

class ExperienceManager:
    """Self-learning site pattern memory"""

    def __init__(self):
        self.patterns: Dict = self._load()
        self.block_level = 0
        self.consecutive_ok = 0
        self.consecutive_fail = 0
        self.request_count = 0
        self.blocked_at: Optional[int] = None

    def _load(self) -> dict:
        if CONFIG_FILE.exists():
            try:
                return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"_meta": {"version": "1.0", "total_patterns": 0}}

    def _save(self):
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.patterns["_meta"]["last_updated"] = datetime.now().isoformat()
        CONFIG_FILE.write_text(
            json.dumps(self.patterns, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def get_domain(self, url: str) -> str:
        return urlparse(url).netloc

    def get_pattern(self, url: str) -> Optional[dict]:
        domain = self.get_domain(url)
        return self.patterns.get(domain)

    def save_pattern(self, url: str, data: dict):
        domain = self.get_domain(url)
        existing = self.patterns.get(domain, {})
        merged = {**existing, **data, "last_success": datetime.now().isoformat()}
        merged["success_count"] = existing.get("success_count", 0) + 1
        self.patterns[domain] = merged
        self._save()

    def record_failure(self, url: str, error: str):
        domain = self.get_domain(url)
        if domain in self.patterns:
            self.patterns[domain]["fail_count"] = self.patterns[domain].get("fail_count", 0) + 1
            self._save()
        # Log to lessons
        entry = f"\n## [{datetime.now().strftime('%Y-%m-%d')}] {domain}\n**Error**: {error}\n---\n"
        LESSONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        existing = LESSONS_FILE.read_text(encoding="utf-8") if LESSONS_FILE.exists() else "# Lessons Learned\n"
        LESSONS_FILE.write_text(existing + entry, encoding="utf-8")

    # --- Anti-blocking ---
    def get_delay(self, config: CrawlConfig) -> float:
        multipliers = [1, 2, 4, 8, 16]
        m = multipliers[min(self.block_level, 4)]
        return random.uniform(config.min_delay * m, config.max_delay * m)

    def report_success(self):
        self.consecutive_ok += 1
        self.consecutive_fail = 0
        self.request_count += 1
        if self.consecutive_ok >= 5 and self.block_level > 0:
            self.block_level -= 1
            self.consecutive_ok = 0

    def report_failure(self, status_code: Optional[int] = None):
        self.consecutive_fail += 1
        self.consecutive_ok = 0
        if self.blocked_at is None:
            self.blocked_at = self.request_count
        escalate = 2 if status_code in (429, 403) else 1
        self.block_level = min(self.block_level + escalate, 4)

    def should_stop(self) -> bool:
        return self.block_level >= 4


# ============================================================================
# Progress / Resume
# ============================================================================

class ProgressManager:
    def __init__(self, task_id: str):
        self.file = PROGRESS_DIR / f"{task_id}.json"
        self.state = self._load()

    def _load(self) -> dict:
        if self.file.exists():
            try:
                return json.loads(self.file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"completed_urls": [], "current_page": 0, "papers": []}

    def _save(self):
        self.file.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")

    def is_completed(self, url: str) -> bool:
        return url in self.state["completed_urls"]

    def mark_completed(self, url: str, papers: List[dict]):
        self.state["completed_urls"].append(url)
        self.state["papers"].extend(papers)
        self.state["current_page"] += 1
        self._save()

    def get_papers(self) -> List[dict]:
        return self.state.get("papers", [])

    def cleanup(self):
        if self.file.exists():
            self.file.unlink()


# ============================================================================
# Extractors — site-specific paper extraction
# ============================================================================

class PaperExtractor:
    """Extract paper metadata from HTML using Scrapling Selector"""

    @staticmethod
    def from_arxiv(selector) -> List[Paper]:
        """Extract papers from arXiv search results"""
        papers = []
        items = selector.css("li.arxiv-result")
        if not items:
            # Alternative: older arxiv layout
            items = selector.css("dl dt")
            for dt in items:
                p = Paper()
                title_el = dt.css("a[title]")
                if title_el:
                    p.title = title_el[0].text.clean()
                    p.url = urljoin("https://arxiv.org", title_el[0].attrib.get("href", ""))
                dd = dt.next
                if dd and dd.tag == "dd":
                    authors_text = dd.css(".descriptor + .list-inline")
                    if authors_text:
                        p.authors = [a.text.clean() for a in authors_text[0].css("a")]
                    abstract_el = dd.css(".mathjax")
                    if abstract_el:
                        p.abstract = abstract_el[0].text.clean()
                papers.append(p)
            return papers

        for item in items:
            p = Paper()
            title_el = item.css("p.title")
            if title_el:
                p.title = title_el[0].text.clean()
            link = item.css("p.list-title a")
            if link:
                p.url = link[0].attrib.get("href", "")
                # Extract arxiv ID for PDF
                arxiv_id = re.search(r"(\d+\.\d+)", p.url)
                if arxiv_id:
                    p.pdf_url = f"https://arxiv.org/pdf/{arxiv_id.group(1)}"
            authors_el = item.css("p.authors")
            if authors_el:
                p.authors = [a.text.clean() for a in authors_el[0].css("a")]
            abstract_el = item.css("span.abstract-full")
            if abstract_el:
                p.abstract = abstract_el[0].text.clean().rstrip("▽ Less")
            else:
                abstract_short = item.css("span.abstract-short")
                if abstract_short:
                    p.abstract = abstract_short[0].text.clean()
            year_el = item.css("p.is-size-7")
            if year_el:
                year_match = re.search(r"(\d{4})", year_el[0].text)
                if year_match:
                    p.year = int(year_match.group(1))
            papers.append(p)
        return papers

    @staticmethod
    def from_semantic_scholar(selector) -> List[Paper]:
        """Extract from Semantic Scholar search results"""
        papers = []
        items = selector.css("[data-test-id='result-card']")
        for item in items:
            p = Paper()
            title_el = item.css("h2 a")
            if title_el:
                p.title = title_el[0].text.clean()
                href = title_el[0].attrib.get("href", "")
                p.url = urljoin("https://www.semanticscholar.org", href)
            authors_el = item.css("[data-test-id='author-list'] span")
            if authors_el:
                p.authors = [a.text.clean() for a in authors_el]
            abstract_el = item.css("[data-test-id='text-truncator']")
            if abstract_el:
                p.abstract = abstract_el[0].text.clean()
            meta_el = item.css("[data-test-id='paper-meta']")
            if meta_el:
                meta_text = meta_el[0].text
                year_match = re.search(r"(\d{4})", meta_text)
                if year_match:
                    p.year = int(year_match.group(1))
                cite_match = re.search(r"(\d+)\s*Citation", meta_text)
                if cite_match:
                    p.citations = int(cite_match.group(1))
            papers.append(p)
        return papers

    @staticmethod
    def from_google_scholar(selector) -> List[Paper]:
        """Extract from Google Scholar search results"""
        papers = []
        items = selector.css(".gs_r.gs_or.gs_scl")
        for item in items:
            p = Paper()
            title_el = item.css("h3.gs_rt a")
            if title_el:
                p.title = title_el[0].text.clean()
                p.url = title_el[0].attrib.get("href", "")
            else:
                title_span = item.css("h3.gs_rt")
                if title_span:
                    p.title = title_span[0].text.clean()
            authors_el = item.css(".gs_a")
            if authors_el:
                author_text = authors_el[0].text.clean()
                # Format: "Author1, Author2 - Venue, Year - Publisher"
                parts = author_text.split(" - ")
                if parts:
                    p.authors = [a.strip() for a in parts[0].split(",") if a.strip()]
                if len(parts) > 1:
                    venue_year = parts[1]
                    year_match = re.search(r"(\d{4})", venue_year)
                    if year_match:
                        p.year = int(year_match.group(1))
                    p.venue = re.sub(r"\d{4}", "", venue_year).strip(" ,-")
            abstract_el = item.css(".gs_rs")
            if abstract_el:
                p.abstract = abstract_el[0].text.clean()
            cite_el = item.css("a:contains('Cited by')")
            if cite_el:
                cite_text = cite_el[0].text
                cite_match = re.search(r"Cited by (\d+)", cite_text)
                if cite_match:
                    p.citations = int(cite_match.group(1))
            # PDF link
            pdf_el = item.css("a[href*='.pdf']")
            if pdf_el:
                p.pdf_url = pdf_el[0].attrib.get("href", "")
            papers.append(p)
        return papers

    @staticmethod
    def from_generic_list(selector) -> List[Paper]:
        """Generic extraction: try common patterns"""
        papers = []
        # Try common list item patterns
        for container_sel in [".paper-item", ".result-item", ".search-result",
                               "article", ".paper", ".entry", "tr.result",
                               ".citation-list tr", ".docsum-content"]:
            items = selector.css(container_sel)
            if items and len(items) > 1:
                for item in items:
                    p = Paper()
                    # Title: first link or heading
                    for sel in ["h2 a", "h3 a", ".title a", "a.title", ".docsum-title"]:
                        t = item.css(sel)
                        if t:
                            p.title = t[0].text.clean()
                            p.url = t[0].attrib.get("href", "")
                            break
                    if not p.title:
                        h = item.css("h2, h3, h4")
                        if h:
                            p.title = h[0].text.clean()
                    # Authors
                    for sel in [".authors", ".author", ".contributor"]:
                        a = item.css(sel)
                        if a:
                            p.authors = [x.strip() for x in a[0].text.clean().split(",")]
                            break
                    # Abstract
                    for sel in [".abstract", ".description", ".snippet", ".summary"]:
                        ab = item.css(sel)
                        if ab:
                            p.abstract = ab[0].text.clean()
                            break
                    # PDF
                    pdf = item.css("a[href*='.pdf']")
                    if pdf:
                        p.pdf_url = pdf[0].attrib.get("href", "")
                    # Year
                    text = item.text
                    year_match = re.search(r"\b(19|20)\d{2}\b", text)
                    if year_match:
                        p.year = int(year_match.group(0))
                    if p.title:
                        papers.append(p)
                break
        return papers


# ============================================================================
# Site Detector
# ============================================================================

EXTRACTOR_MAP = {
    "arxiv.org": PaperExtractor.from_arxiv,
    "semanticscholar.org": PaperExtractor.from_semantic_scholar,
    "scholar.google": PaperExtractor.from_google_scholar,
}


def detect_extractor(url: str):
    domain = urlparse(url).netloc.lower()
    for pattern, extractor in EXTRACTOR_MAP.items():
        if pattern in domain:
            return extractor
    return PaperExtractor.from_generic_list


def auto_detect_mode(url: str) -> str:
    """Guess if this is a search, list, or detail page"""
    path = urlparse(url).path.lower()
    query = urlparse(url).query.lower()
    if any(k in path + query for k in ["search", "query", "q=", "find", "results"]):
        return "search"
    if any(k in path for k in ["/author", "/list", "/category", "/tag", "/collection"]):
        return "list"
    return "detail"


# ============================================================================
# Core Spider
# ============================================================================

class PaperSpider:
    def __init__(self, config: CrawlConfig):
        self.config = config
        self.experience = ExperienceManager()
        self.progress = ProgressManager(
            re.sub(r"[^\w]", "_", urlparse(config.url).netloc + urlparse(config.url).path)[:60]
        )
        self.papers: List[Paper] = []
        self.visited: set = set()

    def _make_request(self, url: str) -> Optional[str]:
        """Make HTTP request using Scrapling"""
        from scrapling.fetchers import Fetcher, StealthyFetcher

        delay = self.experience.get_delay(self.config)
        time.sleep(delay)

        if self.experience.should_stop():
            print("⛔ Anti-blocking: Too many blocks, stopping.")
            return None

        try:
            if self.config.session_type == "stealthy":
                page = StealthyFetcher.fetch(url, headless=True)
            else:
                page = Fetcher.get(url, impersonate="chrome")

            self.experience.report_success()

            # Save page URL for adaptive
            if isinstance(page, str):
                return page
            return str(page)

        except Exception as e:
            self.experience.report_failure()
            print(f"❌ Request failed: {e}")
            return None

    def _fetch_selector(self, url: str):
        """Fetch and return Scrapling Selector"""
        from scrapling.fetchers import Fetcher, StealthyFetcher
        from scrapling.parser import Selector

        delay = self.experience.get_delay(self.config)
        time.sleep(delay)

        if self.experience.should_stop():
            return None

        try:
            if self.config.session_type == "stealthy":
                page = StealthyFetcher.fetch(url, headless=True)
            elif self.config.session_type == "dynamic":
                from scrapling.fetchers import DynamicFetcher
                page = DynamicFetcher.fetch(url, headless=True, network_idle=True)
            else:
                page = Fetcher.get(url, impersonate="chrome")

            self.experience.report_success()
            return page

        except Exception as e:
            self.experience.report_failure()
            print(f"❌ Fetch failed: {e}")
            return None

    def _find_next_page(self, selector, current_url: str) -> Optional[str]:
        """Find next page URL"""
        # Common next-page patterns
        for sel in ["a.next", "a[rel='next']", ".pagination .next a",
                     "li.next a", "a:contains('Next')", "a:contains('下一页')",
                     "a[aria-label='Next']", "a[aria-label='Go to next page']"]:
            els = selector.css(sel)
            if els:
                href = els[0].attrib.get("href", "")
                if href:
                    return urljoin(current_url, href)

        # Try page number increment
        parsed = urlparse(current_url)
        query = parsed.query
        page_match = re.search(r"page=(\d+)", query)
        if page_match:
            next_page = int(page_match.group(1)) + 1
            return current_url.replace(f"page={page_match.group(1)}", f"page={next_page}")

        # offset-based
        offset_match = re.search(r"start=(\d+)", query)
        if offset_match:
            next_offset = int(offset_match.group(1)) + 25
            return current_url.replace(f"start={offset_match.group(1)}", f"start={str(next_offset)}")

        return None

    def crawl(self) -> List[Paper]:
        """Main crawl loop"""
        url = self.config.url
        mode = self.config.mode
        if mode == "auto":
            mode = auto_detect_mode(url)

        pattern = self.experience.get_pattern(url)
        if pattern:
            print(f"✅ Found learned pattern for {self.experience.get_domain(url)}")

        page_num = 0
        current_url = url

        while current_url and page_num < self.config.max_pages:
            if current_url in self.visited:
                break
            if self.progress.is_completed(current_url):
                print(f"⏭️  Skipping (completed): {current_url}")
                # Find next page from saved data
                page_num += 1
                selector = self._fetch_selector(current_url)
                if selector:
                    current_url = self._find_next_page(selector, current_url)
                continue

            self.visited.add(current_url)
            print(f"📄 Page {page_num + 1}: {current_url}")

            selector = self._fetch_selector(current_url)
            if selector is None:
                break

            # Extract papers
            extractor = detect_extractor(current_url)
            page_papers = extractor(selector)

            # Make URLs absolute
            for p in page_papers:
                if p.url and not p.url.startswith("http"):
                    p.url = urljoin(current_url, p.url)
                if p.pdf_url and not p.pdf_url.startswith("http"):
                    p.pdf_url = urljoin(current_url, p.pdf_url)

            print(f"   Found {len(page_papers)} papers")
            self.papers.extend(page_papers)

            # Save progress
            self.progress.mark_completed(current_url, [p.to_dict() for p in page_papers])

            # Save learned pattern
            if page_papers:
                self.experience.save_pattern(url, {
                    "extractor": extractor.__name__,
                    "mode": mode,
                    "session_type": self.config.session_type,
                    "selectors_hint": "auto-detected",
                })

            # Next page
            if mode in ("search", "list"):
                current_url = self._find_next_page(selector, current_url)
            else:
                current_url = None  # detail mode: single page

            page_num += 1

        return self.papers

    def save_output(self, papers: List[Paper]):
        """Save papers to output file"""
        output = {
            "papers": [p.to_dict() for p in papers],
            "meta": {
                "source_url": self.config.url,
                "crawled_at": datetime.now().isoformat(),
                "pages_crawled": len(self.visited),
                "total_papers": len(papers),
            }
        }
        out_path = Path(self.config.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if out_path.suffix == ".jsonl":
            with open(out_path, "w", encoding="utf-8") as f:
                for p in papers:
                    f.write(json.dumps(p.to_dict(), ensure_ascii=False) + "\n")
        else:
            out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

        print(f"💾 Saved {len(papers)} papers → {out_path}")

    def cleanup(self):
        self.progress.cleanup()


# ============================================================================
# Async Spider (using Scrapling's Spider framework)
# ============================================================================

def create_scrapling_spider(url: str, max_pages: int, output: str):
    """Create a Scrapling Spider class dynamically for advanced crawling"""
    from scrapling.spiders import Spider, Request, Response

    class PaperCrawler(Spider):
        name = "paper_crawler"
        start_urls = [url]
        concurrent_requests = 2
        download_delay = 2.0

        def __init__(self):
            super().__init__()
            self.page_count = 0
            self.max = max_pages

        async def parse(self, response: Response):
            extractor = detect_extractor(response.url)
            papers = extractor(response)

            for p in papers:
                if p.url and not p.url.startswith("http"):
                    p.url = response.urljoin(p.url)
                if p.pdf_url and not p.pdf_url.startswith("http"):
                    p.pdf_url = response.urljoin(p.pdf_url)
                yield p.to_dict()

            self.page_count += 1
            if self.page_count < self.max:
                next_url = PaperSpider._find_next_page_static(response, response.url)
                if next_url:
                    yield Request(next_url, callback=self.parse)

    return PaperCrawler


# ============================================================================
# CLI Entry Point
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Academic Paper Scraper")
    parser.add_argument("--url", required=True, help="Start URL")
    parser.add_argument("--max-pages", type=int, default=50)
    parser.add_argument("--min-delay", type=float, default=2.0)
    parser.add_argument("--max-delay", type=float, default=5.0)
    parser.add_argument("--session-type", choices=["http", "stealthy", "dynamic"], default="http")
    parser.add_argument("--mode", choices=["auto", "search", "list", "detail"], default="auto")
    parser.add_argument("--output", default="papers.json")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--proxy", default=None)

    args = parser.parse_args()

    config = CrawlConfig(
        url=args.url,
        max_pages=args.max_pages,
        min_delay=args.min_delay,
        max_delay=args.max_delay,
        session_type=args.session_type,
        mode=args.mode,
        output=args.output,
        resume=args.resume,
        proxy=args.proxy,
    )

    spider = PaperSpider(config)

    print(f"\n🕷️  Paper Spider starting: {args.url}")
    print(f"   Mode: {config.mode} | Session: {config.session_type}")
    print(f"   Max pages: {config.max_pages} | Delay: {config.min_delay}-{config.max_delay}s")
    print()

    papers = spider.crawl()
    spider.save_output(papers)

    print(f"\n✅ Done: {len(papers)} papers extracted from {len(spider.visited)} pages")

    # Cleanup progress on success
    if papers:
        spider.cleanup()


if __name__ == "__main__":
    main()
