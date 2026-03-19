---
name: paper-summarize-academic
description: "Academic paper summarizer with structured output. Optimized for research workflow."
---

# Academic Paper Summarizer

Generate structured academic summaries from papers.

## Usage

### Summarize a paper

```
User: Summarize this paper: https://arxiv.org/abs/2301.12345
```

### Summarize with focus

```
User: Summarize this paper focusing on methodology
```

### Batch summarize

```
User: Summarize all papers in today's collection
```

## Input Sources

- arXiv URLs
- DOI links
- PDF files
- Papers from daily-paper-research collection

## Output Format

```markdown
# Paper Summary: [Title]

## Metadata
- **Authors**: Author list
- **Published**: Date
- **Venue**: Journal/Conference
- **DOI**: doi link
- **arXiv**: arxiv link (if applicable)

## One-Line Summary
[Single sentence capturing the core contribution]

## Problem & Motivation
- What problem does this paper solve?
- Why is it important?

## Methodology
- Approach overview
- Key innovations
- Dataset/experiment setup

## Key Findings
- Finding 1
- Finding 2
- Finding 3

## Strengths & Limitations

### Strengths
- Strength 1
- Strength 2

### Limitations
- Limitation 1
- Limitation 2

## Relevance to [Topic]
- How does this relate to your research interests?
- Potential applications

## Quotes & Citations
> "Important quote from the paper"

## Questions for Further Investigation
- Question 1
- Question 2
```

## Analysis Dimensions

When `--deep` flag is used:

1. **Theoretical Contribution** (1-5 scale)
2. **Methodological Rigor** (1-5 scale)
3. **Practical Applicability** (1-5 scale)
4. **Novelty** (1-5 scale)

## Integration

- Reads from `daily-paper-research/data/daily/*/collected.json`
- Outputs to `summaries/YYYY-MM-DD/`
- Integrates with PaperClaw scoring system

## Configuration

In `config/summarizer.json`:
```json
{
  "defaultFocus": "methodology",
  "includeCitations": true,
  "targetLength": "medium",
  "language": "zh-CN"
}
```
