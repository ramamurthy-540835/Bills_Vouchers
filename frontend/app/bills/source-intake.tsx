'use client'
import {useState} from 'react'
import Link from 'next/link'

export default function SourceIntake({api,period}:{api:(path:string,method?:string,body?:any)=>Promise<any>,period:string}){
 const [source,setSource]=useState('vendor'),[file,setFile]=useState<File|null>(null),[busy,setBusy]=useState(false)
 const [message,setMessage]=useState(''),[preview,setPreview]=useState<any>(null),[history,setHistory]=useState<any[]>([])
 const [columns,setColumns]=useState<string[]>([]),[fields,setFields]=useState<string[]>([]),[mapping,setMapping]=useState<Record<string,string>>({})
 const [detail,setDetail]=useState<any>(null),[analysis,setAnalysis]=useState<any>(null),[snapshots,setSnapshots]=useState<any[]>([])
 async function chooseFile(selected:File|null){
  setFile(selected);setPreview(null);setColumns([]);setMapping({});setMessage('')
  if(!selected)return
  setBusy(true)
  try{const body=new FormData();body.append('file',selected);const result=await api('/intake/columns','POST',body);setColumns(result.columns);setFields(result.supported_fields);setMapping(result.suggested_mapping)}
  catch(e){setMessage((e as Error).message)}finally{setBusy(false)}
 }
 async function submit(stage:boolean){
  if(!file)return
  setBusy(true);setMessage('')
  try{
   const data=new FormData();data.append('source',source);data.append('file',file);data.append('mapping',JSON.stringify(mapping))
   const result=await api('/intake/'+(stage?'batches':'preview'),'POST',data)
   if(stage){setMessage(`Import ${result.batch_id} ${result.replayed?'already exists':'staged'}. No financial invoices were created.`);setPreview(null);setHistory((await api('/intake/batches')).batches)}
   else setPreview(result)
  }catch(e){setMessage((e as Error).message)}finally{setBusy(false)}
 }
 async function load(){setBusy(true);setMessage('');try{setHistory((await api('/intake/batches')).batches)}catch(e){setMessage((e as Error).message)}finally{setBusy(false)}}
 async function open(batch:string){
  setBusy(true);setMessage('');setAnalysis(null);setDetail(null);setSnapshots([])
  try{setDetail(await api(`/intake/batches/${encodeURIComponent(batch)}`));setSnapshots((await api(`/intake/batches/${encodeURIComponent(batch)}/reconciliations?period=${period}`)).snapshots)}
  catch(e){setMessage((e as Error).message)}finally{setBusy(false)}
 }
 async function reconcile(){
  if(!detail)return
  setBusy(true);setMessage('')
  try{const result=await api(`/intake/batches/${encodeURIComponent(detail.batch_id)}/reconcile?period=${period}`,'POST',{});setAnalysis(result);setSnapshots((await api(`/intake/batches/${encodeURIComponent(detail.batch_id)}/reconciliations?period=${period}`)).snapshots)}
  catch(e){setMessage((e as Error).message)}finally{setBusy(false)}
 }
 const unmapped=columns.filter(column=>!mapping[column])
 return <section className="bv-card"><details><summary>Bulk source intake</summary>
 <p>Import Vendor, Customer or Driver records and compare them with existing invoices. Trips, payments and settlements never create taxable invoices automatically.</p>
 <p>CSV, XLSX or JSON; maximum 10 MB and 10,000 records. Required fields: source_record_id and event_type. Source version defaults to 1.</p>
 <div className="account-form"><label>Source system<select aria-label="Source system" disabled={busy} value={source} onChange={e=>{setSource(e.target.value);setPreview(null)}}><option value="vendor">Vendor App</option><option value="customer">Customer App</option><option value="driver">Driver App</option></select></label><label>Source file<input type="file" accept=".csv,.xlsx,.json" disabled={busy} onChange={e=>void chooseFile(e.target.files?.[0]||null)}/></label></div>
 {columns.length>0&&<details><summary>Map source columns ({unmapped.length} ignored)</summary>
 <p>Review each mapping before previewing. Ignored columns are excluded. Monetary values must use decimal text in JSON.</p>
 <div className="account-form">{columns.map(column=><label key={column}>{column}<select aria-label={`Map ${column}`} value={mapping[column]||''} disabled={busy} onChange={e=>{const next={...mapping};if(e.target.value)next[column]=e.target.value;else delete next[column];setMapping(next);setPreview(null)}}>
 <option value="">Ignore this column</option>{fields.map(field=><option key={field} value={field}>{field}</option>)}</select></label>)}</div></details>}
 <div className="filing-actions"><button className="button secondary" disabled={busy||!file||!Object.keys(mapping).length} onClick={()=>submit(false)}>Preview import</button><button className="button primary" disabled={busy||!preview} onClick={()=>submit(true)}>Stage source records</button><button className="button secondary" disabled={busy} onClick={load}>Import history</button></div>
 {busy&&<p role="status">Processing source records…</p>}
 {message&&<p role="status">{message}</p>}
 {preview&&<><p>{preview.accepted_count} valid records; {preview.errors.length} duplicate, conflicting or invalid rows.</p><ul>{preview.errors.slice(0,25).map((e:any)=><li key={e.row}>Row {e.row}: {e.status} — {e.message}</li>)}</ul>
 <details><summary>Preview mapped records (first 25)</summary>{preview.accepted.map((row:any)=><p key={`${row.source_record_id}-${row.source_version}`}>{row.source_record_id} · {row.event_type} · {row.invoice_number||'No invoice number'} · {row.invoice_total||'Amount not provided'}</p>)}</details></>}
 {history.map(batch=><div className="filing-actions" key={batch.batch_id}><span>Import {batch.batch_id} · {batch.created_at}</span><button className="button secondary" disabled={busy} onClick={()=>open(batch.batch_id)}>View import</button></div>)}
 {detail&&<section aria-label="Source import details"><h3>Import review</h3><p>{detail.records.length} staged records. Reconcile against invoices for {period}; missing invoices still require the existing bill-upload and review workflow.</p>
 <div className="filing-actions"><button className="button primary" disabled={busy} onClick={reconcile}>Reconcile with invoices</button><a className="button secondary" href={`/api/gst/bills/intake/batches/${encodeURIComponent(detail.batch_id)}/original`}>Download original source</a><button className="button secondary" disabled={busy} onClick={()=>{setDetail(null);setAnalysis(null);setSnapshots([])}}>Close import</button></div>
 <details><summary>Staged records</summary>{detail.records.slice(0,100).map((row:any,index:number)=><p key={index}>{row.source_system} · {row.source_record_id} · version {row.source_version} · {row.status}</p>)}{detail.records.length>100&&<p>Showing the first 100 records.</p>}</details>
 {snapshots.length>0&&<details><summary>Reconciliation history</summary>{snapshots.map(snapshot=><div className="filing-actions" key={snapshot.run_id}><span>{snapshot.created_at}</span><button className="button secondary" disabled={busy} onClick={()=>setAnalysis(snapshot.payload)}>View saved reconciliation</button></div>)}</details>}
 </section>}
 {analysis&&<section aria-label="Source reconciliation results"><h3>Reconciliation results</h3><p>Observed {analysis.observed_at}. This saved snapshot may become stale; rerun reconciliation after changes. No financial records were created or changed.</p>
 <dl>{Object.entries(analysis.counts).map(([status,count])=><div key={status}><dt>{status.replaceAll('_',' ')}</dt><dd>{String(count)}</dd></div>)}</dl>
 <ul>{analysis.records.slice(0,100).map((row:any,index:number)=><li key={index}><strong>{row.source_record_id}</strong> — {row.status.replaceAll('_',' ')}. {row.message} {row.href&&<Link href={row.href}>Review invoice</Link>}
 {row.differences&&<ul>{Object.entries(row.differences).map(([field,value])=><li key={field}>{field}: {String(value)}</li>)}</ul>}</li>)}</ul>
 {analysis.records.length>100&&<p>Showing the first 100 results; summary counts include all records.</p>}</section>}
 </details></section>
}
