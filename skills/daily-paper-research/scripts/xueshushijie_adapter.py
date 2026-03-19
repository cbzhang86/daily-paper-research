#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

BASE = "https://xueshushijie.cn"
ROUTES: list[dict[str, Any]] = [
    {"path": "/journal/high2019", "label": "高转载期刊 2019", "tags": ["管理", "治理", "社会", "期刊"]},
    {"path": "/journal/high2020", "label": "高转载期刊 2020", "tags": ["管理", "治理", "社会", "期刊"]},
    {"path": "/journal/high2021", "label": "高转载期刊 2021", "tags": ["管理", "治理", "社会", "期刊"]},
    {"path": "/journal/high2022", "label": "高转载期刊 2022", "tags": ["管理", "治理", "社会", "期刊"]},
    {"path": "/journal/rssiHigh2022", "label": "高影响期刊 2022", "tags": ["社科", "期刊", "学术"]},
    {"path": "/journal/rssiHigh2023", "label": "高影响期刊 2023", "tags": ["社科", "期刊", "学术"]},
    {"path": "/journal/institutionalindex2018", "label": "机构索引 2018", "tags": ["机构", "研究", "社科"]},
    {"path": "/journal/institutionalindex2019", "label": "机构索引 2019", "tags": ["机构", "研究", "社科"]},
    {"path": "/journal/institutionalindex2020", "label": "机构索引 2020", "tags": ["机构", "研究", "社科"]},
    {"path": "/journal/institutionalindex2021", "label": "机构索引 2021", "tags": ["机构", "研究", "社科"]},
]


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _score(text: str, keyword: str, route_tags: list[str]) -> int:
    text = (text or "").lower()
    keyword = _clean(keyword).lower()
    if not keyword:
        return 0
    score = 0
    if keyword in text:
        score += 5
    for token in re.split(r"[\s,，;；/]+", keyword):
        token = token.strip().lower()
        if len(token) < 2:
            continue
        if token in text:
            score += 2
    for tag in route_tags:
        if tag.lower() in keyword:
            score += 1
    return score


def _guess_year(route_path: str, context: str) -> int | None:
    m = re.search(r"(20\d{2})", f"{route_path} {context}")
    return int(m.group(1)) if m else None


def _extract_records(page, route: dict[str, Any]) -> list[dict[str, Any]]:
    page.goto(BASE + route["path"], wait_until="networkidle")
    page.wait_for_timeout(1500)
    rows = page.evaluate(
        """
        () => {
          const out = [];
          const links = Array.from(document.querySelectorAll('a[href$=".pdf"], a[href*=".pdf?"]'));
          for (const a of links) {
            const href = a.href || '';
            if (!href) continue;
            let host = a.closest('li, tr, .el-card, .el-col, .el-row, .box, .item, .content, .main, .container, div') || a.parentElement;
            const ctx = host ? host.innerText || '' : (a.innerText || '');
            out.push({
              href,
              anchor_text: (a.innerText || '').trim(),
              context: (ctx || '').trim(),
              page_title: document.title || '',
              page_url: location.href
            });
          }
          return out;
        }
        """
    )
    dedup: dict[str, dict[str, Any]] = {}
    for row in rows:
        href = row.get("href", "")
        if href and href not in dedup:
            dedup[href] = row
    return list(dedup.values())


def collect(keyword: str, limit: int = 8, headed: bool = False) -> list[dict[str, Any]]:
    keyword = _clean(keyword)
    all_items: list[dict[str, Any]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="zh-CN",
        )
        page = context.new_page()
        for route in ROUTES:
            try:
                for row in _extract_records(page, route):
                    ctx = _clean(row.get("context", ""))
                    anchor = _clean(row.get("anchor_text", ""))
                    title = anchor or ctx.split("\n")[0][:120] or route["label"]
                    score = _score(f"{title} {ctx} {route['label']}", keyword, route["tags"])
                    all_items.append({
                        "title": title,
                        "authors": [],
                        "abstract": ctx[:500],
                        "year": _guess_year(route["path"], ctx),
                        "doi": "",
                        "url": row.get("page_url", BASE + route["path"]),
                        "pdf_url": row.get("href", ""),
                        "venue": route["label"],
                        "citation_count": 0,
                        "source": "xueshushijie",
                        "keywords": [keyword] if keyword else [],
                        "institution": "",
                        "subject_classification": route["label"],
                        "pages": "",
                        "fulltext_available": True,
                        "search_keyword": keyword,
                        "route": route["path"],
                        "route_label": route["label"],
                        "match_score": score,
                        "context": ctx[:1000],
                    })
            except Exception:
                continue
        context.close()
        browser.close()

    buckets: dict[str, dict[str, Any]] = {}
    for item in sorted(all_items, key=lambda x: (x["match_score"], len(x.get("title", ""))), reverse=True):
        pdf = item.get("pdf_url", "")
        if not pdf or pdf in buckets:
            continue
        buckets[pdf] = item

    items = list(buckets.values())
    positive = [x for x in items if x["match_score"] > 0]
    selected = positive[:limit] if positive else items[:limit]
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect public PDF resources from xueshushijie.cn")
    parser.add_argument("--keyword", required=True)
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--output", default="")
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()

    data = collect(args.keyword, limit=args.limit, headed=args.headed)
    out = json.dumps(data, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
