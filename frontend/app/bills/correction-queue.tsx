'use client'
import {useEffect,useState} from 'react'

const stages:Record<string,string>={
 active:'All active corrections',rejected:'Rejected — awaiting correction',
 correction_requested:'Correction requested',corrected:'Corrected — awaiting resubmission',
 resubmitted:'Resubmitted — awaiting review',approved:'Approved corrections',
}
type Row={invoice_id:string,invoice_number:string,supplier_legal_name:string,
 correction_stage:string,rejection_reason:string,correction_reason:string,correction_at:string}
export default function CorrectionQueue({api,period,revision,busy,onReview}:{
 api:(path:string)=>Promise<any>,period:string,revision:number,busy:boolean,onReview:(id:string)=>void
}){
 const [expanded,setExpanded]=useState(false),[stage,setStage]=useState('active'),[offset,setOffset]=useState(0)
 const [rows,setRows]=useState<Row[]>([]),[next,setNext]=useState<number|null>(null)
 const [loading,setLoading]=useState(false),[error,setError]=useState(''),[retry,setRetry]=useState(0)
 useEffect(()=>{
  if(!expanded)return
  let active=true
  setLoading(true);setError('');setRows([]);setNext(null)
  api(`/corrections?period=${encodeURIComponent(period)}&state=${stage}&offset=${offset}`)
   .then(result=>{if(active){setRows(result.invoices);setNext(result.next_offset)}})
   .catch(e=>{if(active)setError(e.message||'Correction queue could not be loaded.')})
   .finally(()=>{if(active)setLoading(false)})
  return()=>{active=false}
 },[api,period,stage,offset,expanded,revision,retry])
 return <section className="bv-card" aria-label="Bill correction queue">
  <div className="bill-support-header"><div><h2>Bill corrections</h2>
   <p>Find rejected bills, track corrections and review resubmissions for the selected period.</p></div>
   <button className="button secondary" aria-expanded={expanded} onClick={()=>setExpanded(!expanded)}>
    {expanded?'Hide correction queue':'Open correction queue'}</button></div>
  {expanded&&<><div className="account-form"><label>Correction state
   <select aria-label="Correction state" value={stage} onChange={e=>{setStage(e.target.value);setOffset(0)}}>
    {Object.entries(stages).map(([value,label])=><option key={value} value={value}>{label}</option>)}
   </select></label></div>
   <p>Corrections require validation and review before confirmation. Queue membership does not approve GST or ITC.</p>
   {loading?<p role="status">Loading corrections…</p>:error?<div role="alert"><p>{error}</p>
    <button className="button secondary" onClick={()=>setRetry(value=>value+1)}>Retry correction queue</button></div>:
    <>{rows.length===0?<p>No bills match this correction state for the selected period.</p>:
     <ul>{rows.map(row=><li key={row.invoice_id}><h3>{row.invoice_number||'Invoice number not provided'}</h3>
      <p>{row.supplier_legal_name||'Supplier not provided'} · {stages[row.correction_stage]||row.correction_stage}</p>
      {row.rejection_reason&&<p>Rejection: {row.rejection_reason}</p>}
      {row.correction_reason&&<p>Correction: {row.correction_reason}</p>}
      {row.correction_at&&<p>Last correction action: <time dateTime={row.correction_at}>{new Date(row.correction_at).toLocaleString('en-IN')}</time></p>}
      <button className="button secondary" disabled={busy} onClick={()=>onReview(row.invoice_id)}>Review correction</button>
     </li>)}</ul>}
     <div className="filing-actions">
      {offset>0&&<button className="button secondary" onClick={()=>setOffset(Math.max(0,offset-50))}>Previous corrections</button>}
      {next!==null&&<button className="button secondary" onClick={()=>setOffset(next)}>Next corrections</button>}
      <button className="button secondary" onClick={()=>{setOffset(0);setRetry(value=>value+1)}}>Refresh corrections</button>
     </div></>}
  </>}
 </section>
}
