export default function CompanyChecks({checks}:{checks:any}){
 if(!checks)return null
 return <section className="bv-card" aria-label="Saved company checks"><h2>Saved company checks</h2>
  <p><strong>GSTIN format: </strong>{checks.gstin_format_message}</p>
  <p><strong>Government registration verification: </strong>Not connected. A valid format does not prove an active GST registration or a legal-name match.</p>
  <a className="button secondary" href="https://services.gst.gov.in/services/searchtp" target="_blank" rel="noopener noreferrer">Check taxpayer on the official GST portal</a>
  <p>Compare the saved GSTIN, legal name, registration status and business address with the official result. Opening the portal does not mark this account verified.</p>
  {checks.website_url?<p><strong>Saved website: </strong><a href={checks.website_url} target="_blank" rel="noopener noreferrer">{checks.website_url}</a> — ownership has not been verified.</p>:<p>No valid company website saved.</p>}
 </section>
}
