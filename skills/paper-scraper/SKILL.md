---
name: paper-scraper
description: >
  Academic paper crawler for domestic and international paper websites. Extracts paper metadata
  (title, authors, abstract, DOI, PDF links, citations) with adaptive anti-blocking, self-learning
  pattern memory, and resume support. Use when: scraping papers from IEEE, arXiv, Semantic Scholar,
  Google Scholar, CNKI, WanFang, PubMed, Springer, ScienceDirect, or any academic site.
  Triggers: "scrape papers", "crawl paper site", "extract paper metadata", "fetch papers",
  "download paper list", "论文爬取", "论文抓取", "文献爬取".
---

# Academic Paper Scraper

Integrates Scrapling (high-performance parser + anti-bot fetchers) with self-learning experience memory.

## Prerequisites

```bash
pip install scrapling[fetchers] && scrapling install
```

## Architecture

```
paper-scraper/
├── scripts/
│   ├── spider.py          # Core multi-site spider (Scrapling-based)
│   ├── extractors.py      # Site-specific extraction logic
│   └── progress.py        # Checkpoint + resume manager
├── references/
│   └── academic-sites.md  # Selectors and patterns for known sites
├── config/
│   └── sites.json         # Learned site patterns (auto-updated)
└── experiences/
    └── lessons.md         # Failure records and anti-block learnings
```

## Core Workflow

### 1. Check Experience First

```python
import json, os
from pathlib import Path

CONFIG = Path(__file__).parent / "config" / "sites.json"

def load_site_patterns():
    if CONFIG.exists():
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    return {}
```

- If domain matches `sites.json`, use learned selectors and delays
- If new domain, proceed with auto-discovery

### 2. Crawl a Site

```bash
python scripts/spider.py --url "https://arxiv.org/search/?query=llm" --max-pages 10 --output papers.json
```

Options:
- `--url` — start URL or search results page
- `--max-pages` — max pages to crawl (default: 50)
- `--output` — output file (JSON/JSONL)
- `--min-delay / --max-delay` — request interval in seconds
- `--mode` — `auto` | `search` | `list` | `detail`
- `--session-type` — `http` | `stealthy` | `dynamic`
- `--resume` — resume from last checkpoint

### 3. Extraction Modes

| Mode | Use Case |
|------|----------|
| `search` | Search results page → list of papers |
| `list` | Author/publication page → paper list |
| `detail` | Single paper page → full metadata |

### 4. Output Format

```json
{
  "papers": [
    {
      "title": "Paper Title",
      "authors": ["Author 1", "Author 2"],
      "abstract": "...",
      "doi": "10.xxxx/xxxxx",
      "url": "https://...",
      "pdf_url": "https://...pdf",
      "year": 2025,
      "venue": "Conference/Journal",
      "citations": 42,
      "keywords": ["kw1", "kw2"]
    }
  ],
  "meta": {
    "source_url": "...",
    "crawled_at": "2026-03-19T...",
    "pages_crawled": 5,
    "patterns_used": "learned/auto-discovered"
  }
}
```

## Anti-Blocking Strategy

| Level | Delay | Trigger |
|-------|-------|---------|
| 0 (Normal) | 2-5s | Default |
| 1 (Caution) | 5-10s | Single 429/403 |
| 2 (Careful) | 10-20s | Repeated blocks |
| 3 (Critical) | 30-60s | Multiple blocks |
| 4 (Pause) | STOP | CAPTCHA detected |

- Rotate User-Agent from pool
- Adaptive delays based on response signals
- Domain-specific learned delay configs from `sites.json`

## Self-Learning System

After each successful crawl:
1. Save working selectors to `config/sites.json[domain]`
2. Record anti-block parameters (min/max delay, block threshold)
3. Save pagination pattern (page numbers / next button / infinite scroll)

After failures:
1. Record to `experiences/lessons.md` with error type, cause, solution

## Site-Specific Configs

See `references/academic-sites.md` for known site selectors and patterns.
The agent reads this file when crawling a known academic site.

## Integration with Agent Workflow

The agent can:
1. Call `spider.py` to crawl a site
2. Parse the JSON output
3. Analyze papers (summarize, compare, extract trends)
4. Store results in workspace for further processing

For dynamic sites requiring JavaScript rendering:
```bash
python scripts/spider.py --url "..." --session-type stealthy --max-pages 5
```

For simple static sites (faster):
```bash
python scripts/spider.py --url "..." --session-type http --max-pages 20
```
