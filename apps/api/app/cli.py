"""Public-data refresh commands. python -m app.cli ingest | discover INFY | promises INFY"""
import argparse,sys,json
from .db import init_db,SessionLocal,PORTFOLIO
from . import service

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['ingest','discover','promises','enrich','index']);p.add_argument('ticker',nargs='?',default='');p.add_argument('--days',type=int,default=14);p.add_argument('--url',default='');p.add_argument('--kind',choices=['transcript','annual_report','presentation','results'],default='transcript');a=p.parse_args()
    init_db();tickers=[a.ticker.upper()] if a.ticker else [item[0] for item in PORTFOLIO]
    failed=False
    with SessionLocal() as db:
        for ticker in tickers:
            outcome={'ticker':ticker}
            if a.action=='ingest':
                for kind,fn in [('prices',lambda:service.ingest_prices(db,ticker)),('filings',lambda:service.ingest_filings(db,ticker,a.days))]:
                    try:outcome[kind]=fn()
                    except Exception as e:db.rollback();outcome[kind]={'error':str(e)[:220]}
            elif a.action=='discover':
                try:outcome=service.discover_and_index(db,ticker,max_docs=2)
                except Exception as e:outcome['error']=str(e)[:220]
            elif a.action=='index':
                if not a.ticker or not a.url:
                    p.error('index requires a ticker and an --url original company PDF source')
                try:
                    service.ensure_company(db,ticker)
                    doc,n=service.store_document(db,ticker,{'kind':a.kind,'title':f'{ticker} {a.kind.replace("_"," " )} original document','source_url':a.url,'published_label':'Direct source PDF'})
                    outcome.update({'document_id':doc.id,'pages':n,'source_url':doc.source_url})
                except Exception as e:outcome['error']=str(e)[:220]
            elif a.action=='enrich':
                try:outcome=service.enrich_filings(db,ticker,max_items=4)
                except Exception as e:outcome['error']=str(e)[:220]
            elif a.action=='promises':
                try:outcome=service.run_promise_extraction(db,ticker)
                except Exception as e:outcome['error']=str(e)[:220]
            failed |= 'error' in outcome or any(isinstance(v,dict) and 'error' in v for v in outcome.values())
            if 'documents' in outcome and not any(d['status']=='indexed' for d in outcome['documents']):
                failed=True
            db.rollback()
            print(json.dumps(outcome,ensure_ascii=False))
    return int(failed)
if __name__=='__main__':sys.exit(main())
