---
name: web-data-extraction
description: "Extract structured data from live websites using browser tools and web-fetch APIs — tables, lists, paginated content, search results. Covers JS-driven DOM extraction, MCP search/research, and direct HTTP fetch."
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [web, data, extraction, scraping, browser, research]
    related_skills: [dogfood, hermes-agent]
    homepage: ~
---

# Web Data Extraction

Extract structured data from websites when you need information the web doesn't deliver as a neat API response. Three complementary approaches, ordered by preference.

---

## Approach 1: LinkUp MCP (Search & Research)

When the user asks for current data, facts, or research — try this first. It's the fastest path and works without a browser session.

### Tools

| Tool | When to use |
|------|------------|
| `linkup_search` | Quick factual lookups with a single query — current standings, prices, news, stats, definitions. Supports domain filtering, date ranges, and multi-source verification. |
| `linkup_research` | Deep multi-step investigations — compare X, Y, Z; synthesize from multiple sources with citations. Async: call it, get back a task ID, then poll `linkup_get_research` until status is "completed". |
| `linkup_fetch` | Fetch a specific URL and get its extracted content. Use when you have a known URL that contains the data you need. For simple text/markdown/JSON endpoints, prefer `curl` or `web_extract` instead. |

### When to skip and use the browser instead

- The target page renders content dynamically via JavaScript (SPA, heavy JS frameworks)
- The data is inside a paginated table the user can see but is not in the raw page content
- LinkUp returns partial or stale data for a highly interactive site

---

## Approach 2: Browser Tools (DOM Extraction)

Use the browser toolset when:
1. The page is JS-rendered (APIs are hidden behind client-side rendering)
2. `browser_snapshot` truncates (tables, long lists, paginated content)
3. You need to interact with the page (click filters, submit forms, scroll to load more)

### Core Technique: `browser_console` with JavaScript

When `browser_snapshot` returns a truncated view of a table/list, extract the data programmatically instead of scrolling through dozens of pages:

```javascript
// Extract rows from any table-like structure
(() => {
  const rows = document.querySelectorAll('table tbody tr');
  return Array.from(rows).slice(0, 20).map(row => {
    const cells = row.querySelectorAll('td');
    return {
      rank: cells[0]?.querySelector('h3')?.textContent?.trim(),
      team: cells[1]?.textContent?.trim(),
      points: cells[5]?.querySelector('h4')?.textContent?.trim()
    };
  });
})()
```

### Patterns Library

See `references/js-extraction-patterns.md` for ready-to-use JavaScript snippets for common data shapes:

- **Tables** — any `<table>` structure with header rows and data rows
- **Lists** — `<ul>`/`<ol>`, card grids, feed items
- **Pagination** — extract from visible page, identify next-page link
- **Attributes** — `href`, `src`, `data-*` attributes from links and images
- **Meta data** — `og:*` tags, JSON-LD structured data, canonical URLs

### Clean Ranks (strip position-change icons)

Some ranking tables mix rank numbers with arrow/change indicators in the same cell. Use the nested heading tag (`h3`) for the clean rank:

```javascript
const rank = cells[0]?.querySelector('h3, .rank, [data-rank]')?.textContent?.trim();
```

### Workflow

1. **Navigate** — `browser_navigate(url)`
2. **Check page shape** — `browser_snapshot()` to understand the DOM layout
3. **Extract data** — `browser_console(expression="<JS query>")` gets clean structured output
4. **Iterate if needed** — if data spans multiple pages, extract the next-page link, then navigate to it and repeat
5. **Present** — format as a markdown table, JSON, or plain text for the user

---

## Approach 3: Direct Fetch (for API/JSON/Plain endpoints)

Use `curl` via `terminal()` or `mcp__linkup__linkupapi_fetch` for endpoints that return structured data directly (JSON APIs, raw `.md`/`.txt` files, markdown docs).

```bash
curl -s "https://api.example.com/data" | jq '.results[:10] | [{rank, name, score}]'
```

Prefer this when:
- The URL is a known API endpoint
- The content is plain text, JSON, CSV, or markdown
- No JavaScript rendering is needed

---

## Pitfalls

- **Truncated snapshots**: `browser_snapshot` caps at ~8000 chars for full mode. Don't scroll-repeatedly — use `browser_console` with JS to extract cleanly.
- **Rate limiting**: `browser_console` with JS is an in-page DOM query — no network cost. Use it freely.
- **Dynamic content**: Some pages lazy-load rows as you scroll. Use `browser_scroll` first, then extract.
- **CORS/Same-origin**: `browser_console` JavaScript runs in the page context, so it has full access to the current page's DOM — no CORS restrictions.
- **JSON-LD**: Many pages embed structured data in `<script type="application/ld+json">`. Extract it with `document.querySelector('script[type="application/ld+json"]').textContent` for clean structured output.
- **LinkUp vs browser**: If LinkUp gives partial results (or says "unable to fetch"), switch to the browser — don't retry LinkUp more than once.