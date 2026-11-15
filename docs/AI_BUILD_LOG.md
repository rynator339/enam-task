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
