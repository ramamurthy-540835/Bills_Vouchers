import type { Metadata } from 'next'
import './globals.css'
export const metadata: Metadata = { title: 'Bills & Voucher Finance', description: 'BigQuery GST finance workspace' }
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body>{children}</body></html> }
