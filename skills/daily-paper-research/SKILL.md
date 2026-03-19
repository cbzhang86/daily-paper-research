---
name: daily-paper-research
description: >
  Daily academic paper pipeline for policy/social-science oriented topics. Integrates international
  multi-source paper discovery (paper-distill style), domestic site crawling (paper-scraper style),
  daily clustering/summarization/report generation, and research memory accumulation for later use
  in paper writing and topic development. Use when the user wants a daily paper briefing, paper radar,
  topic monitoring, literature summary, or wants to turn accumulated papers into research assistance.
---

# Daily Paper Research

This skill is the integrated layer above:
- **paper-scraper** → domestic / site-level crawling
- **paper-distill-mcp** → international multi-source paper discovery + ranking ideas
- **AutoResearchClaw** → downstream deep research / writing assistance

## Target workflow

1. **Collect** papers from configured topics and sources
2. **Normalize + deduplicate** records
3. **Analyze** papers into structured summaries
4. **Render** a daily briefing
5. **Persist** outputs for later writing support

## Current default topics

- 管理学大类
- 社会保障类
- 未成年人研究类
- 老龄化研究类

## Main entry

```bash
python scripts/run_daily_pipeline.py --date 2026-03-19
```

Optional:
- `--config config/topics.json`
- `--output data/daily/2026-03-19`
- `--limit-per-topic 15`
- `--skip-domestic`
- `--skip-international`

## Output files

Each daily run creates a folder like:

```text
skills/daily-paper-research/data/daily/YYYY-MM-DD/
├── collected.json           # raw collected papers
├── normalized.json          # deduplicated normalized papers
├── analysis.json            # per-paper summaries + grouped insights
├── report.md                # daily readable report
└── manifest.json            # run metadata
```

## Use with later writing support

The daily folders become a growing local literature bank. Later, when the user provides a topic,
use these stored daily outputs to:
- retrieve recent related papers
- identify recurring themes / methods / gaps
- build a seed bibliography
- draft literature review bullets
- prepare structured input for AutoResearchClaw

## Design notes

- International discovery is done through the `paper-distill-mcp` repo code already cloned in `temp/`
- Domestic discovery currently uses configured `paper-scraper` jobs and is designed to expand site by site
- Analysis is deterministic / rule-based first; LLM-driven deeper analysis can be layered on top later

## Recommended use pattern

- Daily / heartbeat use: run `run_daily_pipeline.py`
- Deep topic investigation: take a chosen topic from accumulated results and then invoke ResearchClaw
