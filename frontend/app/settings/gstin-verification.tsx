"use client"
import {useEffect,useState} from 'react'
const labels:Record<string,string>={not_configured:'Automatic verification not configured',not_checked:'Not checked',pending:'Verification pending',verified:'Verified against provider',mismatch:'Details mismatch',inactive:'Inactive or cancelled registration',failed:'Verification failed',stale:'Verification expired or profile changed',not_found:'Taxpayer record not found'}
export default function GstinVerification(){
 const [data,setData]=useState<any>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[revision,setRevision]=useState(0)
 useEffect(()=>{const controller=new AbortController();setData(null);setError('');fetch('/api/businesses/current/gstin-verification',{cache:'no-store',signal:controller.signal}).then(async response=>{if(!response.ok)throw Error('Verification status could not be loaded. Please retry.');setData(await response.json())}).catch(e=>{if(!controller.signal.aborted)setError(e.message)});return()=>controller.abort()},[revision])
 async function verify(){setBusy(true);setError('');try{
  const csrf=await fetch('/api/auth/csrf');if(!csrf.ok)throw Error('Please sign in again.')
  const {token}=await csrf.json()
  const response=await fetch('/api/businesses/current/verify-gstin',{method:'POST',headers:{'x-csrf-token':token}})
  const result=await response.json();if(!response.ok)throw Error(result.error?.message||result.detail||'Verification failed. Please retry.')
  setData(result)
 }catch(e){setError(e instanceof Error?e.message:'Verification failed.')}finally{setBusy(false)}}
 return <div className="settings-subsection" aria-label="GST registration verification"><h3>Government registration verification</h3>
 <p aria-live="polite"><span className="settings-badge">{busy?'Verification pending':data?labels[data.state]||'Verification unavailable':error?'Verification unavailable':'Loading verification status...'}</span></p>
 {data&&!data.automatic_available&&<p className="settings-note">Automatic verification not configured. You can check the official portal manually; opening it does not verify this account.</p>}
 {data?.state==='pending'&&!busy&&<p className="settings-note">A lookup is in progress. Refresh the status shortly.</p>}
 {data?.source&&<dl className="settings-rows"><div><dt>Source</dt><dd>{data.source}</dd></div><div><dt>Checked at</dt><dd>{data.checked_at?new Date(data.checked_at).toLocaleString('en-IN'):'Not recorded'}</dd></div><div><dt>Taxpayer record found</dt><dd>{data.taxpayer_found===true?'Yes':data.taxpayer_found===false?'No':'Not established'}</dd></div><div><dt>Registration status</dt><dd>{data.registration_status||'Not established'}</dd></div><div><dt>Business-name match</dt><dd>{data.business_name_match===true?'Matches':data.business_name_match===false?'Does not match':'Not established'}</dd></div><div><dt>Freshness</dt><dd>{data.fresh?'Within the 24-hour freshness window':'Stale or not established'}</dd></div></dl>}
 {data?.record?.found&&<details className="financial-disclosure"><summary>Provider details and comparison</summary><dl className="settings-rows">{[['GSTIN checked',data.record.gstin],['Legal name',data.record.legal_name],['Trade name',data.record.trade_name],['Registered address',data.record.address],['Registration type',data.record.registration_type]].map(([label,value])=><div key={label}><dt>{label}</dt><dd>{value||'Not supplied by provider'}</dd></div>)}</dl><p>Names and supplied address details are compared conservatively. Differences require review; saved business details are never overwritten.</p></details>}
 {data?.state==='failed'&&<p className="settings-note">The lookup did not establish a valid registration result. Retry later or check the official portal.</p>}
 <div className="settings-actions">{data?.automatic_available&&data?.can_verify&&<button className="button primary" disabled={busy||data.state==='pending'||!data.checksum_valid} onClick={verify}>Verify GSTIN</button>}{(error||data?.state==='pending')&&<button className="button primary" disabled={busy} onClick={()=>setRevision(value=>value+1)}>Refresh verification status</button>}</div>
 {error&&<p role="alert">{error}</p>}
 <p className="settings-note">Provider registration checks do not verify GSTIN ownership or complete KYC. They do not approve ITC or authorize tax filing.</p>
 </div>
}
