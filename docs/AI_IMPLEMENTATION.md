# How FINN uses AI — no custom model training

## Decision

Use a **hosted LLM** as a narrow language/reasoning component of a larger deterministic financial-intelligence system. Default: Gemini through its documented OpenAI-compatible API. Provider can be replaced through `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL` without changing the product.

Reasons not to train a model: (1) no proprietary labeled dataset in the brief, (2) not enough time/compute to justify pretraining, (3) high hallucination and maintenance risk, and (4) general models already handle classification, structured JSON and comparative reasoning. ENAM values product judgment and efficiency, not standalone weights.

## AI tasks

| Task | Method | AI needed? | Source limits |
|---|---|---|---|
| EOD price and volume anomaly | Formula over cached EOD data | No | Yahoo Finance EOD |
| Filing deduplication | Hashes / NSE IDs | No | Raw NSE disclosure |
| Basic filing category | Explicit regex precedence | No | Disclosure title and text |
| Filing first-cut summary | Optional hosted LLM (`cli enrich`) | Yes | Only text from the original exchange disclosure |
| Company research Q&A | Keyword-ranked passages + hosted LLM | Yes | Indexed original annual reports/transcripts |
| Numeric guidance extraction | Prompted JSON + exact quote/page and number checks | Yes | Original transcript only |
| Financial actuals extraction | Prompted JSON + exact quote/page and number checks | Yes | Annual reports / original results documents |
| Guidance versus actual verdict | Unit/basis/period validation + Python arithmetic | No | Two independently verified records |
| Quarterly results analysis | PDF parsing + hosted structured extractor; deterministic QoQ/YoY | Yes for PDF rows | Original exchange result PDF |

## Retrieval pipeline

1. Dynamic ticker selection (any syntactically valid NSE symbol).
2. Discover original document links using Screener as a **directory only**; the model receives neither Screener-generated summaries nor broker notes.
3. Download original PDF and extract page-level text with PyMuPDF, retaining URL/page metadata.
4. Split into 2300-character evidence chunks, index by company and document, select relevant passages by keyword ranking.
5. Send only those passages and question to the hosted model under a strict system prompt that forbids external knowledge.
6. Return answer together with URLs and page citations. On missing source or model failure, show errors/evidence-only state instead of inventing analysis.

## Promise Tracker controls

- Model output includes `metric`, `period`, `target_low`, `target_high`, `unit`, `basis`, an **exact quote**, document ID and page.
- Reject numeric guidance if it has no explicit period, no numeric limit, or if the quote does not appear in the extracted page.
- Actual figures undergo equivalent quote verification.
- Compare only the same metric, fiscal period, unit and compatible reporting basis. Otherwise verdict is `unverifiable`, or `pending` if no actual exists.
- Comparisons are `met` / `missed` / `pending` / `unverifiable`. We do **not** call them trading recommendations.

## Cost

- Calculations and the first pass of classification don't consume LLM tokens.
- `cli enrich` intentionally caps filings per company at four per run, caches generated text, and does not re-enrich unchanged records.
- Previously indexed PDFs, passages and extracted metrics are stored.
- Use a small model for structured bulk extraction, reserve higher-end model calls for difficult ambiguous research only if accuracy warrants the added expense.
- Free-tier availability depends on the actual Gemini account/usage tier; do not treat free as a guarantee.

## Future improvements

1. OCR fallback only for scanned document pages, with clear extraction confidence.
2. Embedding-based retrieval and cross-encoder ranking for better multi-year evidence recall.
3. Source excerpt highlights / page-level deep links and stronger financial table extraction.
4. Automated quality evaluation sets for extraction and cross-period comparability.
5. Bounded worker queues, per-request cost budgeting, source freshness checks and observability.

## Assessment mode

The shipped Infosys case uses two manually checked original passages and a Python verdict. HAL, PERSISTENT and TRENT have selected company-specific passages. Full PDF discovery remains available for these and additional tickers. No live hosted inference was performed in the completion pass. The provider receives at most six ticker-scoped passages for research. Responses with missing or out-of-set citation identifiers fall back to evidence-only mode.
