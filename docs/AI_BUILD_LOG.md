# AI-assisted development log

This is a **curated chronology**, not a substitute for the actual prompts and messages. Export/share the full ChatGPT conversation as required by ENAM.

## Challenge and product decisions

- Reviewed the 8 Nov 2026 ENAM FINN challenge and its corporate-announcements/finance glossary.
- Chose a mobile-first Hybrid Signal Inbox + Promise Tracker, prioritising a single coherent investor workflow.
- User chose a balanced originality/reliability target, consumer-fintech aesthetic, Next.js + Python stack.
- Chose hosted AI through a configurable OpenAI-compatible API rather than fine-tuning or training from scratch.

## Implementation choices

- Added a verified source document store and page-level text chunks, separating extraction from interactive requests.
- Started with explainable regex category priorities, plus optional LLM refinement.
- Implemented deterministic alerts using EOD closing returns and 20 previous volume sessions.
- Added quote-validated hosted-model extractors for guidance, reported actuals and quarter results.
- UI uses four connected workspaces and explicit *illustrative* state for local/no-key exploration.

## Issues found and addressed

- First classifier unit test caught alternate wording for trading-window closure; added the missing routine classification.
- Improved volume alert baseline to require 20 previous observed sessions, avoiding unstable early comparisons.
- Corrected NSE announcement date interpretation to India-local time before storing UTC.
- Schema change for results analysis triggered an older-SQLite compatibility error; added a minimal additive migration.
- Kept failure states honest when external market sources or hosted inference are unavailable.

## Verification constraints

- Python backend tests passed (13/13).
- TypeScript / TSX source passed offline syntax parsing.
- Network unavailable in authoring environment, so package installation, real NSE/Yahoo fetching, Gemini API inference and cloud deployment were not verified.

## Next iteration candidates

- More reliable original source discovery and metadata.
- Dedicated scheduled workers rather than synchronous PDF ingestion requests.
- LLM structured-extraction evaluations against real annotated company filings.
- Better mobile QA and financial-table coverage.

## Completion pass · 15 November 2026

- Reproduced the original 13 tests and installed the existing frontend. Switched the production build to Turbopack after webpack compilation stalled on the verification machine. The static export and API were exercised from the same origin.
- Pulled three months of Yahoo observations and a 14-day NSE filing window for all 18 holdings. Compared stricter and looser alert settings against the same saved dates and followed filing links to PDF responses.
- Live TRENT discovery exposed a presentation mislabelled as a transcript. Classification now uses the specific document link label. Rechecked annual reports, transcripts and presentations for companies outside the portfolio.
- Read the Infosys earnings transcript and annual-report shareholder letter, confirmed each excerpt on its original PDF page, and kept a reviewed case usable without a key.
- Added regression coverage for the saved window, excluded unknown reporting bases, quote/number mismatches, and invalid provider citations. Used the real OpenAI-compatible client against a simulated response for the contract test.
- Verified the investor-facing navigation, filters, threshold controls, evidence, and watchlist in the production browser UI at 390 px. The user chose evidence-only operation and repository-based deployment handoff.
