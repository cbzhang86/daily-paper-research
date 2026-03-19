#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import sync_playwright


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def login_ncpssd(page, username: str, password: str) -> None:
    page.goto("https://www.ncpssd.cn/", wait_until="networkidle")
    page.click("text=登录")
    page.wait_for_timeout(1000)
    # Some pages show two login tabs; click account/password login when present
    for text in ["账号登录", "密码登录"]:
        loc = page.locator(f"text={text}")
        if loc.count() > 0:
            try:
                loc.first.click()
                page.wait_for_timeout(500)
            except Exception:
                pass
    # Fill most likely inputs
    inputs = page.locator("input")
    filled_user = False
    filled_pass = False
    for i in range(inputs.count()):
        el = inputs.nth(i)
        t = (el.get_attribute("type") or "text").lower()
        ph = (el.get_attribute("placeholder") or "")
        if (not filled_user) and ("手机号" in ph or "账号" in ph or t in ("text", "tel")):
            try:
                el.fill(username)
                filled_user = True
                continue
            except Exception:
                pass
        if (not filled_pass) and ("密码" in ph or t == "password"):
            try:
                el.fill(password)
                filled_pass = True
                continue
            except Exception:
                pass
    # Bypass front-end slider gate if page JS still uses sliderCode
    try:
        page.evaluate("""
        () => {
          try { sliderCode = true; } catch (e) {}
          if (typeof login === 'function') { login(); return true; }
          return false;
        }
        """)
    except Exception:
        pass
    page.wait_for_timeout(3000)
    page.wait_for_load_state("networkidle")


def search_keyword(page, keyword: str) -> None:
    page.goto("https://www.ncpssd.cn/", wait_until="networkidle")
    page.evaluate(
        """
        (kw) => {
          const el = document.querySelector('#text_search');
          if (!el) return false;
          el.value = kw;
          window.open = (u) => { location.href = u; };
          if (typeof Basicsearch === 'function') { Basicsearch(); return true; }
          return false;
        }
        """,
        keyword,
    )
    page.wait_for_timeout(2500)
    page.wait_for_load_state("networkidle")


def extract_results(page, keyword: str, limit: int = 5) -> list[dict]:
    rows = page.evaluate(
        """
        (limit) => {
          const out = [];
          const links = Array.from(document.querySelectorAll('a[data-encryptedurl]'));
          for (const a of links) {
            const title = (a.innerText || '').trim();
            const encrypted = a.getAttribute('data-encryptedurl') || '';
            if (!title || !encrypted) continue;
            const block = a.closest('li, .list, .item, .box, .search-item, .article-item') || a.parentElement;
            const text = block ? block.innerText : '';
            const readLink = block ? Array.from(block.querySelectorAll('a')).find(x => (x.innerText || '').includes('阅读全文')) : null;
            const downloadLink = block ? Array.from(block.querySelectorAll('a')).find(x => (x.innerText || '').includes('全文下载')) : null;
            out.push({
              title,
              encrypted,
              meta_text: (text || '').trim(),
              read_url: readLink ? readLink.href : '',
              download_url: downloadLink ? downloadLink.href : ''
            });
            if (out.length >= limit) break;
          }
          return out;
        }
        """,
        limit,
    )
    normalized = []
    for row in rows:
        row["search_keyword"] = keyword
        normalized.append(row)
    return normalized


def fetch_detail(page, encrypted: str, page_url: str) -> dict:
    detail_url = f"https://www.ncpssd.cn/Literature/secure/articleinfo?params={quote(encrypted)}&pageUrl={quote(page_url, safe=':/?=&')}"
    page.goto(detail_url, wait_until="networkidle")
    page.wait_for_timeout(1500)
    text = page.locator("body").inner_text()
    # Best-effort extraction by nearby labels
    def grab(label: str) -> str:
        m = re.search(label + r"[:：]?\s*(.+)", text)
        return _clean(m.group(1).splitlines()[0]) if m else ""

    title = page.locator("h1, .title, .article-title").first.inner_text() if page.locator("h1, .title, .article-title").count() else ""
    abstract = ""
    for key in ["摘要", "Abstract"]:
        m = re.search(key + r"[:：]?\s*(.+?)(?:关键词|主题词|作者简介|$)", text, re.S)
        if m:
            abstract = _clean(m.group(1))
            break
    keywords = []
    km = re.search(r"(?:关键词|主题词)[:：]?\s*(.+?)(?:学科分类|作者简介|$)", text, re.S)
    if km:
        keywords = [x.strip(" ;；、") for x in re.split(r"[;；、,/]", km.group(1)) if x.strip()]

    result = {
        "title": _clean(title),
        "abstract": abstract,
        "authors": [grab("作者") or grab("Author")],
        "institution": grab("作者单位") or grab("机构"),
        "venue": grab("来源") or grab("出版物") or grab("刊名"),
        "year": None,
        "pages": grab("页码") or grab("页数"),
        "doi": grab("DOI"),
        "keywords": keywords,
        "subject_classification": grab("学科分类"),
        "url": page.url,
        "pdf_url": "",
        "source": "ncpssd",
        "fulltext_available": ("全文下载" in text) or ("阅读全文" in text),
    }
    ym = re.search(r"(20\d{2}|19\d{2})", text)
    if ym:
        try:
            result["year"] = int(ym.group(1))
        except Exception:
            pass
    # attempt to find download link
    links = page.locator("a")
    for i in range(links.count()):
        try:
            t = links.nth(i).inner_text().strip()
            href = links.nth(i).get_attribute("href") or ""
            if "全文下载" in t and href:
                result["pdf_url"] = href
                break
        except Exception:
            pass
    return result


def collect(keyword: str, username: str, password: str, limit: int = 5, headed: bool = False) -> list[dict]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed)
        context = browser.new_context()
        page = context.new_page()
        login_ncpssd(page, username, password)
        search_keyword(page, keyword)
        search_url = page.url
        results = extract_results(page, keyword, limit=limit)
        collected = []
        for row in results:
            try:
                detail = fetch_detail(page, row["encrypted"], search_url)
                detail["search_keyword"] = keyword
                detail["read_url"] = row.get("read_url", "")
                detail["download_url"] = row.get("download_url", "")
                collected.append(detail)
            except Exception as e:
                collected.append({
                    "title": row.get("title", ""),
                    "abstract": "",
                    "authors": [],
                    "institution": "",
                    "venue": "",
                    "year": None,
                    "pages": "",
                    "doi": "",
                    "keywords": [],
                    "subject_classification": "",
                    "url": "",
                    "pdf_url": row.get("download_url", ""),
                    "source": "ncpssd",
                    "search_keyword": keyword,
                    "error": str(e),
                    "fulltext_available": bool(row.get("download_url") or row.get("read_url")),
                })
        context.close()
        browser.close()
        return collected


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect papers from ncpssd")
    parser.add_argument("--keyword", required=True)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--output", default="")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--username", default=os.getenv("NCPSSD_USERNAME", ""))
    parser.add_argument("--password", default=os.getenv("NCPSSD_PASSWORD", ""))
    args = parser.parse_args()

    if not args.username or not args.password:
        raise SystemExit("NCPSSD_USERNAME / NCPSSD_PASSWORD required")

    data = collect(args.keyword, args.username, args.password, limit=args.limit, headed=args.headed)
    out = json.dumps(data, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
