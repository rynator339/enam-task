"""Hosted LLM adapter. No custom model training, no unsupported outside-company knowledge."""
import os, json, re
from typing import Any
from .logic import verify_quote

SYSTEM = '''You are FINN, a cautious analyst of Indian listed companies.
Use ONLY the supplied passages from ORIGINAL annual reports, exchange filings, and company earnings-call transcripts.
Never add outside facts, inferred figures, stock-price forecasts, or buy/sell recommendations.
Every factual assertion must point to a supplied passage identifier [D# p.#].
If evidence is insufficient, explicitly say what is missing. Separate management forecasts from reported outcomes.
No broker research, news, or third-party screener-generated commentary is allowed.'''

def llm_ready()->bool:
    return bool(os.getenv('LLM_API_KEY') or os.getenv('GEMINI_API_KEY'))

def _client():
    from openai import OpenAI
    key=os.getenv('LLM_API_KEY') or os.getenv('GEMINI_API_KEY')
    if not key: raise RuntimeError('No hosted-model API key configured')
    return OpenAI(api_key=key,base_url=os.getenv('LLM_BASE_URL','https://generativelanguage.googleapis.com/v1beta/openai/'),timeout=40.0,max_retries=1)

def completion(system:str,user:str,temperature:float=0.1,max_tokens:int=1300)->str:
    response=_client().chat.completions.create(model=os.getenv('LLM_MODEL','gemini-2.5-flash'),messages=[{'role':'system','content':system},{'role':'user','content':user}],temperature=temperature,max_tokens=max_tokens)
    return response.choices[0].message.content or ''

def json_completion(instruction:str,passages:str)->Any:
    raw=completion(SYSTEM+'\nReturn strict JSON only. '+instruction,passages,temperature=0,max_tokens=1900)
    raw=re.sub(r'^\s*```(?:json)?\s*|\s*```\s*$', '',raw.strip())
    return json.loads(raw)

def answer_question(question:str,passages:list[dict])->str:
    if not passages: return 'No indexed primary-source passages are available for this company yet.'
    material='\n\n'.join(f"[D{i+1} p.{p['page']}] {p['title']}\n{p['content'][:1800]}" for i,p in enumerate(passages[:9]))
    return completion(SYSTEM, f'Question: {question}\n\nEvidence:\n{material}\n\nProvide a concise, source-cited answer. Do not cite anything not supplied.',max_tokens=1050)

def extract_guidance(ticker:str,pages:list[dict])->list[dict]:
    """Reject any quote that cannot be found on its asserted original PDF page."""
    if not pages: return []
    prompt=f'''Extract only EXPLICIT NUMERIC management forward guidance for {ticker}.
Return an array (max 6) of objects with EXACT keys metric, period, low, high, unit, basis, quote, page.
metric must be one of revenue_growth, revenue, ebitda_margin, ebitda, pbt, pat, capex, capacity_growth, other.
Numeric target expressed as "at least X" => low=X, high=null. "up to Y"=>low=null,high=Y.
Include exact original quote of >= 30 characters copied verbatim from provided page; do NOT paraphrase quote.
period should be a standard FY or quarter e.g. FY2027 or Q2 FY2027; if not explicit, skip.
For non-specific qualitative or conditional guidance without a firm numeric range, skip.
Use units such as %, INR crore, INR billion, and do not perform unrequested conversions.
Return [] if no confident entries.'''
    data='\n'.join(f"[p.{p['page']}] {p['content'][:6500]}" for p in pages[:10])
    try: result=json_completion(prompt,data)
    except Exception: return []
    valid=[]
    if not isinstance(result,list): return []
    for item in result:
        try:
            page=int(item['page']); source=next(p['content'] for p in pages if p['page']==page)
            if not verify_quote(str(item['quote']),source):continue
            lo=float(item['low']) if item.get('low') is not None else None
            hi=float(item['high']) if item.get('high') is not None else None
            if lo is None and hi is None: continue
            if lo is not None and hi is not None and lo>hi:continue
            if not re.search(r'FY\s*\d{2,4}|Q[1-4]',str(item.get('period','')),re.I):continue
            valid.append({'metric':str(item['metric']).lower().strip(),'period':str(item['period']).replace(' ','').upper(),'target_low':lo,'target_high':hi,'unit':str(item['unit']).strip(),'basis':str(item.get('basis','unspecified')).strip(),'quote':str(item['quote']),'page':page})
        except (KeyError,TypeError,ValueError,StopIteration): continue
    return valid

def extract_actuals(ticker:str,pages:list[dict])->list[dict]:
    if not pages:return []
    prompt=f'''Extract up to 12 ACTUAL REPORTED financial figures for {ticker}, not promises/guidance.
Return an array of JSON objects with keys metric, period, value, unit, basis, quote, page.
Only extract revenue_growth, revenue, ebitda_margin, ebitda, pbt, pat, capex, capacity_growth where clearly present.
quote MUST be an exact contiguous quotation >=30 characters from the supplied page that contains the figure.
Specify period like FY2026 or Q2FY2027, ensure it matches the passage. No inferred figures or calculations.
Use units as printed (%, INR crore, etc). Choose consolidated/standalone only when clear.
Return [] if no verifiable values.'''
    data='\n'.join(f"[p.{p['page']}] {p['content'][:6500]}" for p in pages[:10])
    try: result=json_completion(prompt,data)
    except Exception:return []
    if not isinstance(result,list):return []
    valid=[]
    for item in result:
        try:
            page=int(item['page']); source=next(p['content'] for p in pages if p['page']==page)
            if not verify_quote(str(item['quote']),source):continue
            valid.append({'metric':str(item['metric']).lower().strip(),'period':str(item['period']).replace(' ','').upper(),'value':float(item['value']),'unit':str(item['unit']).strip(),'basis':str(item.get('basis','unspecified')).strip(),'quote':str(item['quote']),'page':page})
        except (KeyError,TypeError,ValueError,StopIteration):continue
    return valid


def extract_quarterly_results(ticker:str,pages:list[dict])->dict:
    """Structured numbers with quote validation; never invent missing PBT/EBITDA."""
    default={'rows':[],'note':'No verifiable quarterly metrics were extracted. Review the original filing.','basis':'unspecified'}
    if not pages:return default
    instructions=f"""Extract actual QUARTERLY results from the original {ticker} corporate filing.
Return JSON object with basis (consolidated/standalone/unspecified), period, and rows.
Each row must contain metric (revenue, ebitda, pbt, pat), current, previous, year_ago, unit, quote, page.
Numbers can be null if not printed explicitly. Do not infer EBITDA from operating profit, or infer any missing value.
All values in each row must be on the SAME metric and consolidated/standalone basis.
quote must be >=30 contiguous characters EXACTLY copied from the supplied original PDF page and contain the relevant reported figures.
The period should be clearly specified in the filing, e.g. Q2FY2027. If quarter mapping is not clear, skip.
Return only rows where current is verifiable and quote is exact. Use INR crore or other units AS PRINTED.
"""
    text='\n'.join(f"[p.{p['page']}] {p['content'][:8500]}" for p in pages[:8])
    try:data=json_completion(instructions,text)
    except Exception:return default
    if not isinstance(data,dict):return default
    cleaned=[]
    for row in data.get('rows',[]):
        try:
            page=int(row['page']); source=next(p['content'] for p in pages if p['page']==page)
            if not verify_quote(str(row['quote']),source):continue
            metric=str(row['metric']).strip().lower()
            if metric not in {'revenue','ebitda','pbt','pat'}:continue
            vals={}
            for k in ('current','previous','year_ago'):
                vals[k]=float(row[k]) if row.get(k) is not None else None
            if vals['current'] is None:continue
            def change(a,b):return round((a/b-1)*100,2) if a is not None and b not in (None,0) else None
            cleaned.append({'metric':metric,**vals,'qoq_pct':change(vals['current'],vals['previous']),'yoy_pct':change(vals['current'],vals['year_ago']),'unit':str(row.get('unit','')).strip(),'page':page,'quote':str(row['quote'])})
        except (KeyError,TypeError,ValueError,StopIteration):continue
    return {'basis':str(data.get('basis','unspecified')),'period':str(data.get('period','')),'rows':cleaned,'note':None if cleaned else default['note']}

def explain_material_filing(title:str,body:str,category:str)->dict|None:
    """Optional inexpensive enrichment, never add facts beyond the filing excerpt."""
    if not llm_ready() or not body.strip():return None
    instruction='''Use ONLY the company exchange-announcement text provided.
Return a JSON object with keys summary and why_it_matters.
summary: one clear sentence <=35 words, describing only actual disclosed information.
why_it_matters: one sentence <=25 words explaining the potential investor relevance, without making price predictions.
If the disclosure lacks concrete detail, state that the attachment should be read for specifics.
Do not infer transaction amounts, financial impact, people or dates not in the provided text.'''
    try:
        data=json_completion(instruction,f'Category: {category}\nTitle: {title}\nOriginal exchange text: {body[:3500]}')
        if not isinstance(data,dict):return None
        summary=str(data.get('summary','')).strip()
        why=str(data.get('why_it_matters','')).strip()
        if not summary or not why or len(summary)>420 or len(why)>360:return None
        return {'summary':summary,'why_it_matters':why}
    except Exception:return None
