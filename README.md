# FINN | Signal Inbox + Promise Tracker

A mobile-first research desk for an 18-company Indian equity watchlist. Review original NSE filings and unusual closing prices or volumes, open a company's research view, then check whether management delivered on its guidance.

## Try the two-minute demo

1. Open **Today → Latest saved week** in the period selector. The first screen otherwise uses the last 24 hours, which can be quiet on weekends. Focused shows high- and medium-priority events. All includes routine filings. Open a filing card to see its source and investigate the company.
2. In **Settings**, change the price and volume thresholds. Apply a custom window and choose **Market activity**. Alerts use the absolute close-to-close return or volume divided by the preceding 20 sessions' average. Preferences are saved in the browser. Alerts arrive in the inbox after data refresh.
3. Select **Compare the evidence** on Today. Infosys guided to a 20–22% FY2025 operating margin and reported 21.1%. The historical Promise Tracker record links the guidance and actual to different original PDF pages. Ask the prefilled question to see both passages. [Earnings call, PDF p. 4](https://www.infosys.com/investors/reports-filings/quarterly-results/2023-2024/q4/documents/transcripts/earningscall.pdf#page=4) · [Annual report shareholder letter, PDF p. 1](https://www.infosys.com/investors/reports-filings/annual-report/annual/documents/2024-25/letter-to-the-shareholder.pdf#page=1)
4. Try **HAL**, **PERSISTENT** or **TRENT** for short, original-document examples outside the portfolio. For a new NSE ticker, type the symbol, open its workspace, then select **Discover & index original sources**. Availability depends on the original PDF.

The first launch loads a genuine dated snapshot collected on 15 November 2026. It contains 1,134 Yahoo daily observations and 103 NSE filings. The saved-week filter ends at the latest cached event. The Infosys comparison is manually source-reviewed and its verdict is calculated in Python. A hosted key is optional. Without one, research returns cited passages and the reviewed comparison. Fictional interface examples are accessible only through an explicitly labelled preview.

## Run locally

Use Python 3.12 and Node.js 22+ with npm. Run the following from the repository root in two terminals.

**API**

```sh
cd apps/api
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000
```

**Web**

```sh
cd apps/web
npm ci
npm run dev
```

Open [the local app](http://localhost:3000) or [API health](http://localhost:8000/api/health). SQLite is created automatically. The default two-process setup needs no environment files. To test the production UI in this setup, run `npm run build && npm start` in the web directory after stopping the development frontend.

## Publish or run as one service

The root Dockerfile exports the existing Next.js frontend and serves it from the existing FastAPI process. This gives a phone one origin for the entire app. Render deployment steps, persistence options and post-deployment checks are in [DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Refresh and discover

From `apps/api` in the activated virtual environment:

```sh
python -m app.cli ingest INFY
python -m app.cli ingest
python -m app.cli discover COFORGE
python -m app.cli --help
python -m pytest -q
```

NSE and Yahoo adapters keep original URLs or instrument identifiers, trading dates and disclosure times. Repeated refreshes reuse existing records. Screener is a directory for finding primary documents. The indexer downloads the linked PDF, extracts page text and retains the PDF page number. The packaged ad-hoc examples contain selected passages. Discovery can expand them into a larger index.

## Optional hosted research

Set `GEMINI_API_KEY` or `LLM_API_KEY`, `LLM_BASE_URL` and a provider-supported `LLM_MODEL` in the API host's secrets or an ignored `apps/api/.env`. Restart the API. The example config shows the Gemini-compatible base URL. For a different provider supply its compatible endpoint and model. No training or fine-tuning takes place.

The API retrieves ticker-scoped passages, sends them with the question and validates the returned citation identifiers. Extraction checks quoted text and numbers. Calculations and comparisons stay in Python. A citation check cannot establish that every sentence is entailed by the page. Provider authentication, model availability, and the quality of actual hosted output still require a live-key test.

## Implementation and evidence

- [Verified runs and limits](docs/VERIFICATION.md)
- [Architecture](docs/ARCHITECTURE.md) and [AI implementation](docs/AI_IMPLEMENTATION.md)
- [Build decisions and log](docs/AI_BUILD_LOG.md)
- [Submission instructions and email draft](docs/SUBMISSION_NOTES.md)

`apps/api/app` contains source adapters, SQLite/PostgreSQL models, the passage index and endpoints. `apps/web` contains the Next.js mobile interface. The dated snapshot is stored under `apps/api/app/data`. This prototype has no trading integration, intraday monitoring, user accounts or mobile OS notifications.
