import { Sparkles } from 'lucide-react';
export default function Brand({ small = false }: { small?: boolean }) {
 return <div className={'brand '+(small?'brand-small':'')}><div className="brand-mark"><Sparkles size={small?17:22} strokeWidth={2.5}/></div><div className="brand-name">finn<span className="brand-period">.</span></div></div>;
}
