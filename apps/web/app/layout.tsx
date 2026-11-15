import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = {
  title: 'FINN — Less noise. More conviction.',
  description: 'Source-grounded investor intelligence. Understand what changed, why it matters, and what management actually delivered.',
};
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
