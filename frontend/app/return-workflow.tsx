'use client'
import {useCallback,useEffect,useState} from 'react'
import Link from 'next/link'

export default function ReturnWorkflow({period,canWrite}:{period:string,canWrite:boolean}){
 const [data,setData]=useState<any>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[reason,setReason]=useState('')
 const load=useCallback(async()=>{const response=await fetch(`/api/gst/returns?period=${period}`,{cache:'no-store'});if(!response.ok)throw Error('Could not load return preparation.');setData(await response.json())},[period])
 useEffect(()=>{setData(null);load().catch(e=>setError(e.message))},[load])
 async function act(action:string){setBusy(true);setError('');try{
  const csrf=await fetch('/api/auth/csrf');const {token}=await csrf.json()
  const response=await fetch(`/api/gst/returns/${action}?period=${period}`,{method:'POST',headers:{'content-type':'application/json','x-csrf-token':token},body:JSON.stringify({version:data.version,reason})})
  const result=await response.json();if(!response.ok)throw Error(result.error?.message||result.detail?.message||(typeof result.detail==='string'?result.detail:'Return update failed.'))
  setReason('');await load()
 }catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 const editable=canWrite&&data&&!data.is_test
 return <section className="bv-card"><h2>Return preparation and review</h2>
 <p>Prepare an immutable working paper from canonical bills. A different tax administrator must approve it. Government-format exports and direct filing are not enabled.</p>
 {error&&<p role="alert">{error}</p>}{!data?<button className="button secondary" onClick={()=>load().catch(e=>setError(e.message))}>Reload return preparation</button>:<>
 <p role="status">Status: {data.state.replaceAll('_',' ')}</p>{data.is_test&&<p>Synthetic workspaces cannot prepare or approve real returns.</p>}
 {data.source_changed&&<p role="alert">Source data changed. Reopen if needed and prepare a fresh snapshot before approval.</p>}
 {data.snapshot&&<p>Prepared {data.snapshot.prepared_at} for {data.snapshot.gstin}; {data.snapshot.invoices.length} confirmed invoices.</p>}
 {editable&&<div className="filing-actions">
 {['draft','prepared','reopened'].includes(data.state)&&<button className="button primary" disabled={busy} onClick={()=>act('prepare')}>Prepare snapshot</button>}
 {data.state==='prepared'&&data.maker_id===data.user_id&&<button className="button primary" disabled={busy||data.source_changed} onClick={()=>act('review')}>Submit for review</button>}
 {data.can_review&&['under_review','approved','exported'].includes(data.state)&&<>
 <label>Review or reopen reason<textarea value={reason} maxLength={1000} disabled={busy} onChange={e=>setReason(e.target.value)}/></label>
 {data.state==='under_review'&&data.maker_id!==data.user_id&&<><button className="button primary" disabled={busy||data.source_changed||reason.trim().length<3} onClick={()=>act('approve')}>Approve snapshot</button><button className="button secondary" disabled={busy||reason.trim().length<3} onClick={()=>act('reject')}>Return to draft</button></>}
 <button className="button secondary" disabled={busy||reason.trim().length<3} onClick={()=>act('reopen')}>Reopen period</button>
 </>}
 </div>}
 {data.state==='approved'&&!data.source_changed&&<Link className="button secondary" href={`/api/gst/returns/working-paper?period=${period}`}>Download approved working paper (draft format)</Link>}
 </>}
 </section>
}
