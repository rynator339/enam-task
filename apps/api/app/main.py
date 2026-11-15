"""FINN FastAPI service. Python 3.11+; SQLite dev / PostgreSQL production."""
import os, re, secrets, logging, json
from datetime import datetime,timedelta,timezone
from contextlib import asynccontextmanager
from typing import Literal
from fastapi import FastAPI, Depends, HTTPException, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from .db import init_db,get_db,Company,Price,Announcement,Document,Chunk,Promise,Metric,SessionLocal
from .logic import CATEGORIES
from . import ai,service

LOG=logging.getLogger('finn')
@asynccontextmanager
async def lifespan(app:FastAPI):
    init_db();yield

app=FastAPI(title='FINN Investor Intelligence API',version='0.1.0',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=[v.strip() for v in os.getenv('CORS_ORIGINS','http://localhost:3000').split(',') if v.strip()],allow_methods=['GET','POST'],allow_headers=['*'])

SAMPLES=[
 {'id':'demo-1','ticker':'INFY','company':'Infosys','title':'Quarterly results worth comparing with past guidance','summary':'Example: management discusses sales and margin performance. Open the original filing and compare reported outcomes with prior expectations.','reason':'Example of a high-priority results event; illustrative content only.','category':'results','priority':'high','offset':2},
 {'id':'demo-2','ticker':'LT','company':'Larsen & Toubro','title':'Large order announcement requires materiality review','summary':'Example: an order-win disclosure is assessed using disclosed size, segment importance and potential revenue visibility.','reason':'Illustrative contract/order event; the underlying deal is not a real filing.','category':'press_release','priority':'medium','offset':6},
 {'id':'demo-3','ticker':'HDFCBANK','company':'HDFC Bank','title':'Management change merits closer inspection','summary':'Example: investigate a hypothetical executive appointment, responsibilities and background.','reason':'An executive change may be material; this is an illustrative example.','category':'management_change','priority':'high','offset':9},
 {'id':'demo-4','ticker':'RELIANCE','company':'Reliance Industries','title':'Unusual price and volume activity','summary':'Example alert: daily close crosses a selected price threshold while traded volume is above the recent average.','reason':'Illustrative threshold breach, not measured live market activity.','category':'market_move','priority':'medium','offset':12},
 {'id':'demo-5','ticker':'TCS','company':'Tata Consultancy Services','title':'Routine compliance filing','summary':'Example of a standard filing retained but collapsed so it does not crowd out material events.','reason':'Routine filings are available for audit even when hidden from the default view.','category':'unclassified','priority':'low','offset':14},
]

def demo_items():
    now=datetime.now(timezone.utc)
    return [{**{k:v for k,v in s.items() if k!='offset'},'published_at':(now-timedelta(hours=s['offset'])).isoformat(),'source_url':None,'is_illustrative':True,'type':'filing' if s['category']!='market_move' else 'price'} for s in SAMPLES]

def validate_ticker(value:str)->str:
    val=value.upper().strip().removesuffix('.NS')
    if not re.fullmatch(r'[A-Z0-9&_-]{1,25}',val):raise HTTPException(422,'Enter a valid NSE symbol (for example INFY).')
    return val

def company_dict(c:Company,latest:Price|None=None):
    return {'ticker':c.ticker,'name':c.name,'sector':c.sector,'in_watchlist':c.in_watchlist,'close':latest.close if latest else None,'day_change_pct':latest.day_change_pct if latest else None,'volume_multiple':latest.volume_multiple if latest else None,'price_day':latest.day if latest else None}

@app.get('/api/health')
def health(db:Session=Depends(get_db)):
    return {'status':'ok','database':'connected','ai_configured':ai.llm_ready(),'ai_model':os.getenv('LLM_MODEL','gemini-2.5-flash') if ai.llm_ready() else None,'company_count':db.query(Company).count(),'announcement_count':db.query(Announcement).count(),'document_count':db.query(Document).count(),'data_mode':'live/cached if sourced; illustrative sample available separately'}

@app.get('/api/companies')
def list_companies(watchlist:bool=True,db:Session=Depends(get_db)):
    q=select(Company).order_by(Company.ticker)
    if watchlist:q=q.where(Company.in_watchlist.is_(True))
    companies=db.execute(q).scalars().all()
    result=[]
    for c in companies:
        p=db.execute(select(Price).where(Price.ticker==c.ticker).order_by(Price.day.desc()).limit(1)).scalar_one_or_none()
        result.append(company_dict(c,p))
    return {'companies':result,'count':len(result)}

@app.get('/api/companies/{ticker}')
def get_company(ticker:str,db:Session=Depends(get_db)):
    ticker=validate_ticker(ticker)
    c=db.get(Company,ticker)
    if c is None:c=service.ensure_company(db,ticker)
    price=db.execute(select(Price).where(Price.ticker==ticker).order_by(Price.day.desc()).limit(1)).scalar_one_or_none()
    documents=db.execute(select(Document).where(Document.ticker==ticker).order_by(Document.fetched_at.desc())).scalars().all()
    metrics=db.execute(select(Metric).where(Metric.ticker==ticker).order_by(Metric.period.desc()).limit(30)).scalars().all()
    return {**company_dict(c,price),'documents':[{'id':d.id,'title':d.title,'kind':d.kind,'url':d.source_url,'published_label':d.published_label,'status':d.status} for d in documents],'metrics':[{'id':m.id,'metric':m.metric,'period':m.period,'value':m.value,'unit':m.unit,'basis':m.basis,'page':m.page,'document_id':m.document_id} for m in metrics],'is_live_data':bool(price or documents)}

@app.get('/api/companies/{ticker}/prices')
def get_prices(ticker:str,limit:int=Query(60,ge=1,le=365),db:Session=Depends(get_db)):
    ticker=validate_ticker(ticker)
    rows=db.execute(select(Price).where(Price.ticker==ticker).order_by(Price.day.desc()).limit(limit)).scalars().all()
    return {'ticker':ticker,'prices':[{'day':p.day,'close':p.close,'volume':p.volume,'day_change_pct':p.day_change_pct,'volume_multiple':p.volume_multiple} for p in reversed(rows)],'is_live_data':bool(rows)}

@app.get('/api/feed')
def get_feed(window_hours:int=Query(24,ge=1,le=24*365),priority:str='all',category:str='all',price_threshold:float=Query(3.0,ge=0.1,le=50),volume_threshold:float=Query(2.0,ge=1,le=25),demo:bool=False,db:Session=Depends(get_db)):
    if demo:
        data=demo_items()
    else:
        cutoff=datetime.now(timezone.utc)-timedelta(hours=window_hours)
        records=db.execute(select(Announcement,Company).join(Company,Company.ticker==Announcement.ticker).where(Announcement.published_at>=cutoff,Company.in_watchlist.is_(True)).order_by(Announcement.published_at.desc()).limit(2500)).all()
        data=[{'id':a.id,'ticker':a.ticker,'company':c.name,'title':a.title,'summary':a.summary,'reason':a.reason,'category':a.category,'priority':a.priority,'published_at':a.published_at.isoformat(),'source_url':a.source_url,'source':a.source,'is_illustrative':False,'type':'filing'} for a,c in records]
        companies=db.execute(select(Company).where(Company.in_watchlist.is_(True))).scalars().all()
        for c in companies:
            p=db.execute(select(Price).where(Price.ticker==c.ticker).order_by(Price.day.desc()).limit(1)).scalar_one_or_none()
            if not p or (datetime.now(timezone.utc).date()-datetime.fromisoformat(p.day).date()).days>max(1,(window_hours+23)//24):continue
            moves=[]
            if p.day_change_pct is not None and abs(p.day_change_pct)>=price_threshold:moves.append(f'{p.day_change_pct:+.2f}% close-to-close move vs {price_threshold:g}% threshold')
            if p.volume_multiple is not None and p.volume_multiple>=volume_threshold:moves.append(f'{p.volume_multiple:.2f}× prior-session average volume vs {volume_threshold:g}× threshold')
            if moves:
                published=datetime.fromisoformat(p.day).replace(hour=18,tzinfo=timezone.utc)
                data.append({'id':f'price-{p.ticker}-{p.day}','ticker':c.ticker,'company':c.name,'title':'Unusual end-of-day market activity','summary':'; '.join(moves)+'.','reason':'Deterministic alert based on reported EOD prices/volumes; not intraday monitoring.','category':'market_move','priority':'medium','published_at':published.isoformat(),'source_url':f'https://finance.yahoo.com/quote/{c.ticker}.NS/history/','source':'Yahoo Finance EOD','is_illustrative':False,'type':'price'})
    if priority!='all':data=[x for x in data if x['priority']==priority]
    if category!='all':data=[x for x in data if x['category']==category]
    ranking={'high':3,'medium':2,'low':1}
    data.sort(key=lambda x:(ranking.get(x['priority'],0),x['published_at']),reverse=True)
    return {'items':data,'count':len(data),'illustrative':demo,'window_hours':window_hours,'high':sum(x['priority']=='high' for x in data),'medium':sum(x['priority']=='medium' for x in data),'low':sum(x['priority']=='low' for x in data)}

@app.get('/api/signals/{signal_id}')
def get_signal(signal_id:str,db:Session=Depends(get_db)):
    if signal_id.startswith('demo-'):
        match=next((x for x in demo_items() if x['id']==signal_id),None)
        if not match:raise HTTPException(404,'Sample signal not found')
        return match
    a=db.get(Announcement,signal_id)
    if a:return {'id':a.id,'ticker':a.ticker,'title':a.title,'summary':a.summary,'body':a.body,'category':a.category,'priority':a.priority,'reason':a.reason,'published_at':a.published_at.isoformat(),'source_url':a.source_url,'source':a.source,'is_illustrative':False,'results_analysis':json.loads(a.analysis_json) if a.analysis_json else None}
    if signal_id.startswith('price-'):
        parts=signal_id.split('-')
        if len(parts)<5:raise HTTPException(404,'Signal not found')
        ticker=parts[1];day='-'.join(parts[2:])
        p=db.execute(select(Price).where(Price.ticker==ticker,Price.day==day)).scalar_one_or_none()
        if p:return {'id':signal_id,'ticker':ticker,'title':'Unusual end-of-day market activity','summary':f'{p.day_change_pct}% price change; {p.volume_multiple}× volume.','category':'market_move','priority':'medium','reason':'Computed against thresholds selected in the feed.','published_at':day,'source_url':f'https://finance.yahoo.com/quote/{ticker}.NS/history/','source':'Yahoo Finance EOD','is_illustrative':False}
    raise HTTPException(404,'Signal not found')

class ResearchRequest(BaseModel):
    ticker:str=Field(min_length=1,max_length=28)
    question:str=Field(min_length=3,max_length=800,default='What are the key risks and recent business trends according to the company reports?')

@app.post('/api/research')
def research(request:ResearchRequest,db:Session=Depends(get_db)):
    ticker=validate_ticker(request.ticker)
    service.ensure_company(db,ticker)
    chunks=service.get_relevant_chunks(db,ticker,request.question)
    if not chunks:
        return {'ticker':ticker,'answer':'No original company documents have been indexed. Select Discover & index documents before asking FINN.','citations':[],'ai_generated':False,'needs_documents':True}
    citations=[{'title':c['title'],'page':c['page'],'url':c['source_url'],'document_id':c['document_id'],'excerpt':c['content'][:250]} for c in chunks[:6]]
    if ai.llm_ready():
        try:
            answer=ai.answer_question(request.question,chunks)
            return {'ticker':ticker,'answer':answer,'citations':citations,'ai_generated':True,'needs_documents':False}
        except Exception as ex:
            LOG.warning('LLM failed: %s',ex)
            return {'ticker':ticker,'answer':'The AI provider could not complete this answer. Original passages are available below; no narrative analysis has been fabricated.','citations':citations,'ai_generated':False,'needs_documents':False,'error':str(ex)[:200]}
    return {'ticker':ticker,'answer':'Primary-source passages were retrieved successfully. Connect a hosted-model API key to receive a concise evidence-grounded analysis.','citations':citations,'ai_generated':False,'needs_documents':False}

@app.post('/api/companies/{ticker}/discover')
def discover(ticker:str,db:Session=Depends(get_db)):
    ticker=validate_ticker(ticker)
    try:return service.discover_and_index(db,ticker,max_docs=2)
    except Exception as e:raise HTTPException(502,f'Primary document discovery unavailable: {str(e)[:220]}')

@app.get('/api/companies/{ticker}/promises')
def get_promises(ticker:str,db:Session=Depends(get_db)):
    ticker=validate_ticker(ticker)
    rows=db.execute(select(Promise).where(Promise.ticker==ticker).order_by(Promise.created_at.desc())).scalars().all()
    docs={d.id:d for d in db.execute(select(Document).where(Document.ticker==ticker)).scalars().all()}
    return {'ticker':ticker,'promises':[{'id':p.id,'metric':p.metric,'period':p.period,'target_low':p.target_low,'target_high':p.target_high,'unit':p.unit,'basis':p.basis,'quote':p.quote,'page':p.page,'source_url':docs[p.document_id].source_url if p.document_id in docs else None,'actual':p.actual,'actual_url':docs[p.actual_document_id].source_url if p.actual_document_id in docs else None,'actual_page':p.actual_page,'status':p.status,'rationale':p.rationale} for p in rows],'count':len(rows)}

@app.post('/api/companies/{ticker}/analyze-promises')
def analyze_promises(ticker:str,db:Session=Depends(get_db)):
    ticker=validate_ticker(ticker)
    try:return service.run_promise_extraction(db,ticker)
    except Exception as e:raise HTTPException(502,f'AI extraction could not finish: {str(e)[:230]}')

@app.post('/api/admin/ingest/{ticker}')
def ingest(ticker:str,authorization:str|None=Header(default=None),db:Session=Depends(get_db)):
    token=os.getenv('INGEST_TOKEN')
    if not token or not authorization or not secrets.compare_digest(authorization,f'Bearer {token}'):
        raise HTTPException(403,'Admin ingestion requires a correctly configured INGEST_TOKEN.')
    ticker=validate_ticker(ticker)
    result={'ticker':ticker,'prices':None,'filings':None,'errors':[]}
    for name,fn in [('prices',lambda:service.ingest_prices(db,ticker)),('filings',lambda:service.ingest_filings(db,ticker,days=21))]:
        try:result[name]=fn()
        except Exception as e:result['errors'].append(f'{name}: {str(e)[:170]}')
    return result


@app.post('/api/signals/{signal_id}/analyze-results')
def analyze_quarterly_results(signal_id:str,db:Session=Depends(get_db)):
    try:return service.run_results_analysis(db,signal_id)
    except ValueError as e:raise HTTPException(422,str(e))
    except Exception as e:raise HTTPException(502,f'Could not extract filing results: {str(e)[:210]}')
