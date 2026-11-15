# Product choices and trade-offs

| Decision | Reason | Trade-off |
|---|---|---|
| Hybrid Signal Inbox + Promise Tracker | Unique link from what changed to management accountability | Less breadth in other financial-research modules |
| Mobile-first consumer fintech design | Approachable, fast information hierarchy | Less data density than a professional terminal |
| Next.js + Python FastAPI | Flexible UX and strong financial/PDF Python tooling | Separate build toolchains, combined in one Docker service |
| Original primary sources for research | Prevents circular news/broker summaries | Extraction / site access more difficult |
| Hosted model, no training | Fastest route to real capabilities with clear cost control | External API key, latency and provider limits |
| Rules for first-pass materiality | Transparent and cheap | Fine-grained materiality needs richer evidence |
| Precompute/cached indexed passages | Low latency for repeat queries | Data freshness depends on scheduled ingest |
| Previous 20 EOD sessions for volume | Interpretable benchmark | No signal if insufficient history |
| Explicit illustrative demo switch | User can explore no-key prototype honestly | Demo content isn't evidence of live ingestion |
| No authentication / brokerage actions | Reduces build complexity | Not ready for public multi-user deployment |
