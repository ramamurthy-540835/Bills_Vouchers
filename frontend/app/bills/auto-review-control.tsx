'use client'
import {useEffect} from 'react'
import {GST} from '../../lib/copy/gst'

const statuses:Record<string,string>={not_started:'Auto Review Not Started',running:'Auto Review Running',auto_confirmed:'Auto Confirmed',manual_required:'Manual Review Required',failed:'Auto Review Failed',cancelled:'Auto Review Cancelled'}
const checks:Record<string,string>={required_fields:'Required fields',duplicate:'Duplicate check',gst_calculation:'GST calculation',invoice_total:'Invoice total',original_evidence:'Original evidence',gst_policy:'Approved GST policy'}
export default function AutoReviewControl({invoice,write,busy,dirty,change,run,refresh}:{invoice:any;write:boolean;busy:boolean;dirty:boolean;change:(enabled:boolean)=>void;run:()=>void;refresh:()=>void}){
 const policy=invoice.auto_review||{enabled:false,status:'not_started'}
 useEffect(()=>{if(policy.status!=='running')return;const timer=setInterval(refresh,2500);return()=>clearInterval(timer)},[policy.status,refresh])
 const reason=invoice.auto_review_locked||(invoice.status==='rejected'?'Rejected bills require the existing correction workflow.':!write?'You do not have permission to confirm bills.':dirty?'Save your changes before running Auto Review.':'')
 return <section className="auto-review-card" aria-label="Auto Review controls">
  <div className="auto-review-heading"><div><h3>Auto Review</h3><p>Automatically validate and confirm bills that pass all checks.</p></div>
   <button type="button" role="switch" aria-label="Auto Review" aria-checked={policy.enabled} className="auto-review-switch" disabled={busy||Boolean(reason)||(invoice.status==='confirmed'&&!policy.enabled)} onClick={()=>change(!policy.enabled)}>{policy.enabled?'ON':'OFF'}</button></div>
  <p role="status">{statuses[policy.status]||'Auto Review Not Started'}</p>
  {reason&&<p>{reason}</p>}
  {invoice.status==='confirmed'&&<p>This bill is confirmed. Turning OFF does not undo confirmation.</p>}
  {policy.status==='running'&&<p>Review is queued or processing. You may turn OFF to cancel before confirmation commits.</p>}
  {!!policy.reasons?.length&&<ul>{policy.reasons.map((r:string)=><li key={r}>{GST.reasons[r]||r}</li>)}</ul>}
  {!!Object.keys(policy.checks||{}).length&&<ul>{Object.entries(policy.checks).map(([key,passed])=><li key={key}>{checks[key]||key}: {passed?'Passed':'Requires review'}</li>)}</ul>}
  {write&&policy.enabled&&invoice.status!=='confirmed'&&policy.status!=='running'&&<button type="button" className="button primary" disabled={busy||Boolean(reason)} onClick={run}>Run Auto Review</button>}
 </section>
}
