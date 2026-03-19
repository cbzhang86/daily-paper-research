---
name: daily-paper-digest
description: "Generate daily paper digest from collected papers. Integrates with daily-paper-research pipeline."
---

# Daily Paper Digest

Generate structured daily digest from collected papers.

## Usage

### Generate digest for today

```
User: Generate today's paper digest
```

### Generate digest for specific date

```
User: Generate paper digest for 2026-03-19
```

### Generate digest with focus

```
User: Generate digest focusing on AI energy consumption papers
```

## Input

Reads from `skills/daily-paper-research/data/daily/YYYY-MM-DD/`:
- `collected.json` — raw paper data
- `normalized.json` — normalized records
- `analysis.json` — analysis results

## Output

Generates:
- `digest.md` — formatted daily digest
- `highlights.md` — key papers summary
- `trends.md` — emerging trends analysis

## Digest Format

```markdown
# Daily Paper Digest — YYYY-MM-DD

## Overview
- Total papers: X
- Sources: arXiv, PubMed, ncpssd, etc.
- Top topics: topic1, topic2, topic3

## Top Papers (3-5)

### 1. [Paper Title](link)
- **Authors**: Author1, Author2
- **Key Finding**: One sentence summary
- **Relevance**: Why it matters
- **Full-text**: ✅ Available / ❌ Not available

## Trends & Patterns
- Trend 1: description
- Trend 2: description

## Recommended Reading
- [Paper A] — for methodology
- [Paper B] — for literature review

## Follow-up Questions
- Question 1
- Question 2
```

## Integration

Works with:
- `daily-paper-research` pipeline
- `paper-summarize-academic` for deep summaries
- `hipocampus` for memory persistence

## Configuration

In `config/digest.json`:
```json
{
  "topPapersCount": 5,
  "includeAbstracts": true,
  "highlightFulltext": true,
  "topics": ["管理学", "未成年研究", "老龄化研究", "社会保障"]
}
```
