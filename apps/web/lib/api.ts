export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '');
export type Priority = 'high' | 'medium' | 'low';
export type ResultAnalysis = { basis: string; period: string; note: string | null; rows: { metric: string; current: number; previous: number | null; year_ago: number | null; qoq_pct: number | null; yoy_pct: number | null; unit: string; page: number; quote: string }[] };
export type FeedItem = {
  id: string; ticker: string; company: string; title: string; summary: string; reason: string;
  category: string; priority: Priority; published_at: string; source_url: string | null;
  source?: string; is_illustrative: boolean; type: string; body?: string; results_analysis?: ResultAnalysis | null;
};
export type FeedResponse = { items: FeedItem[]; as_of?:string; count: number; illustrative: boolean; high: number; medium: number; low: number; window_hours: number };
export type Company = { ticker: string; name: string; sector: string; in_watchlist: boolean; close: number | null; day_change_pct: number | null; volume_multiple: number | null; price_day: string | null; documents?: Doc[]; metrics?: Metric[]; is_live_data?: boolean };
export type Doc = { id: string; title: string; kind: string; url: string; published_label: string; status: string };
export type Metric = { id: string; metric: string; period: string; value: number; unit: string; basis: string; page: number; document_id: string };
export type Price = { day: string; close: number; volume: number; day_change_pct: number | null; volume_multiple: number | null };
export type PromiseClaim = { id: string; metric: string; period: string; target_low: number | null; target_high: number | null; unit: string; quote: string; page: number; source_url: string | null; actual: number | null; actual_url: string | null; actual_page: number | null; status: 'met' | 'missed' | 'pending' | 'unverifiable'; rationale: string };
export type Answer = { ticker: string; answer: string; citations: { title: string; page: number; url: string; excerpt: string }[]; ai_generated: boolean; needs_documents: boolean; error?: string };
export type Health = { status: string; ai_configured: boolean; ai_model: string | null; company_count: number; announcement_count: number; document_count: number };
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { ...init, cache: 'no-store', headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) } });
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try { const payload = await response.json(); detail = typeof payload.detail === 'string' ? payload.detail : detail; } catch { /* no JSON */ }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}
export function formatTime(v: string): string {
  const d = new Date(v);
  return Number.isNaN(d.valueOf()) ? 'Unknown time' : d.toLocaleString('en-IN', { timeZone:'Asia/Kolkata',year:'numeric',day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit', hour12: true });
}
export function formatMoney(v: number | null): string {
  if (v === null || !Number.isFinite(v)) return '—';
  return new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 }).format(v);
}
export const CATEGORY_NAMES: Record<string, string> = {
  results: 'Financial results', 'M&A': 'M&A', fund_raise: 'Fundraising', management_change: 'Management', litigation: 'Legal & regulatory', insider_trading: 'Insider activity', earnings_call: 'Earnings calls', investor_meetings: 'Investor meetings', credit_rating: 'Credit rating', dividend: 'Dividend', bonus_split: 'Bonus / split', capex: 'Capex', press_release: 'Company update', postal_ballot: 'Postal ballot', agm_egm: 'Shareholder meeting', pledging: 'Share pledging', unclassified: 'Routine disclosure', market_move: 'Market activity'
};
export function cleanError(e: unknown): string { return e instanceof Error ? e.message : 'Request failed. Please try again.'; }
