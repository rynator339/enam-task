# FINN — Financial Investment Agent

**ENAM AI Engineer Build Challenge · IIT Delhi · 2026**

FINN is a mobile-first investor-intelligence prototype. It filters a mock 18-company NSE portfolio's corporate announcements and EOD market anomalies into a focused inbox, then offers evidence-backed company research and a management **Promise Tracker** (explicit guidance vs subsequently reported outcomes).

> **Status — source implementation, not a deployed service:** The Python API and its offline tests were run successfully in the authoring environment. Frontend TS/TSX syntax passed validation, but the full Next.js build, external NSE/Yahoo/Screener fetching, Gemini calls, and cloud deployment were **not** end-to-end verified because this environment has no outbound network/API credentials. The UI provides a clearly labelled *illustrative preview*, which must not be submitted as real market events. See [`docs/VERIFICATION.md`](docs/VERIFICATION.md).

## What works in the source

- **Today / signal inbox:** priority-ranked corporate filing feed with 24-hour, 7-day, 30-day or custom trailing interval; category filtering; hidden/collapsed routine paperwork; source links.
- **Deterministic EOD alerts:** daily close-to-close percentage moves and volume versus the **previous 20 trading sessions**, with configurable thresholds.
- **Corporate announcements:** best-effort NSE public-announcements ingestion, event classification, deduplication, and optional hosted-model enrichment of important filing summaries.
- **Company intelligence:** dynamically enter any valid NSE ticker, discover links to original company documents via Screener, index PDF passages, inspect extracted metrics, and ask source-grounded questions.
- **Promise Tracker:** hosted AI extracts explicit management guidance and reported actual figures with quote/page validation; deterministic code checks periods, units, reporting basis and numerical target outcomes.
- **Quarterly-results intelligence:** for genuine original results PDFs, optionally extract Revenue, EBITDA, PBT and PAT, with QoQ/YoY changes only where the relevant prior values are verifiable.
- **Evidence discipline:** source URLs, original document passages and no invented financial data. Fallback UI explains unavailable sources or missing LLM key.
- **Interface:** responsive Next.js and CSS, consumer-fintech palette, watchlist, alert preferences, signal detail drawer, research workspace.

## Architecture

```
Next.js / TypeScript (mobile web)
            | HTTP
       FastAPI (Python)
        /     |     \
    Postgres  AI      Public source adapters
     or      model    Yahoo chart / NSE filings /
    SQLite   API      Screener document links
               |                 |
             Evidence-grounded PDF retrieval / PyMuPDF / rules
```

**Our model strategy:** No training or fine-tuning. FINN calls a hosted Gemini or OpenAI-compatible model only when needed, with primary-source passages retrieved by Python. Calculations, comparability, signal rules and source checks remain deterministic in our code. This follows the assignment's allowance for commercial/open-source APIs and emphasis on efficient tool use.

## Run locally

Requirements: Python 3.11+, Node.js 20+ and npm. External network required to install dependencies and fetch current company data.

**Terminal A — API**

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate             # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Visit <http://localhost:8000/docs> for the API's interactive documentation.

**Terminal B — web interface**

```bash
cd apps/web
npm install
cp .env.example .env.local
npm run dev
```

Open <http://localhost:3000>. The Next.js UI defaults to API port 8000.

You can explore the **illustrative sample** before ingesting actual data. The sample is clearly labelled as fictional and has no fake source URLs.

## Connect live/cached market data

With the API configured, **from `apps/api`**:

```bash
# Refresh selected company EOD prices and public NSE filings
python -m app.cli ingest INFY
# Attempt all 18 portfolio companies; allows partial failures per ticker
python -m app.cli ingest

# Discover ORIGINAL annual report and transcript links, then index up to 2
python -m app.cli discover INFY

# If link discovery fails, manually index a verified ORIGINAL PDF document link:
python -m app.cli index INFY --kind transcript --url "https://YOUR-COMPANY-IR-DOMAIN/original-earnings-call.pdf"

# Optional: generate source-grounded management guidance comparisons
python -m app.cli promises INFY

# Optional: enrich up to four significant filing summaries using the hosted model
python -m app.cli enrich INFY

# Run checks
pytest -q
```

NSE and Screener may refuse automated access, throttle requests or change page markup. **No CAPTCHA or login bypass** is implemented; failures are reported. Yahoo Finance is an unofficial data feed, not guaranteed production access. The system should not claim real-time or continuously guaranteed alert delivery.

### Hosted AI

1. Obtain a Gemini API key using Google AI Studio (or use an OpenAI-compatible provider).
2. Set **only in `apps/api/.env`**, never in the browser:

```dotenv
GEMINI_API_KEY=YOUR_KEY
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
LLM_MODEL=gemini-2.5-flash
```

Alternatively set `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL` for another compatible provider. The `openai` Python client is used purely as the compatible API client library; the default `base_url` connects to Google Gemini, not OpenAI's hosted endpoint.

Without the key, classifications, numeric alerts, data ingestion and evidence retrieval still work. Narrative answers, structured results PDF extraction, Promise Tracker extraction and AI filing enrichment will explain that the key is required. No fake answers are substituted. Model pricing/free quotas and model names can change; verify current account eligibility before running a large ingest.

### Database

By default, local SQLite is created on first API startup. In production, supply the Supabase PostgreSQL connection URL:

```dotenv
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:PORT/postgres?sslmode=require
```

Use the connection/pooler URL published by your Supabase project. No Supabase account credentials are checked into Git. Schema is created automatically on initial startup; a simple additive migration for the `analysis_json` column is included. For a long-lived production service, replace the prototype migration method with Alembic migrations.

## Deploy

1. Create a Supabase PostgreSQL database and set `DATABASE_URL` in your API hosting service.
2. Deploy `apps/api` to a Python/Docker-capable service. Set `DATABASE_URL`, `CORS_ORIGINS=https://YOUR-WEB-DOMAIN`, and optionally `GEMINI_API_KEY` / `LLM_MODEL`.
3. Deploy `apps/web` to Vercel as the project root directory. Set `NEXT_PUBLIC_API_BASE_URL=https://YOUR-API-DOMAIN` **at build time**.
4. Confirm `/api/health`, `/api/companies`, and the document retrieval flow from the deployed browser.
5. Add GitHub Action secret `DATABASE_URL` to enable scheduled EOD refresh via `.github/workflows/ingest.yml`, monitoring logs for source errors. GitHub schedule execution timing is best effort, not a real-time alert mechanism.
6. Test the site on a phone and test a previously unseen ticker. Only provide ENAM a deployed link after real data ingestion and evidence links have been validated.

**API Docker image:** `apps/api/Dockerfile` is included. Docker hosts should configure their service port and secrets according to their provider's instructions.

## Data provenance and safety decisions

- **Push**: publicly disclosed NSE/BSE filings and EOD Yahoo prices; company filing source linked when available. NSE times are interpreted as India-local and normalized to UTC.
- **Pull**: original company annual reports, earnings call transcripts and investor presentations, discovered through document links; never use generated Screener notes, brokerage reports, or model memory as company evidence.
- **Comparisons**: do not equate annual with quarterly, standalone with consolidated, or INR crore with percent. Do not infer EBITDA from operating profit.
- **Freshness**: price-day and disclosure timestamps are shown; only ingested data appears in the live feed. Empty live results remain empty.
- **No financial advice**: this is an informational prototype, not a signal to execute trades.

## Limitations to disclose

- No live broker integration, intraday price feed, mobile OS push notifications, production user accounts or AI model training.
- Quarterly result PDFs and guidance extraction can fail when tables are scanned, poorly converted or contain ambiguous reporting bases; unsupported claims are withheld.
- Source discovery uses a public HTML link directory and may require updates when site markup changes or access is restricted.
- Initial API research/import endpoints are prototype-grade (no per-user rate limiting). Before public production use, add authentication, rate limits, strict egress allowlists and audit logs. Default admin ingestion endpoint is disabled unless an `INGEST_TOKEN` is configured.
- Running an SQL database service and long PDF jobs may require a more capable deployment than a short-lived serverless function; long operations should ultimately move to background jobs.
- ENAM requires the actual AI build history: include this ChatGPT conversation's share/export alongside repository documentation; a markdown decision log does **not** substitute for the conversation history.

## Repository map

```
apps/api/app/      FastAPI endpoints, DB models, source adapters, AI, deterministic logic
apps/api/tests/    Offline API and numerical validation
apps/web/app/      Next.js routes, consumer-fintech styles, interactive frontend
apps/web/lib/      Typed API client
apps/web/components/ Charts and reusable visual elements
.github/workflows/ Scheduled ingestion job
scripts/           Convenience scripts
docs/              Architecture, quality checks, AI decision, submission notes
```

## Verification and interview story

See [`docs/VERIFICATION.md`](docs/VERIFICATION.md), [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), and [`docs/AI_IMPLEMENTATION.md`](docs/AI_IMPLEMENTATION.md). The pitch: *FINN doesn't optimise for collecting more financial information; it makes existing original information easier to prioritise, verify and interrogate.*
