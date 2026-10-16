import type {ReactNode} from 'react'
import GstinVerification from './gstin-verification'
export default function CompanyChecks({checks,websiteEditor}:{checks:any;websiteEditor?:ReactNode}){
 if(!checks)return null
 return <section className="bv-card settings-card" aria-label="Saved company checks"><h2>Saved company checks</h2>
  <p className="settings-intro">Review saved registration and business verification details.</p>
  <h3>Registration checks</h3>
  <dl className="settings-rows"><div><dt>GSTIN format</dt><dd>{checks.gstin_format_message||'Not provided'}</dd></div></dl>
  <p className="settings-note">A valid format does not prove an active GST registration or a legal-name match.</p>
  <GstinVerification/>
  <div className="settings-actions"><a className="button primary" href="https://services.gst.gov.in/services/searchtp" target="_blank" rel="noopener noreferrer">Check taxpayer on the official GST portal</a></div>
  <p className="settings-note">Use the GST portal to compare the saved GSTIN, legal name, registration status and address with the official record. Opening the portal does not mark this account verified.</p>
  {websiteEditor||<div className="settings-subsection"><h3>Company website</h3>{checks.website_url?<><a href={checks.website_url} target="_blank" rel="noopener noreferrer">{checks.website_url}</a><p className="settings-note">Saved. Website ownership has not been verified.</p></>:<span className="settings-badge">Not saved</span>}</div>}
 </section>
}
