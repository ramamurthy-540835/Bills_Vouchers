'use client'
import {useState} from 'react'

export default function SourceIntake({api}:{api:(path:string,method?:string,body?:any)=>Promise<any>}){
 const [source,setSource]=useState('vendor'),[file,setFile]=useState<File|null>(null),[busy,setBusy]=useState(false),[message,setMessage]=useState(''),[preview,setPreview]=useState<any>(null),[history,setHistory]=useState<any[]>([])
 async function submit(stage:boolean){if(!file)return;setBusy(true);setMessage('');try{const data=new FormData();data.append('source',source);data.append('file',file);const result=await api('/intake/'+(stage?'batches':'preview'),'POST',data);if(stage){setMessage(`Import ${result.batch_id} ${result.replayed?'already exists':'staged'}. No financial invoices were created.`);setPreview(null)}else setPreview(result)}catch(e){setMessage((e as Error).message)}finally{setBusy(false)}}
 async function load(){setBusy(true);try{setHistory((await api('/intake/batches')).batches)}catch(e){setMessage((e as Error).message)}finally{setBusy(false)}}
 return <section className="bv-card"><details><summary>Bulk source intake</summary>
 <p>Preview and retain Vendor, Customer or Driver records for reconciliation. This intake stages source events; it does not create or confirm financial invoices.</p>
 <p>CSV, XLSX or JSON; maximum 10 MB and 10,000 records. Required columns: source_record_id, source_version, event_type. Use invoice, credit_note, debit_note, trip, payment or settlement as the event type.</p>
 <div className="account-form"><label>Source system<select aria-label="Source system" disabled={busy} value={source} onChange={e=>{setSource(e.target.value);setPreview(null)}}><option value="vendor">Vendor App</option><option value="customer">Customer App</option><option value="driver">Driver App</option></select></label><label>Source file<input type="file" accept=".csv,.xlsx,.json" disabled={busy} onChange={e=>{setFile(e.target.files?.[0]||null);setPreview(null)}}/></label></div>
 <div className="filing-actions"><button className="button secondary" disabled={busy||!file} onClick={()=>submit(false)}>Preview import</button><button className="button primary" disabled={busy||!preview} onClick={()=>submit(true)}>Stage source records</button><button className="button secondary" disabled={busy} onClick={load}>Import history</button></div>
 {message&&<p role="status">{message}</p>}
 {preview&&<><p>{preview.accepted_count} valid records; {preview.errors.length} duplicate, conflicting or invalid rows.</p><ul>{preview.errors.slice(0,25).map((e:any)=><li key={e.row}>Row {e.row}: {e.status} — {e.message}</li>)}</ul></>}
 {history.map(batch=><p key={batch.batch_id}>Import {batch.batch_id} · {batch.created_at}</p>)}
 </details></section>
}
