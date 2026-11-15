# FINN architecture and component ownership

## Overview

```
                           ┌───────────────────────────────┐
                           │ Next.js mobile-first UI       │
                           │ Today / Research / Watchlist  │
                           │ Settings / Signal detail      │
                           └───────────────┬───────────────┘
                                           │ HTTP JSON
                           ┌───────────────▼───────────────┐
                           │ FastAPI                       │
                           │ GET feed, company, promises   │
                           │ POST research, index, extract │
                           └────┬──────────┬───────────┬───┘
                                │          │           │
                     ┌──────────▼─┐   ┌────▼────┐ ┌───▼───────────┐
                     │SQLAlchemy  │   │Hosted AI│ │Source adapters│
                     │SQLite/PgSQL│   │Gemini or│ │Yahoo EOD      │
                     │evidence DB │   │compatible││NSE filings    │
                     └────────────┘   └─────────┘ │Screener links │
                                                 │Company PDF    │
                                                 └───────────────┘
```

## Data domains

- `companies`: 18 predefined NSE symbols, sector groupings and extra ad hoc tickers.
- `prices_daily`: observed EOD closes, volume, day change, previous-20-session volume multiple.
- `announcements`: source disclosures, categorisation, priority, rationale, summary, optional AI-extracted results.
- `source_documents` and `document_chunks`: original PDF URL, page text, source type, extraction status.
- `financial_metrics`: verified amounts with period, unit, reporting basis, quote/page.
- `guidance_claims`: verified forecast + matched actual when comparable.

## Relevance model

1. Routine paperwork filtered to low unless otherwise material.
2. Significant disclosures such as results, management changes, material M&A / litigation routed high by default.
3. Other financing, capacity and market-sensitive events medium by category, but the classifier remains transparent and conservative; no purported price-impact prediction.
4. Alerts from price and volume computed independently after EOD refresh, never from the model.
5. All events searchable with category and timeframe filters, including collapsed routine items.

## Dynamic NSE research

`POST /api/companies/{ticker}/discover` resolves an unseen symbol, discovers original document links, then indexes up to two PDFs. `POST /api/research` reads company evidence chunks; question wording influences retrieval, but not the source scope. `POST /api/companies/{ticker}/analyze-promises` extracts matched claims and actuals only from indexed sources.

## Operational trade-offs

- **Good for challenge:** direct Python source scripts, cached passage index, few dependencies, no embedding store required, no expensive model training.
- **Known limitations:** third-party HTTP source reliability; source PDF extraction can be slow; user-initiated indexing is synchronous in this prototype; no multi-user auth or task queue.
- **Mature system next:** schedule/worker queue, more robust filing data vendor or exchange-authorized ingestion, granular release-source metadata and realtime notification delivery, pgvector, structured financial-statement validation, trace logs, rate limiting and monitoring.

## Security and compliance notes

Secrets are exclusively backend environment variables. Browser receives no GEMINI_API_KEY. Requests to remote PDFs are limited to HTTPS and size; deployment to an open internet audience should add a strict allowlist / private-IP resolution defense, timeouts, auth and rate limits. Never scrape through login barriers or bypass CAPTCHA. AI provider receives excerpts of publicly disclosed corporate documents, which is appropriate for this demonstration but provider data-processing policy should be reviewed for production.
