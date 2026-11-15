'use client';
import { Price, formatMoney } from '@/lib/api';
export default function TrendChart({ points }: { points: Price[] }) {
  if (points.length < 2) return <div className="chart-empty"><div className="empty-line" />Price history appears here after the EOD source refresh.</div>;
  const w=640,h=205,pad=22;
  const vals=points.map(p=>p.close),lo=Math.min(...vals),hi=Math.max(...vals),spread=Math.max(hi-lo,1);
  const xy=points.map((p,i)=>({x:pad+i*(w-2*pad)/(points.length-1),y:h-pad-(p.close-lo)/spread*(h-2*pad)}));
  const path=xy.map((p,i)=>`${i?'L':'M'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ');
  const area=path+` L ${xy[xy.length-1].x.toFixed(1)} ${h-pad} L ${xy[0].x.toFixed(1)} ${h-pad} Z`;
  const positive=vals[vals.length-1]>=vals[0];
  return <div className="price-chart"><div className="chart-top"><div><span className="chart-eyebrow">LAST OBSERVED CLOSE</span><strong>₹{formatMoney(vals[vals.length-1])}</strong></div><span className={'chart-change '+(positive?'gain':'loss')}>{positive?'+':''}{((vals[vals.length-1]/vals[0]-1)*100).toFixed(2)}% over displayed period</span></div><svg viewBox={`0 0 ${w} ${h}`} className="chart-svg" role="img" aria-label="Historical closing price chart"><defs><linearGradient id="lineFill" x1="0" y1="0" x2="0" y2="1"><stop stopColor="#078b80" stopOpacity="0.18"/><stop offset="1" stopColor="#078b80" stopOpacity="0"/></linearGradient></defs>{[0,1,2,3].map(i=><line key={i} x1={pad} x2={w-pad} y1={pad+i*(h-2*pad)/3} y2={pad+i*(h-2*pad)/3} stroke="#e8efed" strokeDasharray="4 7"/>)}<path d={area} fill="url(#lineFill)"/><path d={path} fill="none" stroke="#078b80" strokeWidth="3.5" strokeLinejoin="round" strokeLinecap="round"/><circle cx={xy[xy.length-1].x} cy={xy[xy.length-1].y} r="5" fill="#078b80" stroke="white" strokeWidth="2.5"/></svg><div className="chart-labels"><span>{points[0].day}</span><span>{points[points.length-1].day}</span></div></div>;
}
