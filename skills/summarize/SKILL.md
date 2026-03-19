---
name: summarize
description: "Summarize URLs or files with the summarize CLI (web, PDFs, images, audio, YouTube)."
version: "1.0.0"
author: "steipete"
---

# Summarize

Summarize URLs or files using the summarize CLI tool.

## Installation

```bash
# Install summarize CLI
pip install summarize-cli

# Or via npm
npm install -g summarize-cli
```

## Usage

### Summarize a URL

```
User: Summarize https://example.com/article
```

### Summarize a file

```
User: Summarize ~/Downloads/paper.pdf
```

### Summarize with options

```
User: Summarize this URL with focus on methodology:
https://arxiv.org/abs/2301.12345
```

## Supported Formats

| Format | Support | Notes |
|--------|---------|-------|
| Web pages (HTML) | ✅ | Full text extraction |
| PDF documents | ✅ | With layout preservation |
| Images | ✅ | OCR enabled |
| Audio files | ✅ | Auto-transcription |
| YouTube videos | ✅ | Transcript extraction |

## Output Format

```markdown
## Summary
[Brief 2-3 sentence overview]

## Key Points
- Point 1
- Point 2
- Point 3

## Main Arguments
- Argument 1: supporting evidence
- Argument 2: supporting evidence

## Conclusions
- Conclusion 1
- Conclusion 2

## Relevant Quotes
> "Important quote from source"
```

## Options

| Option | Values | Default |
|--------|--------|---------|
| `--length` | short, medium, long | medium |
| `--format` | bullet, paragraph, outline | bullet |
| `--focus` | main-points, methodology, conclusions | main-points |
| `--language` | zh-CN, en-US | zh-CN |

## Examples

### Short summary

```
User: Give me a short summary of this URL
https://blog.example.com/post
```

### Focus on methodology

```
User: Summarize this paper focusing on methodology
https://arxiv.org/abs/2301.12345
```

### Compare multiple sources

```
User: Summarize and compare these articles:
- https://source1.com/article
- https://source2.com/article
```

## Security

- Only processes URLs/files explicitly provided by user
- Does not access credentials or sensitive files
- No external API calls beyond specified URLs
- No data retention after summary

## Integration

Works with:
- `daily-paper-research` — summarize collected papers
- `paper-summarize-academic` — deep academic summaries
- `hipocampus` — store summaries in memory

## Configuration

Create `config/summarize.json`:

```json
{
  "defaultLength": "medium",
  "defaultFormat": "bullet",
  "defaultLanguage": "zh-CN",
  "cacheResults": true,
  "cacheExpiry": 86400
}
```
