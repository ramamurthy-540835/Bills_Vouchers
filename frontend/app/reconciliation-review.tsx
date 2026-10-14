'use client'
import {useState} from 'react'

const labels:Record<string,string>={needs_correction:'Needs correction',awaiting_supplier:'Awaiting supplier',reviewed:'Evidence reviewed',reopened:'Review reopened'}

export default function ReconciliationReview({row,period,sourceHash,canReview,onSaved}:{row:any;period:string;sourceHash:string;canReview:boolean;onSaved:()=>void}){
 const [decision,setDecision]=useState('needs_correction'),[reason,setReason]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState(''),[history,setHistory]=useState<any[]|null>(null),[before,setBefore]=useState<number|null>(null)
 async function loadHistory(more=false){setBusy(true);setError('');try{
  const url=`/api/gst/bills/reconciliation/history?period=${encodeURIComponent(period)}&case_id=${encodeURIComponent(row.id)}${more&&before?`&before_version=${before}`:''}`
  const response=await fetch(url,{cache:'no-store'});if(!response.ok)throw Error('Could not load review history.')
  const result=await response.json();setHistory(previous=>more?[...(previous||[]),...result.history]:result.history);setBefore(result.next_before_version)
 }catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 async function save(){setBusy(true);setError('');try{
  const csrf=await fetch('/api/auth/csrf');if(!csrf.ok)throw Error('Your session could not be validated. Sign in again.')
  const token=(await csrf.json()).token
  const response=await fetch(`/api/gst/bills/reconciliation/review?period=${encodeURIComponent(period)}`,{method:'POST',headers:{'content-type':'application/json','x-csrf-token':token},body:JSON.stringify({case_id:row.id,source_hash:sourceHash,version:row.review?.version||0,decision,reason})})
  const result=await response.json();if(!response.ok)throw Error(result.error?.message||(typeof result.detail==='string'?result.detail:'Could not save the review.'))
  onSaved()
 }catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 return <div>
  <h3>Review decision</h3>
  {row.review?<p>{labels[row.review.decision]||row.review.decision} · version {row.review.version}. {row.review.reason} {row.review.stale&&<strong>Evidence has changed; review again.</strong>}</p>:<p>No review decision recorded.</p>}
  {error&&<p role="alert">{error}</p>}
  <button type="button" className="button secondary" disabled={busy} onClick={()=>loadHistory()}>View review history</button>
  {history&&<><ul>{history.map(entry=><li key={entry.version}>Version {entry.version}: {labels[entry.decision]||entry.decision} — {entry.reason}. Reviewer {entry.actor_id}, {entry.created_at}.</li>)}</ul>{!history.length&&<p>No previous reviews.</p>}{before&&<button type="button" disabled={busy} onClick={()=>loadHistory(true)}>Load older reviews</button>}</>}
  {canReview?<form onSubmit={e=>{e.preventDefault();save()}} style={{display:'grid',gap:8,minWidth:0}}>
   <p>Recording a review does not approve an ITC claim or resolve a source mismatch. Correct the underlying evidence where necessary.</p>
   <label>Review outcome<select style={{display:'block',width:'100%'}} value={decision} disabled={busy} onChange={e=>setDecision(e.target.value)}>{Object.entries(labels).filter(([key])=>key!=='reopened'||row.review).map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label>
   <label>Review reason<textarea style={{display:'block',width:'100%'}} required minLength={3} maxLength={1000} disabled={busy} value={reason} onChange={e=>setReason(e.target.value)}/></label>
   <button className="button primary" disabled={busy||reason.trim().length<3}>{busy?'Saving…':'Save review decision'}</button>
  </form>:<p>An authorized accountant or tax administrator can record review decisions.</p>}
 </div>
}
