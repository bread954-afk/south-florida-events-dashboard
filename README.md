# South Florida Events Dashboard

Live-ready static dashboards for:
- Broward County
- Miami-Dade County

Files:
- `index.html` — landing page
- `broward.html` — Broward dashboard
- `broward-events.json` — Broward event archive
- `miami.html` — Miami-Dade dashboard
- `miami-events.json` — Miami-Dade event archive
- `dashboard-months.js` — shared Sep–Dec month/date logic

The dashboards fetch the JSON files on page load, so event data can be updated independently from the dashboard layout.

## Sep–Dec 2026 month selector

Both county dashboards use one page and one county event archive for September through December 2026.

- Choose September, October, November, or December from the Month selector.
- The page defaults to the browser's current month inside the supported range, September before the range, and December after the range.
- Search, city, category, and price filters stay selected when the month changes.
- Favorites are shared across all four months for that county.
- Completed months remain browseable.
- An empty future month displays its calendar and a friendly "check back" message instead of a data error.
