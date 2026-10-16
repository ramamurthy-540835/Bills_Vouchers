'use client'
import {useCallback,useEffect,useState} from 'react'
import Link from 'next/link'
import {formatINR} from '../lib/format-values'

export default function ReturnWorkflow({period,canWrite,refreshKey,reviewRevision=0,confirmedCount}:{period:string,canWrite:boolean,confirmedCount?:number,refreshKey?:unknown,reviewRevision?:number}){
 const [data,setData]=useState<any>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[reason,setReason]=useState(''),[loading,setLoading]=useState(false),[loadError,setLoadError]=useState('')
 const load=useCallback(async()=>{setLoading(true);setLoadError('');try{const response=await fetch(`/api/gst/returns?period=${period}`,{cache:'no-store'});if(!response.ok)throw Error(response.status===401?'Your session expired. Sign in again.':response.status===403?'You do not have permission to perform this action.':'Please retry. Your saved records have not been changed.');setData(await response.json())}catch(e){setLoadError(e instanceof Error?e.message:'Please retry.')}finally{setLoading(false)}},[period])
 useEffect(()=>{setData(null);setError('');void load()},[load,refreshKey,reviewRevision])
 async function act(action:string){setBusy(true);setError('');try{
  const csrf=await fetch('/api/auth/csrf');const {token}=await csrf.json()
  const response=await fetch(`/api/gst/returns/${action}?period=${period}`,{method:'POST',headers:{'content-type':'application/json','x-csrf-token':token},body:JSON.stringify({version:data.version,reason})})
  const result=await response.json();if(!response.ok)throw Error(result.error?.message||result.detail?.message||(typeof result.detail==='string'?result.detail:'Return update failed.'))
  setReason('');await load()
 }catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 const editable=canWrite&&data&&!data.is_test&&!loading&&!loadError
 return <section className="bv-card return-workflow-card" aria-label="Return preparation"><h2>Return Preparation &amp; Review</h2>
 <p className="section-description">Prepare, review and approve GST working papers.</p><details className="financial-disclosure"><summary>About return preparation</summary><p>Working papers are based on canonical bills. Approved snapshots are immutable.</p><p>Maker-checker separation applies: a different tax administrator must approve the prepared snapshot.</p><p>Government-format exports and direct filing are not enabled.</p></details>
 {error&&<p role="alert">{error}</p>}{loadError&&<div className="financial-error" role="alert"><h3>Return preparation could not be loaded. Please retry.</h3><p>{loadError}</p><button className="button secondary" disabled={loading} onClick={()=>void load()}>Retry return preparation</button></div>}{loading&&<p role="status">Loading return preparation...</p>}{data&&<>
 {!data.snapshot&&<p>No return working paper has been prepared for this period.</p>}{confirmedCount===0&&<p>No confirmed invoices are available. Confirm the applicable bills before preparing a working paper; nil-return preparation is not supported.</p>}{!canWrite&&<p>You do not have permission to perform this action.</p>}<p role="status">Status: {data.state.replaceAll('_',' ')}</p>{data.is_test&&<p>Synthetic workspaces cannot prepare or approve real returns.</p>}
 {data.source_changed&&<p role="alert">Source data changed. Reopen if needed and prepare a fresh snapshot before approval.</p>}
 {data.snapshot&&<details className="financial-disclosure"><summary>View prepared working paper</summary><p>This is the saved working-paper snapshot, not a government filing export.</p><div className="recon-list">{Object.entries(data.snapshot.summary?.totals||{}).map(([key,value])=><div key={key}><span>{key.replaceAll('_',' ')}</span><strong>{formatINR(value)}</strong></div>)}</div><p>{data.snapshot.invoices?.length} confirmed invoices in this snapshot.</p></details>}{data.snapshot&&<p>Prepared {data.snapshot.prepared_at} for {data.snapshot.gstin}; {data.snapshot.invoices.length} confirmed invoices.</p>}
 {editable&&<div className="filing-actions">
 {['draft','prepared','reopened'].includes(data.state)&&<button className="button primary" disabled={busy||confirmedCount===0} onClick={()=>act('prepare')}>Prepare snapshot</button>}
 {data.state==='prepared'&&data.maker_id===data.user_id&&<button className="button primary" disabled={busy||data.source_changed} onClick={()=>act('review')}>Submit for review</button>}
 {data.can_review&&['under_review','approved','exported'].includes(data.state)&&<>
 <label>Review or reopen reason<textarea value={reason} maxLength={1000} disabled={busy} onChange={e=>setReason(e.target.value)}/></label>
 {data.state==='under_review'&&data.maker_id!==data.user_id&&<><button className="button primary" disabled={busy||data.source_changed||reason.trim().length<3} onClick={()=>act('approve')}>Approve snapshot</button><button className="button secondary" disabled={busy||reason.trim().length<3} onClick={()=>act('reject')}>Return to draft</button></>}
 <button className="button secondary" disabled={busy||reason.trim().length<3} onClick={()=>act('reopen')}>Reopen period</button>
 </>}
 </div>}
 {!loading&&!loadError&&data.state==='approved'&&!data.source_changed&&<Link className="button secondary" href={`/api/gst/returns/working-paper?period=${period}`}>Download approved working paper (draft format)</Link>}
 </>}
 </section>
}
