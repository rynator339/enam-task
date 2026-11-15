from datetime import datetime,timedelta,timezone
from sqlalchemy.orm import Session
from sqlalchemy import select,func
from .db import Company,Price,Announcement,Document,Chunk,Metric,Promise,utcnow
from .logic import stable_id,classify,concise_summary,price_stats,compare_guidance,keyword_score
from . import sources,ai

def ensure_company(db:Session,ticker:str)->Company:
    ticker=ticker.upper()
    c=db.get(Company,ticker)
    if not c:
        c=Company(ticker=ticker,name=ticker,sector='Unclassified',in_watchlist=False)
        db.add(c);db.commit()
    return c

def ingest_prices(db:Session,ticker:str)->int:
    records=sources.fetch_market_prices(ticker)
    if not records:raise ValueError(f'No price rows returned for {ticker}')
    inserted=0
    closes=[]; volumes=[]
    for item in sorted({r['day']: r for r in records}.values(), key=lambda r:r['day']):
        closes.append(item['close']);volumes.append(item['volume'])
        change,mult=price_stats(closes,volumes)
        row=db.execute(select(Price).where(Price.ticker==ticker,Price.day==item['day'])).scalar_one_or_none()
        if row is None:
            row=Price(ticker=ticker,day=item['day'],close=item['close'],volume=item['volume'])
            db.add(row);inserted+=1
        row.close=item['close'];row.volume=item['volume'];row.day_change_pct=change if change is not None else row.day_change_pct;row.volume_multiple=mult if mult is not None else row.volume_multiple
    db.commit();return inserted

def ingest_filings(db:Session,ticker:str,days:int=14)->int:
    records=sources.fetch_nse_announcements(ticker,days)
    count=0
    seen=set()
    for a in records:
        if a['ticker'].upper()!=ticker:continue
        category,priority,reason=classify(a['title'],a['body'])
        k=stable_id(ticker,a['source_id'] or a['published_at'].isoformat(),a['title'],a['source_url'])
        if k in seen or db.get(Announcement,k):continue
        seen.add(k)
        db.add(Announcement(id=k,ticker=ticker,title=a['title'][:600],body=a['body'],category=category,priority=priority,reason=reason,summary=concise_summary(a['title'],a['body']),published_at=a['published_at'],source_url=a['source_url'],source=a['source']))
        count+=1
    db.commit();return count

def store_document(db:Session,ticker:str,entry:dict)->tuple[Document,int]:
    doc_id=stable_id(ticker,entry['source_url'])
    existing=db.get(Document,doc_id)
    if existing and existing.status=='indexed':
        return existing,db.query(Chunk.page).filter(Chunk.document_id==doc_id).distinct().count()
    pages=sources.fetch_pdf_pages(entry['source_url'])
    if existing:
        doc=existing
    else:
        doc=Document(id=doc_id,ticker=ticker,kind=entry['kind'],title=entry['title'],source_url=entry['source_url'],published_label=entry.get('published_label',''))
        db.add(doc)
        db.flush()
    for page,content in pages:
        for pos in range(0,len(content),2300):
            section=content[pos:pos+2450]
            chunk_id=stable_id(doc_id,page,pos)
            if not db.get(Chunk,chunk_id):db.add(Chunk(id=chunk_id,document_id=doc_id,ticker=ticker,page=page,content=section))
    doc.status='indexed';doc.error=None;doc.fetched_at=utcnow()
    db.commit()
    return doc,len(pages)

def discover_and_index(db:Session,ticker:str,max_docs:int=2)->dict:
    ensure_company(db,ticker)
    entries=sources.discover_company_documents(ticker)
    # Prefer recent transcript + annual report; keep originals, never screener notes.
    selected=[]
    for kind in ('transcript','annual_report','presentation'):
        selected.extend([entry for entry in entries if entry['kind']==kind][:1])
        if len(selected)>=max_docs:break
    outcome=[]
    for entry in selected[:max_docs]:
        try:
            doc,n=store_document(db,ticker,entry)
            outcome.append({'title':doc.title,'kind':doc.kind,'status':'indexed','pages':n,'url':doc.source_url})
        except Exception as ex:
            outcome.append({'title':entry['title'],'kind':entry['kind'],'status':'failed','error':str(ex)[:260],'url':entry['source_url']})
    return {'ticker':ticker,'discovered_count':len(entries),'documents':outcome}

def get_relevant_chunks(db:Session,ticker:str,question:str,limit:int=8)->list[dict]:
    entries=db.execute(select(Chunk,Document).join(Document,Document.id==Chunk.document_id).where(Chunk.ticker==ticker).limit(3500)).all()
    ranked=[]
    for chunk,doc in entries:
        s=keyword_score(question,chunk.content)
        ranked.append((s,{'page':chunk.page,'content':chunk.content,'title':doc.title,'source_url':doc.source_url,'document_id':doc.id,'kind':doc.kind}))
    ranked.sort(key=lambda p:p[0],reverse=True)
    return [entry for score,entry in ranked[:limit] if score>0] or [entry for score,entry in ranked[:min(3,limit)]]

def run_promise_extraction(db:Session,ticker:str)->dict:
    if not ai.llm_ready():return {'extracted':0,'actuals':0,'error':'Configure GEMINI_API_KEY or LLM_API_KEY in the backend environment first.'}
    docs=db.execute(select(Document).where(Document.ticker==ticker,Document.status=='indexed')).scalars().all()
    if not docs:return {'extracted':0,'actuals':0,'error':'Index an original company earnings-call transcript or annual report first.'}
    total_guidance=0; total_actuals=0
    for doc in docs:
        chunks=db.execute(select(Chunk).where(Chunk.document_id==doc.id).order_by(Chunk.page)).scalars().all()
        pages_map={}
        for c in chunks:pages_map[c.page]=(pages_map.get(c.page,'')+' '+c.content).strip()
        if doc.kind=='transcript':
            keys=('guidance','expect','target','outlook','capex','margin','growth')
            page_candidates=[{'page':p,'content':s} for p,s in pages_map.items() if any(k in s.lower() for k in keys)][:9]
            for item in ai.extract_guidance(ticker,page_candidates):
                pk=stable_id(doc.id,item['page'],item['metric'],item['period'],item['quote'])
                if db.get(Promise,pk):continue
                db.add(Promise(id=pk,ticker=ticker,document_id=doc.id,**item));total_guidance+=1
        if doc.kind in ('annual_report','results','presentation'):
            keys=('financial highlights','revenue','ebitda','profit after tax','capital expenditure','growth')
            page_candidates=[{'page':p,'content':s} for p,s in pages_map.items() if any(k in s.lower() for k in keys)][:10]
            for item in ai.extract_actuals(ticker,page_candidates):
                pk=stable_id(doc.id,item['page'],item['metric'],item['period'],item['quote'])
                if db.get(Metric,pk):continue
                db.add(Metric(id=pk,ticker=ticker,document_id=doc.id,**item));total_actuals+=1
    db.commit()
    promises=db.execute(select(Promise).where(Promise.ticker==ticker)).scalars().all()
    actuals=db.execute(select(Metric).where(Metric.ticker==ticker)).scalars().all()
    for p in promises:
        matched=[m for m in actuals if m.metric==p.metric and m.period.upper()==p.period.upper()]
        p.actual = p.actual_document_id = p.actual_page = None
        if not matched:
            p.status, p.rationale = 'pending', 'No comparable reported value found yet.'
            continue
        comparable = [m for m in matched if m.unit.lower()==p.unit.lower() and m.basis==p.basis]
        if len({m.value for m in comparable}) > 1:
            p.status, p.rationale = 'unverifiable', 'Conflicting reported values require review.'
            continue
        # Prefer comparable units + accounting basis; don't use newest unrelated period.
        m=next((m for m in matched if m.unit.lower()==p.unit.lower() and m.basis==p.basis),matched[0])
        p.status,p.rationale=compare_guidance(p.target_low,p.target_high,m.value,p.unit,m.unit,p.period,m.period,p.basis,m.basis)
        if p.status in {'met','missed'}:
            p.actual=m.value;p.actual_document_id=m.document_id;p.actual_page=m.page
    db.commit()
    return {'extracted':total_guidance,'actuals':total_actuals,'total_promises':len(promises),'verdicts':sum(p.status in {'met','missed'} for p in promises)}

def run_results_analysis(db:Session,announcement_id:str)->dict:
    import json
    a=db.get(Announcement,announcement_id)
    if not a:raise ValueError('Announcement was not found')
    if a.category!='results':raise ValueError('Only a financial results filing can be analysed by this endpoint.')
    if not a.source_url:raise ValueError('The filing has no original PDF URL.')
    if a.analysis_json:return json.loads(a.analysis_json)
    if not ai.llm_ready():raise ValueError('Hosted-model API key is required for structured PDF extraction.')
    doc,_,=store_document(db,a.ticker,{'kind':'results','title':a.title,'source_url':a.source_url,'published_label':a.published_at.strftime('%d %b %Y')})
    chunks=db.execute(select(Chunk).where(Chunk.document_id==doc.id).order_by(Chunk.page)).scalars().all()
    pages_map={}
    for c in chunks:pages_map[c.page]=(pages_map.get(c.page,'')+' '+c.content).strip()
    keys=('statement of financial results','quarter ended','revenue from operations','profit before tax','profit after tax')
    pages=[{'page':p,'content':s} for p,s in pages_map.items() if any(k in s.lower() for k in keys)][:9]
    result=ai.extract_quarterly_results(a.ticker,pages)
    if result['rows']:
        result['source_url']=a.source_url
        a.analysis_json=json.dumps(result,ensure_ascii=False)
        db.commit()
    return result

def enrich_filings(db:Session,ticker:str,max_items:int=4)->dict:
    """Enrich a small number of high-priority filings only; avoid one costly AI call per routine filing."""
    if not ai.llm_ready():return {'enriched':0,'error':'No hosted AI key configured.'}
    records=db.execute(select(Announcement).where(Announcement.ticker==ticker,Announcement.priority.in_(['high','medium']),Announcement.body!='').order_by(Announcement.published_at.desc()).limit(40)).scalars().all()
    enriched=0
    for a in records:
        if enriched>=max_items:break
        if a.summary!=concise_summary(a.title,a.body):continue
        info=ai.explain_material_filing(a.title,a.body,a.category)
        if info:
            a.summary=info['summary'];a.reason=info['why_it_matters'];enriched+=1
    db.commit()
    return {'enriched':enriched,'considered':min(len(records),40),'max_items':max_items}
