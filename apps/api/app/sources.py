"""Source adapters: best-effort public data; no bypass of paywalls/CAPTCHAs."""
import os, hashlib, re, io, time
from datetime import date,datetime,timedelta,timezone
from urllib.parse import urljoin,urlparse
import httpx
from bs4 import BeautifulSoup
import fitz
from .logic import normalize_date

USER_AGENT = 'FINN-Research-Prototype/1.0 (+public market source attribution)'
BROWSER_AGENT = 'Mozilla/5.0 (compatible; FINN Prototype; public company filings)'
TIMEOUT = 18

def fetch_market_prices(ticker:str, lookback:str='3mo') -> list[dict]:
    """Yahoo Finance chart endpoint; no reliance on an unofficial yfinance install."""
    symbol=f'{ticker}.NS'
    r=httpx.get(f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}', params={'range':lookback,'interval':'1d'}, headers={'User-Agent':BROWSER_AGENT}, timeout=TIMEOUT, follow_redirects=True)
    r.raise_for_status()
    payload=r.json()['chart']['result'][0]
    q=payload['indicators']['quote'][0]
    ts=payload.get('timestamp',[])
    out=[]
    for i, stamp in enumerate(ts):
        close=q['close'][i]
        vol=q['volume'][i]
        if close is None or vol is None: continue
        day=datetime.fromtimestamp(stamp,timezone.utc).strftime('%Y-%m-%d')
        out.append({'day':day,'close':float(close),'volume':int(vol)})
    return out

def fetch_nse_announcements(ticker:str,days:int=14) -> list[dict]:
    """NSE public endpoint; respects access denials without evasion."""
    start=(date.today()-timedelta(days=days)).strftime('%d-%m-%Y')
    end=date.today().strftime('%d-%m-%Y')
    headers={'User-Agent':BROWSER_AGENT,'Referer':'https://www.nseindia.com/companies-listing/corporate-filings-announcements','Accept':'application/json,text/plain,*/*'}
    with httpx.Client(timeout=TIMEOUT,headers=headers,follow_redirects=True) as client:
        # A normal public landing page request is used to receive session cookies.
        landing=client.get('https://www.nseindia.com/companies-listing/corporate-filings-announcements')
        landing.raise_for_status()
        response=client.get('https://www.nseindia.com/api/corporate-announcements',params={'index':'equities','symbol':ticker,'from_date':start,'to_date':end})
        response.raise_for_status()
        entries=response.json()
    if isinstance(entries,dict): entries=entries.get('data',[])
    if not isinstance(entries,list): raise ValueError('Unexpected NSE response format')
    records=[]
    for a in entries:
        published=normalize_date(a.get('an_dt') or a.get('sort_date') or '')
        src=a.get('attchmntFile') or ''
        records.append({'ticker':a.get('symbol') or ticker,'title':a.get('desc') or 'Company announcement','body':a.get('attchmntText') or '', 'published_at':published,'source_url':src if str(src).startswith('https://') else None,'source':'NSE','source_id':str(a.get('seq_id') or '')})
    return records

def discover_company_documents(ticker:str) -> list[dict]:
    """Screener is only a link directory; research ingests the ORIGINAL linked documents."""
    if not re.fullmatch(r'[A-Z0-9&_-]{1,25}', ticker): raise ValueError('Invalid NSE ticker')
    url=f'https://www.screener.in/company/{ticker}/consolidated/'
    r=httpx.get(url,headers={'User-Agent':BROWSER_AGENT},timeout=TIMEOUT,follow_redirects=True)
    if r.status_code==404:
        url=f'https://www.screener.in/company/{ticker}/'; r=httpx.get(url,headers={'User-Agent':BROWSER_AGENT},timeout=TIMEOUT,follow_redirects=True)
    r.raise_for_status()
    soup=BeautifulSoup(r.text,'html.parser')
    area=soup.select_one('#documents') or soup
    docs=[]; seen=set()
    # Link groups on Screener currently include annual reports, concalls and presentations.
    for a in area.select('a[href]'):
        href=urljoin(url,a.get('href',''))
        if href in seen or not href.startswith('https://'): continue
        visible=' '.join(a.stripped_strings)
        li=a.find_parent('li')
        context=' '.join((li.get_text(' ',strip=True) if li is not None else visible).split())[:200]
        heading=a.find_previous(['h3','h4','h2'])
        heading_text=heading.get_text(' ',strip=True) if heading and heading.find_parent(id='documents') is not None else ''
        label=(visible+' '+context+' '+heading_text).lower()
        lower=href.lower()
        if 'transcript' in label or 'concall' in label or 'earnings call' in label:
            kind='transcript'
        elif 'annual report' in label or 'annual report' in lower:
            kind='annual_report'
        elif 'presentation' in label and ('investor' in label or 'results' in label):
            kind='presentation'
        else:
            continue
        # Never ingest Screener's own generated summaries; follow primary PDF links.
        host=urlparse(href).hostname or ''
        if host.endswith('screener.in') or host.endswith('youtube.com') or host.endswith('youtu.be') or host.endswith('google.com'):
            continue
        seen.add(href)
        docs.append({'title': visible or context or kind.replace('_',' ').title(),'source_url':href,'kind':kind,'published_label':context[:80]})
    # latest usually listed first, and cap to avoid oversized workloads.
    return docs[:65]

def fetch_pdf_pages(url:str,max_pages:int=180)->list[tuple[int,str]]:
    parsed=urlparse(url)
    if parsed.scheme!='https' or not parsed.hostname or any(x in parsed.hostname for x in ['localhost','127.','169.254.']):
        raise ValueError('Unsafe/non-HTTPS document URL')
    r=httpx.get(url,headers={'User-Agent':BROWSER_AGENT},timeout=35,follow_redirects=True)
    r.raise_for_status()
    max_bytes=int(os.getenv('MAX_PDF_BYTES','14000000'))
    if len(r.content)>max_bytes: raise ValueError('Document exceeds configured PDF limit')
    if not (r.content.startswith(b'%PDF') or 'pdf' in r.headers.get('content-type','').lower()):
        raise ValueError('Source did not return a PDF. Use the original downloadable filing link.')
    pages=[]
    with fitz.open(stream=r.content,filetype='pdf') as pdf:
        for i,page in enumerate(pdf):
            if i>=max_pages:break
            text=' '.join(page.get_text(sort=True).split())
            if text:pages.append((i+1,text[:14000]))
    if not pages: raise ValueError('PDF has no extractable text (possibly scanned)')
    return pages
