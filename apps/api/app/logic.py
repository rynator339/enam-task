"""Human-auditable financial calculations, announcement routing and evidence matching."""
import hashlib, re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Any

CATEGORIES = ['results','M&A','fund_raise','management_change','litigation','insider_trading','earnings_call','investor_meetings','credit_rating','dividend','bonus_split','capex','press_release','postal_ballot','agm_egm','pledging','unclassified']
RULES = [
 ('results',r'financial results|quarterly results|annual results|audited results|unaudited results|outcome.*financial'),
 ('M&A',r'acquisit|merger|demerger|joint venture|stake sale|scheme of arrangement'),
 ('management_change',r'resignation|appointment of (?:a )?(?:cfo|ceo|director|md)|change in management|key managerial|chief financial officer|chief executive officer'),
 ('litigation',r'insolvency|litigation|court order|regulatory order|penalty|show cause|fine imposed|sebi order'),
 ('credit_rating',r'credit rating|rating (?:upgrade|downgrade|reaffirm)|icra|crisil|care ratings'),
 ('fund_raise',r'qip|qualified institutional|rights issue|preferential allotment|commercial paper|buyback|issue of bonds|non.convertible debenture'),
 ('pledging',r'encumbrance|pledge|release of pledge|promoter.*pledge'),
 ('insider_trading',r'insider trad|sast|disclosure.*trading|promoter.*acquir|promoter.*dispos'),
 ('earnings_call',r'earnings call|concall|conference call|analyst call|transcript'),
 ('investor_meetings',r'investor meeting|investor conference|institutional investor|analyst meet'),
 ('dividend',r'dividend|record date.*dividend'),
 ('bonus_split',r'bonus issue|stock split|sub.division of shares|split of shares'),
 ('capex',r'capacity expansion|new manufacturing|capital expenditure|setting up.*plant|commissioning.*facility'),
 ('postal_ballot',r'postal ballot|e.voting result'),
 ('agm_egm',r'annual general meeting|extraordinary general meeting|\bagm\b|\begm\b'),
 ('press_release',r'press release|order win|new product|strategic partnership|order received|contract award'),
]
ROUTINE_PATTERN = re.compile(r'trading window closure|closure of trading window|certificate under|reconciliation of share capital|newspaper publication|compliance certificate|scrutinizer report|esop allotment|secretarial compliance|regulation 74|regulation 76|loss of share certificate', re.I)
MATERIAL_PATTERN = re.compile(r'fraud|default|downgrade|resign|penalty|insolvency|material|acquisition|merger|demerger|qip|financial results|quarterly results|scheme of arrangement', re.I)

def classify(title: str, body: str = '') -> tuple[str,str,str]:
    raw = f'{title} {body[:1600]}'
    if ROUTINE_PATTERN.search(title):
        return 'unclassified','low','Routine compliance or administrative disclosure.'
    category = next((cat for cat,pattern in RULES if re.search(pattern,raw,re.I)), 'unclassified')
    if category in {'results','M&A','management_change','litigation'}:
        priority = 'high'; reason=f'{category.replace("_", " ").upper()} disclosure warrants review.'
    elif category in {'credit_rating','fund_raise','pledging','capex','press_release','insider_trading'}:
        priority = 'medium'; reason=f'{category.replace("_", " ").capitalize()} could affect company fundamentals; inspect the filing.'
    else:
        priority = 'low'; reason='Informational or procedural filing; kept accessible in the digest.'
    if MATERIAL_PATTERN.search(raw) and priority == 'low' and category != 'unclassified':
        priority='medium'; reason='Potentially material wording detected; verify against the original filing.'
    return category,priority,reason

def concise_summary(title:str, body:str='') -> str:
    txt = ' '.join((body or '').split())
    if not txt:
        return title.rstrip('.') + '.'
    if len(txt)>235:
        txt = txt[:235].rsplit(' ',1)[0].rstrip(' ,.;') + '…'
    return txt

def price_stats(closes: list[float], volumes: list[int]) -> tuple[float | None,float | None]:
    if len(closes)<2 or not closes[-2]:
        change = None
    else:
        change = round((closes[-1]/closes[-2]-1)*100,2)
    prev = [v for v in volumes[max(0,len(volumes)-21):-1] if v is not None and v>0]
    multiple = round(volumes[-1]/(sum(prev)/len(prev)),2) if len(prev)>=20 and volumes[-1] >= 0 else None
    return change,multiple

def compare_guidance(low: float | None, high: float | None, actual: float | None, unit_target: str, unit_actual: str, period_target:str, period_actual:str, basis_target:str='unspecified', basis_actual:str='unspecified') -> tuple[str,str]:
    if actual is None:
        return 'pending','No reported actual value available for this period.'
    if period_target.strip().lower() != period_actual.strip().lower():
        return 'unverifiable','Target and actual refer to different reporting periods.'
    if unit_target.strip().lower() != unit_actual.strip().lower():
        return 'unverifiable','Target and actual use different units; conversion is not assumed.'
    if basis_target != basis_actual and 'unspecified' not in {basis_target,basis_actual}:
        return 'unverifiable','Target and actual have incompatible reporting bases.'
    if low is None and high is None:
        return 'unverifiable','No explicit numerical target to compare.'
    # A lower-bound target is met when >= lower bound. An upper-bound target is met when <= upper bound.
    if low is not None and actual < low:
        return 'missed',f'Reported {actual:g} {unit_actual} is below the lower bound of {low:g}.'
    if high is not None and actual > high:
        return 'missed',f'Reported {actual:g} {unit_actual} exceeds the upper bound of {high:g}.'
    return 'met',f'Reported {actual:g} {unit_actual} falls within the stated numerical target.'

def normalize_date(value: str) -> datetime:
    for fmt in ('%d-%b-%Y %H:%M:%S','%d-%b-%Y %H:%M','%Y-%m-%d %H:%M:%S','%Y-%m-%dT%H:%M:%S','%d-%m-%Y %H:%M:%S','%d-%b-%Y','%Y-%m-%d'):
        try: return datetime.strptime(value,fmt).replace(tzinfo=ZoneInfo("Asia/Kolkata")).astimezone(timezone.utc)
        except ValueError: pass
    return datetime.now(timezone.utc)

def stable_id(*parts:Any) -> str:
    return hashlib.sha256('|'.join(str(p) for p in parts).encode()).hexdigest()[:40]

def verify_quote(quote:str, source_text:str) -> bool:
    def norm(s): return re.sub(r'\W+', '',s.lower(),flags=re.UNICODE)
    q=norm(quote); text=norm(source_text)
    return len(q)>=30 and q in text

def keyword_score(question:str,chunk:str) -> float:
    terms=set(re.findall(r'[a-z]{3,}',question.lower())) - {'what','this','that','with','from','about','the','and','company','does','have','been','when','show'}
    c=chunk.lower()
    return sum(min(c.count(t), 4) for t in terms)
