'use client'
import {useEffect,useState} from 'react'

export const rejectionReasons=[
 ['duplicate_invoice','Duplicate invoice'],['invalid_gstin','Invalid GSTIN'],
 ['incorrect_rate','Incorrect GST rate'],['gst_amount_mismatch','GST amount mismatch'],
 ['invoice_total_mismatch','Invoice total mismatch'],['missing_number','Missing invoice number'],
 ['missing_date','Missing invoice date'],['supplier_mismatch','Supplier details mismatch'],
 ['customer_mismatch','Customer details mismatch'],['incorrect_tax_head','Incorrect tax head'],
 ['low_quality','Low-quality evidence'],['incomplete_document','Incomplete document'],
 ['wrong_business','Wrong business'],['unsupported_document','Unsupported document'],['other','Other']
]

export default function ReviewEvidence({invoice,write,busy,dirty,api,onBusy,onUpdated}:{invoice:any;write:boolean;busy:boolean;dirty:boolean;api:(path:string,method?:string,body?:any,version?:number)=>Promise<any>;onBusy:(value:boolean)=>void;onUpdated:(value:any)=>void}){
 const [comparison,setComparison]=useState<any>(null),[events,setEvents]=useState<any[]>([]),[reason,setReason]=useState(''),[error,setError]=useState(''),[revision,setRevision]=useState(0)
 useEffect(()=>{let active=true;setComparison(null);setError('');Promise.all([api(`/${invoice.invoice_id}/gst-comparison`),api(`/${invoice.invoice_id}/review-history`)]).then(([c,h])=>{if(active){setComparison(c);setEvents(h.events)}}).catch(e=>{if(active)setError(e.message)});return()=>{active=false}},[invoice.invoice_id,invoice.version,revision,api])
 async function change(action:string){if(reason.trim().length<3){setError('Enter a correction reason.');return}onBusy(true);setError('');try{onUpdated(await api(`/${invoice.invoice_id}/correction/${action}`,'POST',{reason},invoice.version));setReason('')}catch(e){setError((e as Error).message)}finally{onBusy(false)}}
 return <section aria-label="GST comparison and correction">
  <h3>GST comparison</h3>
  <p>Original evidence is retained. Calculations check arithmetic at the declared rate; they do not verify the legal rate or eligibility.</p>
  {error&&<p role="alert">{error} <button type="button" className="button secondary" onClick={()=>setRevision(v=>v+1)}>Retry</button></p>}
  {!comparison&&!error&&<p role="status">Loading comparison...</p>}
  {comparison&&<><dl><dt>First extracted GST (not a verified source amount)</dt><dd>{comparison.source_gst_amount??'Unavailable'}</dd><dt>Current recorded GST</dt><dd>{comparison.extracted_gst_amount}</dd><dt>Confirmed GST</dt><dd>{comparison.approved_gst_amount??'Not confirmed'}</dd></dl>
   <div style={{overflowX:'auto'}}><table><caption>Declared-rate arithmetic, INR</caption><thead><tr><th>Line</th><th>Recorded GST</th><th>Calculated GST</th><th>Difference</th><th>Status</th></tr></thead><tbody>{comparison.rows.map((r:any)=><tr key={r.line}><td>{r.line}</td><td>{r.extracted_gst_amount}</td><td>{r.system_calculated_gst_amount}</td><td>{r.difference_amount}</td><td>{r.classification.replaceAll('_',' ')}{r.cess_review_required?' / Cess needs review':''}</td></tr>)}</tbody></table></div></>}
  {invoice.correction_state&&invoice.correction_state!=='none'&&<p>Correction status: <strong>{invoice.correction_state.replaceAll('_',' ')}</strong></p>}
  {write&&invoice.status==='rejected'&&<><label className="bill-rejection-reason">Correction reason<textarea value={reason} maxLength={1000} onChange={e=>setReason(e.target.value)} disabled={busy}/></label>
   <div className="filing-actions">{['none','rejected',undefined].includes(invoice.correction_state)&&<button className="button primary" disabled={busy||dirty} onClick={()=>change('request-correction')}>Request correction</button>}
   {invoice.correction_state==='corrected'&&<button className="button primary" disabled={busy||dirty} onClick={()=>change('resubmit')}>Resubmit corrected bill</button>}
   {invoice.correction_state==='correction_requested'&&<p>Edit the bill fields and save changes before resubmitting.</p>}</div></>}
  <details><summary>Review and correction history</summary>{events.length?events.map((event,index)=><p key={index}>{event.created_at} · {event.action} · Version {event.version} · {event.correction_reason||event.rejection_reason||'Recorded in audit history'}</p>):<p>No review history loaded.</p>}</details>
 </section>
}
