# Build verification — transparent status

**Completed in the authoring session**

- [x] Next.js source code for Today, Signal detail, Research, Promise Tracker, Watchlist, Settings.
- [x] Mobile/desktop responsive CSS implementation and mobile bottom navigation.
- [x] Python FastAPI, SQLAlchemy SQLite + optional PostgreSQL support.
- [x] 18-company watchlist seed and general dynamic NSE ticker handling.
- [x] Yahoo EOD adapter, NSE public announcements adapter, original PDF discovery and extraction code.
- [x] Deterministic priority classifier, deduplication and price/volume calculations.
- [x] Hosted-model adapter for grounded Q&A, extraction and enrichment; exact source-quote verification.
- [x] Demo mode clearly labelled illustrative; no fake source URLs or claims of live data.
- [x] Backend offline tests: **13 passed** during the build session.
- [x] TSX / TypeScript syntax parsing: passed on 5 authored frontend modules.
- [x] Docker API config, scheduled GitHub Actions job, run/deploy instructions.

**Not verified in this environment**

- [ ] `npm install` and `npm run build` (no outbound npm registry access).
- [ ] Visual browser QA on the rendered Next.js app (dependencies unavailable here).
- [ ] NSE, Yahoo Finance or Screener HTTP access (container external DNS/network blocked).
- [ ] Hosted Gemini / other LLM inference (no user-provided API credential).
- [ ] Live end-to-end document indexing and Promise Tracker outcome for real company files.
- [ ] Deployed frontend/backend URL and cloud database integration (no user cloud account credentials).
- [ ] Real-device/mobile network QA.

**Next quality gates before ENAM submission**

1. Install frontend dependencies, run `npm run typecheck` and `npm run build`; repair any issues found.
2. Bring up backend and frontend locally; open `http://localhost:3000`; verify navigation, search, responsive layout and settings.
3. Ingest several NSE companies on a network-enabled machine; confirm timestamps and primary filing URLs.
4. Add hosted-model key to API backend only; index one recent actual earnings-call PDF and one results/annual report; run `promises` and `enrich`.
5. Test previously unseen NSE ticker, empty/invalid ticker, unavailable sources, no key, and several real disclosures.
6. Deploy to a hosted API + web URL, configure persistent PostgreSQL, test on phone, complete ENAM email and attach actual AI history.

The authoring environment cannot truthfully claim completion of the unchecked items; they must be tested under the actual deployment environment.
