import type { Metadata } from 'next'
import './globals.css'
import './workspace.css'
import './demo.css'
import './v7.css'
import './gst-easy.css'
export const metadata: Metadata = { title: 'Bills & Voucher Finance', description: 'GST finance workspace' }
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body>{children}</body></html> }
