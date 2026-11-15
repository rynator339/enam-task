"""Install a dated public-data snapshot on first start, in the caller's transaction."""
import gzip
import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from .db import Company, Price, Announcement, Document, Chunk, Promise, Metric
from .logic import classify, concise_summary, compare_guidance, stable_id


def load_snapshot(db):
    folder = Path(__file__).parent / 'data'
    with gzip.open(folder / 'market-2026-11-15.json.gz', 'rt') as stream:
        market = json.load(stream)
    # Never overwrite rows from a newer refresh or from an existing installation.
    prices = set(db.execute(select(Price.ticker, Price.day)).all())
    for ticker, day, close, volume, change, multiple in market['prices']:
        if (ticker, day) not in prices:
            db.add(Price(ticker=ticker, day=day, close=close, volume=volume,
                         day_change_pct=change, volume_multiple=multiple))
    for item in market['filings']:
        if db.get(Announcement, item['id']):
            continue
        item['published_at'] = datetime.fromisoformat(item['published_at'])
        category, priority, reason = classify(item['title'], item['body'])
        db.add(Announcement(**item, category=category, priority=priority, reason=reason,
                            summary=concise_summary(item['title'], item['body'])))
    evidence = json.loads((folder / 'evidence.json').read_text())
    for item in evidence['documents']:
        ticker, url = item['ticker'], item['url']
        if not db.get(Company, ticker):
            db.add(Company(ticker=ticker, name=item['name'], sector=item['sector'], in_watchlist=False))
            db.flush()
        doc_id = stable_id(ticker, url)
        if not db.get(Document, doc_id):
            db.add(Document(id=doc_id, ticker=ticker, source_url=url, title=item['title'],
                            kind=item['kind'], status='selected passages', published_label=item['label']))
            db.flush()
        for page, passage in item['passages']:
            pk = stable_id(doc_id, page, passage)
            if not db.get(Chunk, pk):
                db.add(Chunk(id=pk, ticker=ticker, document_id=doc_id, page=page, content=passage))
    case = evidence['comparison']
    guidance, actual = [evidence['documents'][i] for i in case['document_indices']]
    fields = dict(ticker=guidance['ticker'], metric=case['metric'], unit=case['unit'],
                  period=case['period'], basis=case['basis'])
    def reference(doc):
        page, quote = doc['passages'][0]
        return dict(document_id=stable_id(doc['ticker'], doc['url']), page=page, quote=quote)
    ref, result = reference(guidance), reference(actual)
    claim_id = stable_id(ref['document_id'], ref['page'], case['metric'], case['period'], ref['quote'])
    metric_id = stable_id(result['document_id'], result['page'], case['metric'], case['period'], result['quote'])
    if not db.get(Metric, metric_id):
        db.add(Metric(id=metric_id, **fields, **result, value=case['actual']))
    if not db.get(Promise, claim_id):
        status, reason = compare_guidance(case['low'], case['high'], case['actual'], case['unit'],
                                          case['unit'], case['period'], case['period'], case['basis'], case['basis'])
        db.add(Promise(id=claim_id, **fields, **ref, target_low=case['low'], target_high=case['high'],
                       actual=case['actual'], actual_document_id=result['document_id'], actual_page=result['page'],
                       status=status, rationale='Historical comparison from reviewed source passages. ' + reason))
