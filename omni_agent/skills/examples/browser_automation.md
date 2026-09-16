---
name: browser_automation
description: Browser automation patterns
category: browser
---

# Browser Automation Skill

For web tasks:

1. **Search first** - Understand site structure
2. **Fetch page** - Get HTML content
3. **Parse** - Extract needed data
4. **Act** - If need interaction, use shell tool with curl or python requests

Patterns:
- For scraping: web_fetch + python parsing with BeautifulSoup
- For API: check network tab via fetch, then use requests
- For auth: look for API keys in docs, not hardcoded

Safety:
- Respect robots.txt
- Rate limit requests
- Don't spam

Example python for scraping:
```python
import requests
from bs4 import BeautifulSoup

url = "https://example.com"
resp = requests.get(url, headers={"User-Agent": "OMNI-AGENT"})
soup = BeautifulSoup(resp.text, 'html.parser')
titles = [h.text for h in soup.find_all('h2')]
```
