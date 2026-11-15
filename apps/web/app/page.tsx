'use client';
import { useEffect, useMemo, useState, useCallback, FormEvent } from 'react';
import {
 ArrowDownRight, ArrowLeft, ArrowRight, ArrowUpRight, Bell, BookOpenCheck, CalendarDays,
 CheckCircle2, ChevronDown, ChevronRight, CircleAlert, Clock3, ExternalLink, FileSearch,
 FileText, Filter, Gauge, HelpCircle, Home, Info, Layers3, LoaderCircle, Menu,
 Newspaper, Plus, Radar, RefreshCw, Search, Settings2, ShieldCheck, Sparkles, Target,
 TrendingUp, WalletCards, X, XCircle, SlidersHorizontal, Building2, Eye, Zap, Link2,
} from 'lucide-react';
import Brand from '@/components/Brand';
import TrendChart from '@/components/TrendChart';
import { api, API_BASE, Company, FeedItem, FeedResponse, Health, PromiseClaim, Price, Answer, ResultAnalysis, CATEGORY_NAMES, formatTime, formatMoney, cleanError } from '@/lib/api';

type Tab = 'today' | 'research' | 'watchlist' | 'settings';
type Scope = 'focused' | 'all';
const NAV: {id:Tab;label:string;icon:typeof Home}[]=[
 {id:'today',label:'Today',icon:Home},{id:'research',label:'Research',icon:FileSearch},
 {id:'watchlist',label:'Watchlist',icon:Layers3},{id:'settings',label:'Settings',icon:Settings2},
];
const WINDOWS=[{label:'24 hours',hours:24},{label:'7 days',hours:168},{label:'30 days',hours:720}];
const DEMO_ITEMS:FeedItem[]=[
 {id:'demo-1',ticker:'INFY',company:'Infosys',title:'Quarterly results worth comparing with earlier guidance',summary:'Illustration: compare management expectations with reported sales and margin outcomes.',reason:'Illustrative high-priority results example, not a real filing.',category:'results',priority:'high',published_at:new Date().toISOString(),source_url:null,is_illustrative:true,type:'filing'},
 {id:'demo-2',ticker:'LT',company:'Larsen & Toubro',title:'Materiality review for a potential order disclosure',summary:'Illustration: consider order size, impacted segments and revenue visibility.',reason:'Illustrative corporate disclosure, not a real filing.',category:'press_release',priority:'medium',published_at:new Date().toISOString(),source_url:null,is_illustrative:true,type:'filing'},
 {id:'demo-3',ticker:'HDFCBANK',company:'HDFC Bank',title:'Management transition deserves attention',summary:'Illustration: evaluate the experience and responsibilities of a hypothetical new executive.',reason:'Illustrative executive change; not an actual event.',category:'management_change',priority:'high',published_at:new Date().toISOString(),source_url:null,is_illustrative:true,type:'filing'},
];
const FALLBACK_COMPANIES:Company[]=[
 ['RELIANCE','Reliance Industries','Energy & Retail'],['TCS','Tata Consultancy Services','Information Technology'],['INFY','Infosys','Information Technology'],['HDFCBANK','HDFC Bank','Banking'],['ICICIBANK','ICICI Bank','Banking'],['ITC','ITC','Consumer'],['HINDUNILVR','Hindustan Unilever','Consumer'],['NTPC','NTPC','Power'],['POWERGRID','Power Grid Corporation','Power'],['MARUTI','Maruti Suzuki','Automotive'],['SUNPHARMA','Sun Pharmaceutical','Pharmaceuticals'],['DRREDDY',"Dr. Reddy's Laboratories",'Pharmaceuticals'],['LT','Larsen & Toubro','Industrials'],['ULTRACEMCO','UltraTech Cement','Materials'],['BHARTIARTL','Bharti Airtel','Telecom'],['DIXON','Dixon Technologies','Electronics'],['POLYCAB','Polycab India','Electrical Equipment'],['CDSL','Central Depository Services','Financial Infrastructure'],
].map(([ticker,name,sector])=>({ticker,name,sector,in_watchlist:true,close:null,day_change_pct:null,volume_multiple:null,price_day:null}));
function IconForCategory({category,size=18}:{category:string;size?:number}){
 const I=category==='market_move'?TrendingUp:category==='results'?WalletCards:category==='management_change'?Building2:category==='M&A'?Layers3:category==='credit_rating'?Gauge:category==='unclassified'?FileText:Newspaper;
 return <I size={size} strokeWidth={1.8}/>;
}
function Pill({children,tone='neutral'}:{children:React.ReactNode;tone?:'neutral'|'green'|'red'|'amber'|'teal'}){return <span className={`pill pill-${tone}`}>{children}</span>;}
function LoadingText({text}:{text:string}){return <div className="loading-inline"><LoaderCircle className="spin" size={16}/>{text}</div>;}
function SourceLink({url,label='Original source'}:{url:string|null|undefined;label?:string}){
 return url?<a className="source-link" href={url} target="_blank" rel="noopener noreferrer"><ExternalLink size={14}/>{label}</a>:<span className="missing-source"><CircleAlert size={14}/> No verified source attached</span>;
}
function SignalCard({item,onClick}:{item:FeedItem;onClick:()=>void}){
 return <button type="button" className={`signal-card signal-${item.priority}`} onClick={onClick}>
   <div className="signal-top"><div className={`signal-symbol icon-${item.priority}`}><IconForCategory category={item.category}/></div><div className="signal-meta"><strong>{item.company}</strong><span>{item.ticker} · {formatTime(item.published_at)}</span></div><Pill tone={item.priority==='high'?'red':item.priority==='medium'?'amber':'neutral'}>{item.priority==='high'?'Important':item.priority==='medium'?'Worth a look':'Routine'}</Pill></div>
   <h3>{item.title}</h3><p>{item.summary}</p>
   <div className="signal-foot"><span className="category-label">{CATEGORY_NAMES[item.category]??item.category}{item.is_illustrative?' · Illustration':''}</span><span className="read-link">Explore signal <ArrowRight size={15}/></span></div>
 </button>;
}
function EmptyState({icon:Icon,title,description,children}:{icon:typeof InboxIcon;title:string;description:string;children?:React.ReactNode}){return <div className="empty-state"><div className="empty-icon"><Icon size={28} strokeWidth={1.5}/></div><h3>{title}</h3><p>{description}</p>{children}</div>;}
const InboxIcon=Bell;

export default function Finn(){
 const [tab,setTab]=useState<Tab>('today');
 const [showMenu,setShowMenu]=useState(false);
 const [feed,setFeed]=useState<FeedItem[]>([]);
 const [feedLoading,setFeedLoading]=useState(true);
 const [feedError,setFeedError]=useState<string|null>(null);
 const [companies,setCompanies]=useState<Company[]>(FALLBACK_COMPANIES);
 const [health,setHealth]=useState<Health|null>(null);
 const [demo,setDemo]=useState(false);
 const [windowHours,setWindowHours]=useState(24);
 const [customDays,setCustomDays]=useState(14);
 const [scope,setScope]=useState<Scope>('focused');
 const [category,setCategory]=useState('all');
 const [thresholdPrice,setThresholdPrice]=useState(3);
 const [thresholdVolume,setThresholdVolume]=useState(2);
 const [selected,setSelected]=useState<FeedItem|null>(null);
 const [analysingResults,setAnalysingResults]=useState(false);
 const [resultsError,setResultsError]=useState<string|null>(null);
 const [ticker,setTicker]=useState('INFY');
 const [tickerInput,setTickerInput]=useState('INFY');
 const [company,setCompany]=useState<Company|null>(null);
 const [prices,setPrices]=useState<Price[]>([]);
 const [promises,setPromises]=useState<PromiseClaim[]>([]);
 const [researchLoading,setResearchLoading]=useState(false);
 const [researchError,setResearchError]=useState<string|null>(null);
 const [discovering,setDiscovering]=useState(false);
 const [analyzing,setAnalyzing]=useState(false);
 const [qaLoading,setQaLoading]=useState(false);
 const [question,setQuestion]=useState('What does management say about growth and the key risks?');
 const [answer,setAnswer]=useState<Answer|null>(null);
 const [researchToast,setResearchToast]=useState<string|null>(null);
 const [searchWatchlist,setSearchWatchlist]=useState('');
 const [ready,setReady]=useState(false);

 useEffect(()=>{
   try {const preferences=JSON.parse(localStorage.getItem('finn-preferences')||'{}');if(typeof preferences.price==='number')setThresholdPrice(preferences.price);if(typeof preferences.volume==='number')setThresholdVolume(preferences.volume);}catch{/* ignore */}
   setReady(true);
   api<Health>('/api/health').then(setHealth).catch(()=>setHealth(null));
   api<{companies:Company[]}>('/api/companies').then(d=>setCompanies(d.companies)).catch(()=>{});
 },[]);
 useEffect(()=>{if(ready)localStorage.setItem('finn-preferences',JSON.stringify({price:thresholdPrice,volume:thresholdVolume}));},[thresholdPrice,thresholdVolume,ready]);
 const loadFeed=useCallback(async()=>{
   setFeedLoading(true);setFeedError(null);
   try{
     if(demo){
       try{const d=await api<FeedResponse>('/api/feed?demo=true');setFeed(d.items);}catch{setFeed(DEMO_ITEMS);}
     } else {
       const params=new URLSearchParams({window_hours:String(windowHours),price_threshold:String(thresholdPrice),volume_threshold:String(thresholdVolume)});
       const data=await api<FeedResponse>(`/api/feed?${params}`);setFeed(data.items);
     }
   }catch(e){setFeed([]);setFeedError(cleanError(e));}
   finally{setFeedLoading(false);}
 },[demo,windowHours,thresholdPrice,thresholdVolume]);
 useEffect(()=>{void loadFeed();},[loadFeed]);
 const visibleFeed=useMemo(()=>feed.filter(x=>(scope==='all'||x.priority!=='low')&&(category==='all'||x.category===category)),[feed,scope,category]);
 const lowCount=feed.filter(x=>x.priority==='low').length;
 const highCount=feed.filter(x=>x.priority==='high').length;
 const marketCount=feed.filter(x=>x.category==='market_move').length;
 const activeCompany=companies.find(c=>c.ticker===ticker);

 const loadCompany=useCallback(async(symbol:string)=>{
   setResearchLoading(true);setResearchError(null);setAnswer(null);setTicker(symbol);
   try{
     const [c,p,pr]=await Promise.all([
       api<Company>(`/api/companies/${encodeURIComponent(symbol)}`),
       api<{prices:Price[]}>(`/api/companies/${encodeURIComponent(symbol)}/prices`),
       api<{promises:PromiseClaim[]}>(`/api/companies/${encodeURIComponent(symbol)}/promises`),
     ]);
     setCompany(c);setPrices(p.prices);setPromises(pr.promises);
   }catch(e){setCompany(null);setPrices([]);setPromises([]);setResearchError(cleanError(e));}
   finally{setResearchLoading(false);}
 },[]);
 useEffect(()=>{if(tab==='research'&&!company&&!researchLoading&&!researchError)void loadCompany(ticker);},[tab,company,researchLoading,researchError,loadCompany,ticker]);
 async function openSignal(item:FeedItem){
    setSelected(item);setResultsError(null);
    if(item.is_illustrative||item.type==='price')return;
    try {const details=await api<FeedItem>(`/api/signals/${item.id}`);
      setSelected(current=>current?.id===item.id?{...current,...details}:current);
    } catch {/* show cached feed detail */}
 }
 async function analyzeResults(item:FeedItem){
    setAnalysingResults(true);setResultsError(null);
    try{const result=await api<ResultAnalysis>(`/api/signals/${item.id}/analyze-results`,{method:'POST'});
      setSelected(current=>current?.id===item.id?{...current,results_analysis:result}:current);
    }catch(e){setResultsError(cleanError(e));}
    finally{setAnalysingResults(false);}
 }
 function goResearch(symbol:string){setSelected(null);setTickerInput(symbol);setTab('research');void loadCompany(symbol);}
 function submitCompany(e:FormEvent){e.preventDefault();const clean=tickerInput.trim().toUpperCase().replace(/\.NS$/,'');if(clean)void loadCompany(clean);}
 async function discoverDocs(){setDiscovering(true);setResearchToast(null);try{
   const result=await api<{discovered_count:number;documents:{status:string;title:string;error?:string}[]}>(`/api/companies/${ticker}/discover`,{method:'POST'});
   const indexed=result.documents.filter(d=>d.status==='indexed').length;
   setResearchToast(indexed?`Indexed ${indexed} original document(s). You can now ask sourced research questions.`:`No documents indexed. ${result.documents.find(d=>d.error)?.error||'Inspect source accessibility.'}`);
   await loadCompany(ticker);
 }catch(e){setResearchToast(`Document source unavailable: ${cleanError(e)}`);}finally{setDiscovering(false);}}
 async function analyzePromises(){setAnalyzing(true);setResearchToast(null);try{
   const result=await api<{extracted:number;actuals:number;error?:string}>(`/api/companies/${ticker}/analyze-promises`,{method:'POST'});
   setResearchToast(result.error||`Extracted ${result.extracted} verified guidance claim(s) and ${result.actuals} actual metric(s).`);
   await loadCompany(ticker);
 }catch(e){setResearchToast(cleanError(e));}finally{setAnalyzing(false);}}
 async function askQuestion(e?:FormEvent){e?.preventDefault();if(!question.trim())return;setQaLoading(true);setAnswer(null);try{setAnswer(await api<Answer>('/api/research',{method:'POST',body:JSON.stringify({ticker,question})}));}catch(e){setResearchToast(cleanError(e));}finally{setQaLoading(false);}}
 function navTo(id:Tab){setTab(id);setSelected(null);setShowMenu(false);window.scrollTo({top:0,behavior:'smooth'});}
 const currentDate=new Date().toLocaleDateString('en-IN',{weekday:'long',month:'long',day:'numeric'});

 return <div className="app-shell">
   <aside className={`sidebar ${showMenu?'sidebar-open':''}`}>
     <div className="side-header"><Brand/><button className="mobile-close" onClick={()=>setShowMenu(false)} aria-label="Close menu"><X size={20}/></button></div>
     <div className="side-tagline">Clarity for every decision.</div>
     <div className="side-divider"/>
     <div className="nav-section-label">WORKSPACE</div>
     <nav className="side-nav" aria-label="Main navigation">{NAV.map(item=><button key={item.id} className={'nav-item '+(tab===item.id?'nav-active':'')} onClick={()=>navTo(item.id)}><item.icon size={19} strokeWidth={1.8}/><span>{item.label}</span>{tab===item.id&&<span className="nav-dot"/>}</button>)}</nav>
     <div className="side-bottom"><div className="side-help"><div className="side-help-icon"><Sparkles size={18}/></div><strong>Your second set of eyes.</strong><p>From company disclosures to evidence-backed understanding.</p><button onClick={()=>navTo('research')}>Explore research <ArrowRight size={14}/></button></div><div className="side-footer"><ShieldCheck size={15}/> Primary-source first <span className="version">v0.1</span></div></div>
   </aside>
   {showMenu&&<button className="mobile-scrim" aria-label="Close sidebar" onClick={()=>setShowMenu(false)}/>}
   <div className="main-column">
     <header className="topbar"><div className="topbar-start"><button className="hamburger" onClick={()=>setShowMenu(true)} aria-label="Open menu"><Menu size={21}/></button><div className="crumb">Workspace <ChevronRight size={14}/> <span>{NAV.find(n=>n.id===tab)?.label}</span></div></div><div className="topbar-end"><span className={'connection '+(health?'connection-online':'connection-offline')}><span className="connection-dot"/>{health?'API connected':'API unavailable'}</span><button className="top-icon" onClick={()=>navTo('settings')} aria-label="Preferences"><SlidersHorizontal size={19}/></button><span className="avatar">F</span></div></header>
     <main className="content">
       {tab==='today'&&<>
         <div className="intro-row"><div><div className="eyebrow"><span className="eyebrow-line"/> {currentDate}</div><h1>Good to have you here<span className="teal-dot">.</span></h1><p className="page-subtitle">Less market noise. More of what actually matters.</p></div><button className="outline-action refresh-desktop" onClick={()=>void loadFeed()} disabled={feedLoading}><RefreshCw size={16} className={feedLoading?'spin':''}/> Refresh feed</button></div>
         {(demo||!health)&&<div className={`notice ${demo?'notice-demo':'notice-error'}`}><Info size={19}/><div><strong>{demo?'Illustrative preview — not current market events':'Live backend not connected'}</strong><p>{demo?'These are fictional examples of the interface. Switch to live mode for actual sourced filings and prices.':'Start FastAPI locally or configure NEXT_PUBLIC_API_BASE_URL. Explore an explicitly illustrative preview in the meantime.'}</p></div><button onClick={()=>setDemo(!demo)}>{demo?'Live mode':'See preview'} <ArrowRight size={14}/></button></div>}
         {!demo&&health&&health.announcement_count===0&&<div className="notice notice-info"><Info size={18}/><div><strong>No filings ingested yet</strong><p>Run the data refresh job to populate actual NSE filings and EOD prices. The system will never present samples as real events.</p></div><button onClick={()=>setDemo(true)}>Sample preview <ArrowRight size={14}/></button></div>}
         <div className="hero-summary"><div><div className="hero-kicker"><Radar size={16}/> YOUR INVESTMENT PULSE</div><h2>Know what changed.<br/><span>Understand why.</span></h2><p>Your 18-company universe, organised by relevance instead of volume.</p><button className="hero-cta" onClick={()=>navTo('research')}>Investigate a company <ArrowUpRight size={17}/></button></div><div className="hero-art"><div className="art-orbit art-orbit-1"/><div className="art-orbit art-orbit-2"/><div className="art-core"><Radar size={62} strokeWidth={1}/></div><div className="art-floating art-floating-one"><span className="tiny-dot"/> SIGNAL FOUND</div><div className="art-floating art-floating-two"><Target size={15}/> MATERIALITY FIRST</div></div></div>
         <div className="stats"><div className="stat"><span>Important signals</span><div className="stat-value">{highCount.toString().padStart(2,'0')} <span className="stat-bubble red-dot"/></div><small>{demo?'Illustrative examples':'Within selected time period'}</small></div><div className="stat"><span>Market alerts</span><div className="stat-value">{marketCount.toString().padStart(2,'0')} <span className="stat-bubble green-dot"/></div><small>EOD triggers</small></div><div className="stat"><span>Companies watched</span><div className="stat-value">{companies.length} <span className="stat-bubble teal-dot-bg"/></div><small>Diversified NSE portfolio</small></div></div>
         <div className="section-heading"><div><div className="section-eyebrow">YOUR INTELLIGENCE FEED</div><h2>Signal inbox <span className="count-tag">{visibleFeed.length}</span></h2><p>The developments worth your attention, first.</p></div><div className="section-actions"><button className="ghost-button" onClick={()=>void loadFeed()}><RefreshCw size={17} className={feedLoading?'spin':''}/><span>Refresh</span></button></div></div>
         <div className="filters"><div className="filter-group filter-group-left"><CalendarDays size={17}/><select aria-label="Select feed period" value={windowHours} onChange={e=>setWindowHours(Number(e.target.value))}>{WINDOWS.map(w=><option value={w.hours} key={w.hours}>{w.label}</option>)}{![24,168,720].includes(windowHours)&&<option value={windowHours}>{Math.round(windowHours/24)} days custom</option>}</select><ChevronDown size={14}/></div><div className="filter-separator"/><div className="filter-group"><Filter size={16}/><select aria-label="Select announcement category" value={category} onChange={e=>setCategory(e.target.value)}><option value="all">All categories</option>{['results','M&A','management_change','press_release','credit_rating','market_move','unclassified'].map(c=><option key={c} value={c}>{CATEGORY_NAMES[c]}</option>)}</select><ChevronDown size={14}/></div><div className="filter-spacer"/><div className="segment"><button className={scope==='focused'?'segment-active':''} onClick={()=>setScope('focused')}>Focused</button><button className={scope==='all'?'segment-active':''} onClick={()=>setScope('all')}>All</button></div></div>
         <div className="feed-area">{feedLoading?<div className="feed-loading"><LoaderCircle className="spin" size={24}/>Finding relevant events...</div>:feedError?<EmptyState icon={CircleAlert} title="Cannot load the live feed" description={feedError}><button className="primary-button" onClick={()=>setDemo(true)}>Open illustrative preview <ArrowRight size={16}/></button></EmptyState>:visibleFeed.length?<div className="signal-list">{visibleFeed.map(item=><SignalCard key={item.id} item={item} onClick={()=>void openSignal(item)}/>)}</div>:<EmptyState icon={Bell} title="You're all caught up" description={demo?'No sample signals match these filters. Try changing your selection.':'There are no ingested signals matching this period. You can switch windows, refresh the source data or explore an illustrative preview.'}><button className="primary-button" onClick={()=>demo?setCategory('all'):setDemo(true)}>{demo?'Clear filters':'View sample workflow'} <ArrowRight size={16}/></button></EmptyState>}{scope==='focused'&&lowCount>0&&<button className="routine-banner" onClick={()=>setScope('all')}><div><Eye size={17}/><span>{lowCount} routine {lowCount===1?'filing':'filings'} tucked away</span></div><span>Show everything <ArrowRight size={15}/></span></button>}</div>
       </>}
       {tab==='research'&&<>
         <div className="intro-row"><div><div className="eyebrow"><span className="eyebrow-line"/> COMPANY INTELLIGENCE</div><h1>Go beyond the headline<span className="teal-dot">.</span></h1><p className="page-subtitle">Understand the business. Verify the claims. Follow the evidence.</p></div></div>
         <form className="research-search" onSubmit={submitCompany}><Search size={22}/><input aria-label="NSE ticker" value={tickerInput} onChange={e=>setTickerInput(e.target.value.toUpperCase())} placeholder="Search any NSE symbol — INFY, TCS, RELIANCE..."/><button type="submit" disabled={researchLoading}>Research company <ArrowRight size={17}/></button></form>
         <div className="suggested-tickers"><span>Explore</span>{['INFY','TCS','RELIANCE','LT','TRENT'].map(t=><button key={t} onClick={()=>{setTickerInput(t);void loadCompany(t);}}>{t}</button>)}</div>
         {researchError&&<div className="notice notice-error"><CircleAlert size={20}/><div><strong>Research service unavailable</strong><p>{researchError}</p></div></div>}
         {researchLoading?<div className="feed-loading"><LoaderCircle size={24} className="spin"/>Opening company workspace...</div>:<>
           <div className="company-heading"><div className="company-logo">{ticker.slice(0,2)}</div><div><div className="company-title-row"><h2>{company?.name||activeCompany?.name||ticker}</h2><Pill tone="teal">NSE: {ticker}</Pill></div><span className="company-sector">{company?.sector||activeCompany?.sector||'Listed company'} · Primary-source analysis</span></div></div>
           <div className="research-grid"><section className="panel chart-panel"><div className="panel-head"><div><span className="panel-kicker">MARKET CONTEXT</span><h3>Price trajectory</h3></div><Pill>{prices.length?'Yahoo EOD':'Awaiting data'}</Pill></div><TrendChart points={prices}/></section><section className="panel docs-panel"><div className="panel-head"><div><span className="panel-kicker">EVIDENCE VAULT</span><h3>Original documents</h3></div><span className="docs-count">{company?.documents?.length||0} indexed</span></div><p className="panel-description">Annual reports and earnings-call transcripts. FINN will only research what these sources support.</p><div className="docs-list">{company?.documents?.slice(0,3).map(d=><a className="document-row" key={d.id} target="_blank" rel="noopener noreferrer" href={d.url}><FileText size={17}/><span>{d.title}</span><ExternalLink size={15}/></a>)}{!company?.documents?.length&&<div className="data-placeholder">No primary-source documents indexed yet.</div>}</div><button className="full-outline" onClick={()=>void discoverDocs()} disabled={discovering}><RefreshCw size={16} className={discovering?'spin':''}/>{discovering?'Discovering and indexing...':'Discover & index original sources'}</button></section></div>
           {researchToast&&<div className="inline-message"><Info size={18}/>{researchToast}<button aria-label="Dismiss message" onClick={()=>setResearchToast(null)}><X size={15}/></button></div>}
           <div className="section-heading analysis-heading"><div><div className="section-eyebrow">FINANCIAL DEPTH</div><h2>What the numbers say</h2><p>Only directly extracted financial figures are displayed.</p></div></div>
           <section className="panel metrics-panel">{company?.metrics?.length?<div className="metric-grid">{company.metrics.slice(0,6).map(m=><div className="metric-item" key={m.id}><span>{m.metric.replaceAll('_',' ')}</span><strong>{formatMoney(m.value)} <small>{m.unit}</small></strong><div>{m.period} · PDF p.{m.page}</div></div>)}</div>:<div className="content-empty"><Gauge size={22}/><span>Financial metrics will appear after original reports are indexed and processed. Missing figures are never guessed.</span></div>}</section>
           <div className="section-heading analysis-heading"><div><div className="section-eyebrow">SIGNATURE INTELLIGENCE</div><h2>Promise Tracker <span className="star-inline"><Sparkles size={18}/></span></h2><p>What management said. What the company delivered.</p></div><button className="outline-action" disabled={analyzing} onClick={()=>void analyzePromises()}><Target size={16}/>{analyzing?'Analysing documents...':'Analyse guidance'}</button></div>
           <section className="panel promise-panel">{promises.length?<div className="promise-list">{promises.map(p=><div className="promise-row" key={p.id}><div className="promise-meta"><span className="promise-metric">{p.metric.replaceAll('_',' ')}</span><Pill tone={p.status==='met'?'green':p.status==='missed'?'red':p.status==='pending'?'amber':'neutral'}>{p.status==='met'?<CheckCircle2 size={12}/>:p.status==='missed'?<XCircle size={12}/>:<Clock3 size={12}/>} {p.status}</Pill></div><div className="promise-values"><div><small>MANAGEMENT TARGET</small><strong>{p.target_low!==null&&p.target_high!==null?`${p.target_low}–${p.target_high}`:p.target_low!==null?`≥ ${p.target_low}`:p.target_high!==null?`≤ ${p.target_high}`:'N/A'} <span>{p.unit}</span></strong></div><div><small>REPORTED ACTUAL</small><strong>{p.actual!==null?`${formatMoney(p.actual)} ${p.unit}`:'Not verified'}</strong></div></div><p>{p.rationale}</p><blockquote>“{p.quote}”</blockquote><div className="promise-sources"><SourceLink url={p.source_url} label={`Guidance · p.${p.page}`}/>{p.actual_url&&<SourceLink url={p.actual_url} label={`Reported · p.${p.actual_page}`}/>}</div></div>)}</div>:<div className="promise-placeholder"><div className="promise-icon"><Target size={31}/></div><h3>Make management accountable to the numbers.</h3><p>Index earnings-call transcripts and financial reports, then extract verifiable guidance. Every comparison requires matching metrics, units and reporting periods.</p><div className="promise-steps"><span><CheckCircle2 size={14}/> Extract exact quotes</span><span><CheckCircle2 size={14}/> Match reported actuals</span><span><CheckCircle2 size={14}/> Show evidence-backed verdicts</span></div><button className="primary-button" onClick={()=>void analyzePromises()} disabled={analyzing}><Sparkles size={16}/> {analyzing?'Analysing...':'Analyse source documents'}</button></div>}</section>
           <div className="section-heading analysis-heading"><div><div className="section-eyebrow">ASK FINN</div><h2>Ask a better question</h2><p>Answers restricted to indexed annual reports and company earnings-call transcripts.</p></div></div>
           <section className="panel qa-panel"><div className="qa-suggestions">{['What are the main growth drivers?','What risks does management mention?','How has the margin trajectory changed?'].map(q=><button key={q} onClick={()=>setQuestion(q)}>{q} <ArrowUpRight size={13}/></button>)}</div><form className="qa-form" onSubmit={askQuestion}><input value={question} onChange={e=>setQuestion(e.target.value)} aria-label="Research question" placeholder="Ask about fundamentals, cash quality or management guidance..."/><button disabled={qaLoading||!question.trim()} type="submit">{qaLoading?<LoaderCircle className="spin" size={19}/>:<ArrowRight size={19}/>}</button></form>{answer&&<div className="research-answer"><div className="answer-label"><Sparkles size={15}/> FINN RESPONSE {answer.ai_generated?'· HOSTED AI':'· EVIDENCE ONLY'}</div><p>{answer.answer}</p>{answer.citations.length>0&&<><div className="evidence-title">Evidence ({answer.citations.length})</div><div className="answer-sources">{answer.citations.map((c,i)=><a key={i} href={c.url} target="_blank" rel="noopener noreferrer"><FileText size={15}/><span>{c.title} · p.{c.page}</span><ExternalLink size={13}/></a>)}</div></>}</div>}</section>
         </>}
       </>}
       {tab==='watchlist'&&<><div className="intro-row"><div><div className="eyebrow"><span className="eyebrow-line"/> YOUR COVERAGE</div><h1>Companies in focus<span className="teal-dot">.</span></h1><p className="page-subtitle">A diversified Indian equity universe. Every company is one tap from research.</p></div><Pill tone="teal">{companies.length} tracked</Pill></div><div className="watchlist-toolbar"><Search size={18}/><input placeholder="Filter your companies..." aria-label="Filter companies" value={searchWatchlist} onChange={e=>setSearchWatchlist(e.target.value)}/></div><div className="watchlist-grid">{companies.filter(c=>`${c.ticker} ${c.name} ${c.sector}`.toLowerCase().includes(searchWatchlist.toLowerCase())).map(c=><button className="watch-card" key={c.ticker} onClick={()=>goResearch(c.ticker)}><div className="watch-top"><div className="watch-logo">{c.ticker.slice(0,2)}</div><span className="watch-external"><ArrowUpRight size={17}/></span></div><strong>{c.name}</strong><span>{c.sector}</span><div className="watch-price"><span>{c.close!==null?`₹${formatMoney(c.close)}`:'EOD pending'}</span>{c.day_change_pct!==null&&<span className={c.day_change_pct>=0?'positive':'negative'}>{c.day_change_pct>0?'+':''}{c.day_change_pct.toFixed(2)}%</span>}</div></button>)}</div><p className="footnote">Prices, when shown, are end-of-day values. They are not a live trading terminal.</p></>}
       {tab==='settings'&&<><div className="intro-row"><div><div className="eyebrow"><span className="eyebrow-line"/> MAKE FINN YOURS</div><h1>Signal preferences<span className="teal-dot">.</span></h1><p className="page-subtitle">Choose what counts as unusual. Your preferences update the feed.</p></div></div><section className="panel settings-panel"><div className="setting-head"><div className="setting-icon"><TrendingUp size={23}/></div><div><h3>Daily price movement</h3><p>Alert when absolute close-to-close return exceeds this percentage.</p></div><strong>{thresholdPrice.toFixed(1)}%</strong></div><input className="range-input" type="range" min="0.5" max="10" step="0.5" value={thresholdPrice} onChange={e=>setThresholdPrice(Number(e.target.value))}/><div className="range-labels"><span>0.5%</span><span>10%</span></div><div className="setting-divider"/><div className="setting-head"><div className="setting-icon"><Gauge size={23}/></div><div><h3>Unusual volume multiple</h3><p>Compare current EOD volume with the previous 20 observed trading sessions.</p></div><strong>{thresholdVolume.toFixed(1)}×</strong></div><input className="range-input" type="range" min="1" max="5" step="0.25" value={thresholdVolume} onChange={e=>setThresholdVolume(Number(e.target.value))}/><div className="range-labels"><span>1×</span><span>5×</span></div><div className="setting-divider"/><div className="setting-head"><div className="setting-icon"><CalendarDays size={23}/></div><div><h3>Custom digest window</h3><p>Review signals from a time interval beyond the quick presets.</p></div></div><div className="custom-days"><input type="number" min="1" max="365" value={customDays} onChange={e=>setCustomDays(Number(e.target.value))} aria-label="Custom number of days"/><span>days</span><button className="outline-action" onClick={()=>{setWindowHours(Math.min(365,Math.max(1,customDays))*24);navTo('today');}}>Apply to inbox <ArrowRight size={16}/></button></div></section><div className="settings-bottom"><section className="panel source-policy"><div className="panel-head"><h3><ShieldCheck size={19}/> Our evidence policy</h3></div><p>FINN's research uses only primary-source company annual reports, earnings-call transcripts and original disclosures. It does not infer missing financial results or disguise samples as live events.</p><div className="source-policy-row"><span>AI provider</span><strong>{health?.ai_configured?health.ai_model:'Not configured'}</strong></div><div className="source-policy-row"><span>Backend</span><strong>{health?'Connected':'Offline'}</strong></div><div className="source-policy-row"><span>Document index</span><strong>{health?.document_count??'—'}</strong></div></section><section className="panel source-policy"><div className="panel-head"><h3><Info size={19}/> About this prototype</h3></div><p>FINN is an investor-workflow demonstration for ENAM's AI Engineer Build Challenge. It does not offer financial advice or execute trades.</p><p className="tiny-muted">Data refresh is best-effort. NSE/BSE access controls or third-party outages can interrupt fresh ingestion. Source timestamps should be checked before decisions.</p><a className="policy-link" href={`${API_BASE}/docs`} target="_blank" rel="noopener noreferrer">Explore API documentation <ExternalLink size={15}/></a></section></div></>}
     </main>
     <footer className="app-footer"><span>FINN · Thoughtful investment intelligence</span><span>Evidence over noise. Always.</span></footer>
   </div>
   <nav className="mobile-bottom-nav" aria-label="Mobile navigation">{NAV.map(item=><button key={item.id} className={tab===item.id?'mobile-nav-active':''} onClick={()=>navTo(item.id)}><item.icon size={21} strokeWidth={1.8}/><span>{item.label}</span></button>)}</nav>
   {selected&&<div className="drawer-overlay" onMouseDown={e=>{if(e.target===e.currentTarget)setSelected(null);}}><section className="detail-drawer" role="dialog" aria-modal="true" aria-label="Signal details"><div className="drawer-handle"/><div className="drawer-nav"><button onClick={()=>setSelected(null)} className="back-button"><ArrowLeft size={19}/> Back to feed</button><button className="close-button" aria-label="Close" onClick={()=>setSelected(null)}><X size={19}/></button></div><div className="drawer-body"><div className="drawer-ticker"><div className="signal-symbol"><IconForCategory category={selected.category}/></div><div><strong>{selected.company}</strong><span>{selected.ticker} · {formatTime(selected.published_at)}</span></div></div><div className="drawer-badges"><Pill tone={selected.priority==='high'?'red':selected.priority==='medium'?'amber':'neutral'}>{selected.priority==='high'?'Important':selected.priority==='medium'?'Worth a look':'Routine'}</Pill><Pill>{CATEGORY_NAMES[selected.category]??selected.category}</Pill></div><h2>{selected.title}</h2><p className="drawer-summary">{selected.summary}</p>{selected.is_illustrative&&<div className="drawer-illustration"><Info size={17}/> Fictional demonstration only. No real corporate event or source document is claimed.</div>}<div className="detail-section"><div className="detail-section-label"><Zap size={17}/> WHY FINN SURFACED THIS</div><p>{selected.reason}</p></div><div className="detail-section"><div className="detail-section-label"><FileText size={17}/> ORIGINAL EVIDENCE</div><SourceLink url={selected.source_url} label="View original disclosure"/>{!selected.source_url&&<p className="drawer-tip">Live filings will include a source link when available. FINN does not fabricate one.</p>}</div>{selected.category==='results'&&!selected.is_illustrative&&<div className="detail-section"><div className="detail-section-label"><WalletCards size={17}/> QUARTERLY RESULTS INTELLIGENCE</div>{selected.results_analysis?.rows?.length?<><p className="drawer-tip">{selected.results_analysis.period} · {selected.results_analysis.basis} basis · all figures from original filing</p><div className="results-table">{selected.results_analysis.rows.map(r=><div className="result-row" key={r.metric}><strong>{r.metric.toUpperCase()}</strong><span>{formatMoney(r.current)} {r.unit}</span><small>{r.qoq_pct!==null?`QoQ ${r.qoq_pct>0?'+':''}${r.qoq_pct}%`:'QoQ —'}</small><small>{r.yoy_pct!==null?`YoY ${r.yoy_pct>0?'+':''}${r.yoy_pct}%`:'YoY —'}</small><a href={selected.source_url||'#'} target="_blank" rel="noopener noreferrer">p.{r.page} <ExternalLink size={12}/></a></div>)}</div></>:<><p className="drawer-tip">Get Revenue, EBITDA, PBT and PAT when explicitly reported, with QoQ and YoY figures. Missing metrics stay unavailable.</p><button className="full-outline" onClick={()=>void analyzeResults(selected)} disabled={analysingResults||!selected.source_url}>{analysingResults?<LoaderCircle className="spin" size={16}/>:<Sparkles size={16}/>} {analysingResults?'Extracting verified metrics...':'Analyse original results filing'}</button>{selected.results_analysis?.note&&<p className="drawer-tip">{selected.results_analysis.note}</p>}{resultsError&&<p className="result-error">{resultsError}</p>}</>}</div>}
   <div className="detail-section"><div className="detail-section-label"><BookOpenCheck size={17}/> NEXT STEP</div><p>Review the company's fundamentals and management commentary before forming an investment judgment.</p></div></div><div className="drawer-bottom"><button className="primary-button" onClick={()=>goResearch(selected.ticker)}>Investigate {selected.ticker} <ArrowRight size={17}/></button></div></section></div>}
 </div>;
}
