# Academic Sites Reference

Known patterns and selectors for common paper websites.

## International

### arXiv (arxiv.org)
- **Type**: Preprint server
- **Search URL**: `https://arxiv.org/search/?query={query}&searchtype=all`
- **Pagination**: URL param `start` (increments by 25)
- **Selectors**:
  - Result item: `li.arxiv-result`
  - Title: `p.title`
  - Authors: `p.authors a`
  - Abstract: `span.abstract-full` / `span.abstract-short`
  - PDF: Construct from ID → `https://arxiv.org/pdf/{id}`
  - Year: `p.is-size-7` (regex for 4-digit year)
- **Anti-blocking**: Low, ~1s delay sufficient, no CAPTCHA
- **Rate limit**: Generous, but be polite

### Semantic Scholar (semanticscholar.org)
- **Type**: AI-powered paper search
- **Search URL**: `https://www.semanticscholar.org/search?q={query}&sort=relevance`
- **Pagination**: URL param `page`
- **API**: Available at `api.semanticscholar.org/graph/v1/paper/search`
- **Selectors**:
  - Result: `[data-test-id='result-card']`
  - Title: `h2 a`
  - Authors: `[data-test-id='author-list'] span`
  - Abstract: `[data-test-id='text-truncator']`
  - Meta: `[data-test-id='paper-meta']`
- **Anti-blocking**: Moderate, 2-3s delay, may rate-limit

### Google Scholar (scholar.google.com)
- **Type**: Paper search aggregator
- **Search URL**: `https://scholar.google.com/scholar?q={query}`
- **Pagination**: URL param `start` (increments by 10)
- **Selectors**:
  - Result: `.gs_r.gs_or.gs_scl`
  - Title: `h3.gs_rt a`
  - Authors/Venue: `.gs_a`
  - Abstract: `.gs_rs`
  - Citations: `a:contains('Cited by')`
  - PDF: `a[href*='.pdf']`
- **Anti-blocking**: HIGH — CAPTCHA after ~100 requests
  - Use StealthyFetcher with headless=True
  - 5-10s delays, rotate User-Agent
  - Consider using SerpAPI or Scholarly library as alternative

### PubMed (pubmed.ncbi.nlm.nih.gov)
- **Type**: Biomedical literature
- **Search URL**: `https://pubmed.ncbi.nlm.nih.gov/?term={query}`
- **API**: E-utilities API (free, recommended)
  - `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={query}`
  - `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={ids}`
- **Pagination**: URL param `page`
- **Selectors**:
  - Result: `.docsum-content`
  - Title: `.docsum-title`
  - Authors: `.docsum-authors`
  - Journal: `.docsum-journal-citation`
- **Anti-blocking**: Low for web, API has 3 req/s limit without key

### IEEE Xplore (ieeexplore.ieee.org)
- **Type**: Engineering/CS papers
- **Search**: Requires JavaScript rendering → use DynamicFetcher
- **Anti-blocking**: Moderate, may block headless browsers
- **Recommendation**: Use their API if possible (requires API key)

### Springer (link.springer.com)
- **Type**: Multidisciplinary
- **Search URL**: `https://link.springer.com/search?query={query}`
- **Selectors**:
  - Result: `[data-test='result-list'] li`
  - Title: `a.title`
  - Authors: `.authors`
- **Anti-blocking**: Moderate

### ScienceDirect (sciencedirect.com)
- **Type**: Elsevier journals
- **Search**: Heavily JavaScript-rendered → use DynamicFetcher
- **Anti-blocking**: High, consider Elsevier API

## Domestic (Chinese)

### CNKI (cnki.net) — 中国知网
- **Type**: China's largest academic database
- **Search URL**: `https://kns.cnki.net/kns8s/defaultresult/index`
- **Anti-blocking**: HIGH
  - Requires login for full access
  - Aggressive bot detection
  - Use StealthyFetcher with session persistence
  - 5-15s delays
- **Selectors**: Dynamically loaded, use `dynamic` session type
- **Recommendation**: Prefer API if available, or manual export

### WanFang (wanfangdata.com.cn) — 万方数据
- **Type**: Chinese academic database
- **Search URL**: `https://s.wanfangdata.com.cn/paper?q={query}`
- **Anti-blocking**: Moderate
- **Selectors**: JavaScript-rendered, use dynamic mode

### VIP (cqvip.com) — 维普
- **Type**: Chinese journal database
- **Search URL**: `https://www.cqvip.com/search/?q={query}`
- **Anti-blocking**: Moderate

### Baidu Xueshu (xueshu.baidu.com) — 百度学术
- **Type**: Chinese academic search
- **Search URL**: `https://xueshu.baidu.com/s?wd={query}`
- **Selectors**:
  - Result: `.sc_default_result .sc_content`
  - Title: `h3 a`
  - Authors: `.sc_info .sc_info_other a`
  - Abstract: `.c_abstract`
- **Anti-blocking**: Moderate, 3-5s delays
- **Pagination**: URL param `pn` (increments by 10)

## Session Type Selection Guide

| Site | Recommended Session | Why |
|------|-------------------|-----|
| arXiv | http | Simple static HTML |
| Semantic Scholar | http | Fast, mostly static |
| Google Scholar | stealthy | CAPTCHA protection |
| PubMed | http | Simple HTML + API |
| IEEE Xplore | dynamic | JS-heavy |
| CNKI | stealthy | Bot detection |
| WanFang | dynamic | JS-heavy |
| Baidu Xueshu | http | Mostly static |
