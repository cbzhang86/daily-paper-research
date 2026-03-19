import sys
sys.stdout.reconfigure(encoding='utf-8')
from scrapling.fetchers import DynamicFetcher

page = DynamicFetcher.fetch('https://www.ncpssd.cn/', headless=True, network_idle=True)
print('Page loaded with Playwright')
print('Title:', page.css('title')[0].text.clean() if page.css('title') else 'N/A')
print('Body length:', len(str(page)))

# Look for search input
search_inputs = page.css('input')
for inp in search_inputs:
    placeholder = inp.attrib.get('placeholder', '')
    name = inp.attrib.get('name', '')
    id_ = inp.attrib.get('id', '')
    if placeholder or name:
        print(f'Input: placeholder="{placeholder}" name="{name}" id="{id_}"')

# Look for search forms / buttons
forms = page.css('form')
for form in forms:
    action = form.attrib.get('action', '')
    print(f'Form action: {action}')

# Check for search-related elements
for sel in ['.search', '#search', '.search-box', '.search-input', '[type="search"]']:
    els = page.css(sel)
    if els:
        print(f'Found search element: {sel} ({len(els)} items)')
        for e in els[:2]:
            print(f'  HTML: {e.html_content[:200]}')

# Key nav links
links = page.css('a')
paper_links = []
for link in links:
    href = link.attrib.get('href', '')
    text = link.text.clean()[:50]
    if any(k in href for k in ['literature', 'journal', 'article', 'paper', 'search', 'Literature']):
        paper_links.append(f'{text} -> {href}')

print(f'\nPaper-related links ({len(paper_links)}):')
for pl in paper_links[:15]:
    print(f'  {pl}')
