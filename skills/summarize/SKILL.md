---
name: summarize
description: "Summarize URLs or files with the summarize CLI (web, PDFs, images, audio, YouTube)."
---

# Summarize Skill

Summarize URLs or files using the summarize CLI tool.

## Installation

Requires the `summarize` CLI tool to be installed:

```bash
pip install summarize-cli
# or
npm install -g summarize-cli
```

## Usage

### Summarize a URL

```
User: Summarize https://example.com/article
```

### Summarize a file

```
User: Summarize the PDF at ~/Downloads/paper.pdf
```

### Summarize multiple sources

```
User: Summarize these URLs and give me key points:
- https://blog.example.com/post1
- https://arxiv.org/abs/2301.12345
```

## Supported Formats

- Web pages (HTML)
- PDF documents
- Images (with OCR)
- Audio files (with transcription)
- YouTube videos (with transcript extraction)

## How It Works

1. Extract content from URL or file
2. Send to LLM for summarization
3. Return structured summary with key points

## Options

- `--length`: Target summary length (short/medium/long)
- `--format`: Output format (bullet/paragraph/outline)
- `--focus`: Focus area (main-points/methodology/conclusions)

## Example Output

```markdown
## Summary

Brief 2-3 sentence overview.

## Key Points
- Point 1
- Point 2
- Point 3

## Main Arguments
- Argument 1 with supporting evidence
- Argument 2 with supporting evidence

## Conclusions
- Conclusion 1
- Conclusion 2

## Relevant Quotes
> "Important quote from the source"
```

## Security

- Only processes URLs/files explicitly provided by user
- Does not access credentials or sensitive files
- No external API calls beyond the specified URLs
