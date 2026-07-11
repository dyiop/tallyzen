# JavaScript DOM Extraction Patterns

Ready-to-use `browser_console(expression="...")` snippets for extracting structured data from live web pages.

---

## Table Data (Standard)

```javascript
(() => {
  const rows = document.querySelectorAll('table tbody tr');
  return Array.from(rows).slice(0, 50).map(row => {
    const cells = row.querySelectorAll('td');
    return {
      rank: cells[0]?.textContent?.trim() || '',
      name: cells[1]?.textContent?.trim() || '',
      value: cells[5]?.textContent?.trim() || ''
    };
  });
})()
```

## Table Data (with nested headings for clean ranks)

Ranking tables often mix rank number and position-change arrows in the same cell. Use the heading element:

```javascript
(() => {
  const rows = document.querySelectorAll('table tbody tr');
  return Array.from(rows).slice(0, 30).map(row => {
    const cells = row.querySelectorAll('td');
    if (!cells.length) return null;
    const rank = cells[0]?.querySelector('h3')?.textContent?.trim() || '?';
    const name = cells[1]?.textContent?.trim() || '';
    const points = cells[5]?.querySelector('h4')?.textContent?.trim() || '';
    const change = cells[4]?.textContent?.trim().replace(/\s+/g, ' ') || '';
    return {rank, name, points, change};
  }).filter(Boolean);
})()
```

## Card Grid / List Items

```javascript
(() => {
  const items = document.querySelectorAll('.card, .item, [class*="result"], li.result-item');
  return Array.from(items).slice(0, 20).map(item => ({
    title: item.querySelector('h2, h3, .title, [class*="title"]')?.textContent?.trim() || '',
    link: item.querySelector('a')?.href || '',
    description: item.querySelector('p, .desc, [class*="desc"]')?.textContent?.trim() || ''
  }));
})()
```

## JSON-LD Structured Data (many sites embed this)

```javascript
(() => {
  const scripts = document.querySelectorAll('script[type="application/ld+json"]');
  return Array.from(scripts).map(s => {
    try { return JSON.parse(s.textContent); } catch(e) { return null; }
  }).filter(Boolean);
})()
```

## Meta Tags (Open Graph, Twitter Cards)

```javascript
(() => {
  const meta = document.querySelectorAll('meta[property^="og:"], meta[name^="twitter:"]');
  return Array.from(meta).map(m => ({ property: m.getAttribute('property') || m.getAttribute('name'), content: m.getAttribute('content') }));
})()
```

## All Links on a Page

```javascript
(() => {
  return Array.from(document.querySelectorAll('a[href]')).map(a => ({ text: a.textContent.trim(), href: a.href }));
})()
```

## Paginated: Extract + Find Next Page

```javascript
// Step 1: Extract current page data
const data = Array.from(document.querySelectorAll('table tbody tr')).map(...);

// Step 2: Get next page URL
const nextUrl = document.querySelector('a[rel="next"], .pagination .next, [aria-label="Next"]')?.href;
// If nextUrl exists, navigate to it and repeat step 1
```

## Attribute Values (image srcs, data attributes)

```javascript
(() => {
  const imgs = document.querySelectorAll('img[src]');
  return Array.from(imgs).slice(0, 30).map(img => ({ alt: img.alt || '', src: img.src, width: img.width, height: img.height }));
})()
```

## Select/Dropdown Options

```javascript
(() => {
  const select = document.querySelector('select[name="region"], #region-select, [data-testid="region"]');
  if (!select) return [];
  return Array.from(select.options).map(opt => ({ value: opt.value, text: opt.textContent.trim() }));
})()

---

## Tips

- **Start with `slice(0, 10)`** to test your selector, then expand the limit
- **Use `filter(Boolean)`** to remove null entries from sparse tables
- **Check `browser_console` return type**: `result_type: "list"` means the JSON parsed correctly; `"string"` means it was returned as a string (add `JSON.stringify()`)
- **If the selector returns nothing**, the page likely uses shadow DOM or iframes — check `browser_snapshot` first to understand the actual DOM structure