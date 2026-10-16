import Link from 'next/link'
export default function HelpContent({permissions}:{permissions:string[]}){
 return <section className="bv-card settings-card"><h2>Using GST Easy</h2><p className="settings-intro">Find the right next step for your business and account.</p>
 <div className="help-sections">
 <section><h3>Getting Started</h3><ul><li>Complete your Business Profile and upload your business logo.</li><li>Upload bills and review the extracted invoice values.</li><li>Confirm accurate invoices to include them in your dashboard and reports.</li></ul></section>
 <section><h3>Team Access</h3><ul><li>Business owners can invite accountants and viewers.</li><li>Workspace access does not grant access to unrelated businesses.</li></ul></section>
 <section><h3>Account Help</h3><ul><li>Use sign-in verification and recovery links for password problems.</li><li>Contact your business owner for workspace access issues.</li><li>Never share passwords or verification codes.</li></ul></section>
 <section><h3>Important Notes</h3><ul><li>GSTIN format checks do not prove government registration.</li><li>Returns and calculations require accountant review.</li></ul></section>
 </div><div className="settings-subsection"><h3>Quick Links</h3><nav className="settings-actions" aria-label="Help quick links">{permissions.includes('view_workspace')&&<><Link className="button secondary" href="/settings/profile">Business Profile</Link><Link className="button secondary" href="/bills">Bills &amp; Vouchers</Link></>}{permissions.includes('view_reports')&&<Link className="button secondary" href="/reports">Reports</Link>}</nav></div></section>
}
