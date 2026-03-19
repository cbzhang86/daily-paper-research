# Daily Paper Research Architecture

## Goal

Build a reusable literature system for:
1. daily paper acquisition
2. daily paper analysis + report generation
3. long-term knowledge accumulation
4. downstream topic-to-paper research assistance

## Integrated components

### 1. paper-scraper
Used as the **site-level crawling layer**.
Best for:
- domestic academic sites
- dynamic/login-based sources
- custom selectors and incremental site adaptation

### 2. paper-distill-mcp
Used as the **international paper discovery layer**.
Best for:
- OpenAlex / CrossRef / PubMed / arXiv / EuropePMC / DBLP style discovery
- multi-source retrieval
- ranking / dedup / pool-thinking

### 3. AutoResearchClaw
Used as the **deep research and writing assistance layer**.
Best for:
- topic decomposition
- structured literature review
- gap identification
- turning a topic idea into a research workflow

## Pipeline

```text
Topic config
   ↓
International retrieval (paper-distill style)
   +
Domestic retrieval (paper-scraper style)
   ↓
Normalization + deduplication
   ↓
Per-paper structured summary
   ↓
Daily report generation
   ↓
Historical accumulation in data/daily/
   ↓
Research brief extraction for later writing support
   ↓
AutoResearchClaw / manual deep research
```

## Current implementation status

### Implemented now
- daily-paper-research skill scaffold
- topic config for 4 target domains
- international retrieval through cloned paper-distill code
- normalization / dedup / analysis / markdown report generation
- research brief generation from accumulated daily outputs

### Planned next
- real domestic source adapters (start with ncpssd)
- richer method / institution / policy extraction
- scheduling / daily cron trigger
- one-click handoff into ResearchClaw topic runs

## Suggested usage model

### Daily mode
Run `run_daily_pipeline.py` once per day and produce report.md.

### Research support mode
Run `build_research_brief.py --topic "..."` to assemble recent relevant papers into a writing-oriented brief.

### Full paper assistance mode
Take a research idea + accumulated brief and feed both into AutoResearchClaw / structured drafting workflow.
