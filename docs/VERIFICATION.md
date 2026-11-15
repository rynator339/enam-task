# Verification record · 15 November 2026

The supplied archive passed its original 13 backend tests before edits. The corrected code passed 19 backend tests in an isolated SQLite database. Six non-failing library deprecation warnings came from the test client and PDF bindings.

| Check | Result from this completion pass |
| --- | --- |
| Production frontend | npm dependencies installed, TypeScript checked, Next.js 15.5.29 Turbopack production export completed. FastAPI served that export and its JSON routes on one local origin. |
| Market ingestion | Yahoo returned 63 daily rows per company for all 18 holdings, covering 13 August–13 November 2026. NSE returned 103 filings across all 18 in the 14-day query. Two repeat INFY refreshes against the seeded database inserted zero duplicate prices or filings. |
| Provenance | Opened exchange-returned attachments for INFY, TCS, DRREDDY and BHARTIARTL and confirmed HTTP 200 and PDF signatures. Read the 12 November Infosys press-release cover letter. Two of the 103 filings lack an attachment and display a missing-source state. Other individual attachments were not all inspected. |
| Signal Inbox | The saved week ending 14 November at 16:55:23 IST had 29 filings and three default market alerts. At 0.5% and 1× it yielded 55 market alerts. At 10% and 5× it yielded zero. Regression tests also exercise exact cutoffs, multiple sessions and separate illustrative data. |
| Source discovery | Downloaded original reports, call transcripts or presentations for TRENT, HAL and PERSISTENT. Identified and fixed PPT links being classified as transcripts. Replayed the unfamiliar ticker COFORGE and indexed a 23-page transcript and the first 180 pages of an annual report. A research query returned six citations. |
| Historical comparison | Verified the Infosys FY2025 operating margin forecast in its 18 April 2024 earnings call, PDF p. 4. Verified the 21.1% actual in the original FY2025 shareholder letter, PDF p. 1. Python returned met for the 20–22% range. These reviewed values are a curated input, independent of live model extraction. |
| Mobile browser | Exercised the actual production UI and local API in a 390 CSS-pixel viewport. Reviewed Today and the ranked saved week, opened an HDFC Bank filing drawer and investigated the company, selected INFY and TRENT, asked a question and saw both INFY excerpts, filtered the watchlist, changed both sliders and applied a custom ten-day window. The resulting market filter showed 81 breaches at the tested settings of 0.5% and 5×. Research had no horizontal overflow at this width. |
| Hosted-model boundary | The actual compatible client was tested against a simulated provider. The test checks ticker-scoped prompt contents, accepts a valid citation and falls back to source passages for an invalid citation. No provider key was supplied or requested for the final run. |
| Delivery | Git checkout with baseline and corrected code, source archive, deployment recipe, verification notes and covering email. Public hosting, remote GitHub push and delivery of the email remain manual. |

## Reproduce

Run `python -m pytest -q` in `apps/api` with its requirements installed. In `apps/web`, run `npm ci`, `npm run typecheck` and `npm run build`. The saved week reproduces the counts above on the supplied snapshot even after the current 24-hour window moves on. Fresh data changes the reference date and counts.

## Limits

- Real hosted inference, automatic live guidance/quarterly-result extraction quality, and production quotas remain untested. A quote or citation identifier check does not guarantee semantic accuracy. Evidence-only research exposes the passages themselves.
- Docker engine, cloud deployment, PostgreSQL, scheduled GitHub execution, physical iOS/Android devices and OS notifications were outside the verified run. Production UI and API were tested together locally.
- The scheduler is best-effort. The saved EOD timestamp convention is 15:30 IST on the session date. Special exchange sessions can have different close times. Yahoo provides historical daily bars, and corporate actions can affect close-to-close comparisons.
- Discovery depends on exchange availability and machine-readable PDFs. Import limits are configurable in bytes and cap processing at the first 180 PDF pages. Scanned pages may contribute no text.
