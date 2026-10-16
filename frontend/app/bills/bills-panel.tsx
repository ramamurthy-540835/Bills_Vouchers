'use client'
import {useCallback,useEffect,useState,useRef} from 'react'
import Link from 'next/link'
import {FileUp} from 'lucide-react'
import {GST} from '../../lib/copy/gst'
import {money} from '../workspace'

async function api(path:string,method='GET',body?:any,version?:number){
 const headers:Record<string,string>={}
 if(version!==undefined)headers['if-match']=String(version)
 if(method!=='GET'){
  const csrf=await fetch('/api/auth/csrf');headers['x-csrf-token']=(await csrf.json()).token
  if(!(body instanceof FormData))headers['content-type']='application/json'
 }
 const response=await fetch(`/api/gst/bills${path}`,{method,headers,body:body instanceof FormData?body:body?JSON.stringify(body):undefined})
 if(!response.ok){const error=await response.json().catch(()=>({}));throw Error(error.error?.message||error.detail?.message||(typeof error.detail==='string'?error.detail:GST.failed))}
 return response.json()
}
export default function BillsPanel({data}:{data:any}){
 const [bills,setBills]=useState<any[]>([]),[selected,setSelected]=useState<any>(null),[jobs,setJobs]=useState<any[]>([]),[status,setStatus]=useState(''),[message,setMessage]=useState(''),[busy,setBusy]=useState(false),[loading,setLoading]=useState(true)
 const [dirty,setDirty]=useState(false),[opening,setOpening]=useState(false),[rejectionReason,setRejectionReason]=useState('')
 const [history,setHistory]=useState<any[]>([]),[deleted,setDeleted]=useState<any[]>([])
 const dialog=useRef<HTMLDialogElement>(null),openSequence=useRef(0)
 useEffect(()=>{if(selected&&!dialog.current?.open)dialog.current?.showModal()},[selected])
 function close(){if(busy)return;if(dirty&&!window.confirm('Discard unsaved bill changes?'))return;setSelected(null);setDirty(false)}
 const [historyView,setHistoryView]=useState<'uploads'|'deleted'|null>(null),[historyLoading,setHistoryLoading]=useState(false),[historyError,setHistoryError]=useState('')
 const period=data.period,write=data.can_write
 const jobKey=`gst-bill-job:${data.client_id}:${period}`
 const reload=useCallback(async()=>{const result=await api(`?period=${period}&status=${status}`);setBills(result.invoices);setLoading(false)},[period,status])
 useEffect(()=>{reload().catch(e=>{setMessage(e.message);setLoading(false)})},[reload])
 useEffect(()=>{const id=new URLSearchParams(window.location.search).get('invoice');if(id)open(id)},[period,data.client_id])
 useEffect(()=>{setRejectionReason('')},[selected?.invoice_id])
 async function loadHistory(view?:'uploads'|'deleted'){if(view)setHistoryView(view);setHistoryLoading(true);setHistoryError('');try{setHistory((await api(`/history?period=${period}`)).jobs);if(write)setDeleted((await api(`/deleted?period=${period}`)).invoices)}catch(e){setHistoryError((e as Error).message)}finally{setHistoryLoading(false)}}
 async function retryUpload(id:string){setBusy(true);try{let job=await api(`/upload/${id}/retry`,'POST');sessionStorage.setItem(jobKey,id);while(!['completed','needs_attention'].includes(job.status)&&!job.retryable){setJobs(job.files);await new Promise(resolve=>setTimeout(resolve,1500));job=await api(`/upload/${id}`)}sessionStorage.removeItem(jobKey);if(job.retryable)setMessage('Processing needs attention. Open upload history to retry the saved upload.');setJobs(job.files);await reload();await loadHistory()}catch(e){setMessage((e as Error).message)}finally{setBusy(false)}}
 async function restore(invoice:any){if(!window.confirm('Restore this bill for review? It will require confirmation again.'))return;setBusy(true);try{await api(`/${invoice.invoice_id}/restore`,'POST',undefined,invoice.version);await reload();await loadHistory();setMessage('Bill restored for review.')}catch(e){setMessage((e as Error).message)}finally{setBusy(false)}}
 useEffect(()=>{let active=true;const id=sessionStorage.getItem(jobKey);if(id){setBusy(true);(async()=>{try{while(active){const job=await api(`/upload/${id}`);if(!active)return;setJobs(job.files);await reload();if(job.status==='completed'||job.status==='needs_attention'||job.retryable){sessionStorage.removeItem(jobKey);if(job.retryable)setMessage('Processing needs attention. Open upload history to retry the saved upload.');break}await new Promise(resolve=>setTimeout(resolve,1500))}}catch(e){if(active)setMessage((e as Error).message)}finally{if(active)setBusy(false)}})()}return()=>{active=false}},[jobKey])
 async function upload(files:FileList|File[]|null){
  if(!files?.length||busy)return
  const chosen=Array.from(files)
  if(chosen.length>20||chosen.some(f=>f.size>15*1024*1024)){setMessage(GST.maxFiles);return}
  setBusy(true);setMessage('');setJobs(chosen.map(f=>({filename:f.name,status:'reading'})))
  const completed:any[]=[]
  try{for(const file of chosen){
   const body=new FormData();body.append('files',file)
   let job=await api(`/upload?period=${period}`,'POST',body)
   sessionStorage.setItem(jobKey,job.job_id)
   while(job.status!=='completed'&&job.status!=='needs_attention'&&!job.retryable){
    setJobs([...completed,...job.files,...chosen.slice(completed.length+1).map(f=>({filename:f.name,status:'reading'}))])
    await new Promise(resolve=>setTimeout(resolve,1500));job=await api(`/upload/${job.job_id}`)
   }
   sessionStorage.removeItem(jobKey);completed.push(...job.files)
   setJobs([...completed,...chosen.slice(completed.length).map(f=>({filename:f.name,status:'reading'}))]);await reload()
  }}catch(e){setMessage(e instanceof Error?e.message:GST.failed);setJobs([...completed,...chosen.slice(completed.length).map(f=>({filename:f.name,status:'needs_attention'}))])}finally{setBusy(false)}
 }
 async function open(id:string){if(busy)return;const sequence=++openSequence.current;setOpening(true);try{const result=await api(`/${id}`);if(sequence===openSequence.current){setSelected(result);setDirty(false);setMessage('')}}catch(e){setMessage((e as Error).message)}finally{if(sequence===openSequence.current)setOpening(false)}}
 function save(body:any){if(!write||busy)return;setSelected((current:any)=>({...current,...body}));setDirty(true)}
 async function persist(){
  if(!dirty)return selected
  const fields=['supplier_gstin','supplier_legal_name','supplier_address','recipient_gstin','recipient_legal_name','recipient_address','invoice_number','invoice_date','place_of_supply_state_code','direction','invoice_type','reverse_charge','line_items','totals']
  if(['admin','tax_admin'].includes(data.user?.role))fields.push('reverse_charge_paid_reference')
  const body=Object.fromEntries(fields.map(key=>[key,key==='invoice_date'?(selected[key]||null):selected[key]]))
  const result=await api(`/${selected.invoice_id}`,'PATCH',body,selected.version);setSelected(result);setDirty(false);return result
 }
 async function saveChanges(){setBusy(true);setMessage('');try{await persist();await reload();setMessage(GST.saved)}catch(e){setMessage((e as Error).message)}finally{setBusy(false)}}
 async function sumLines(){setBusy(true);setMessage('');try{const totals=await api('/sum-lines','POST',{line_items:selected.line_items});setSelected((current:any)=>({...current,totals}));setDirty(true);setMessage('Line amounts summed. Check against the original invoice before saving.')}catch(e){setMessage((e as Error).message)}finally{setBusy(false)}}
 async function decision(action:string){if(action==='reject'&&rejectionReason.trim().length<3){setMessage('Enter a rejection reason between 3 and 1000 characters.');return}setBusy(true);setMessage('');try{const current=await persist();setSelected(await api(`/${current.invoice_id}/${action}`,'POST',action==='reject'?{reason:rejectionReason}:undefined,current.version));setRejectionReason('');await reload()}catch(e){setMessage((e as Error).message)}finally{setBusy(false)}}
 async function remove(){if(!window.confirm('Delete this bill from your workspace?'))return;setBusy(true);setMessage('');try{await api(`/${selected.invoice_id}`,'DELETE',undefined,selected.version);setJobs(current=>current.map(job=>({...job,invoice_ids:job.invoice_ids?.filter((id:string)=>id!==selected.invoice_id)})));setSelected(null);setDirty(false);await reload();setMessage('Bill deleted.')}catch(e){setMessage((e as Error).message)}finally{setBusy(false)}}
 const labels=GST.fields
 const input=(field:string,value:any,onSave:(value:string)=>void,type='text')=><label key={field}>{labels[field]}<input aria-label={labels[field]} value={value??''} type={type} disabled={!write||busy} onChange={e=>onSave(e.target.value)}/></label>
 return <>
  {!selected&&message&&<p className="notice" role="status">{message}</p>}
  {opening&&<p role="status">Opening bill...</p>}
  <section className="bv-card bill-history-card" aria-label="Upload history and deleted bills"><div className="bill-support-header"><div><h2>Upload History &amp; Deleted Bills</h2><p>Track previous uploads, processing results and deleted invoice records.</p></div><div className="bill-history-actions"><button className="button secondary" disabled={busy||historyLoading} aria-expanded={historyView==='uploads'} onClick={()=>loadHistory('uploads')}>View Upload History</button>{write&&<button className="button secondary" disabled={busy||historyLoading} aria-expanded={historyView==='deleted'} onClick={()=>loadHistory('deleted')}>View Deleted Bills</button>}</div></div>
   {historyLoading&&<p role="status">Loading history...</p>}{historyError&&<p role="alert">{historyError}</p>}
   {!historyLoading&&!historyError&&historyView==='uploads'&&history.length===0&&<p>No upload jobs for this period.</p>}
   {!historyLoading&&!historyError&&historyView==='deleted'&&deleted.length===0&&<p>No deleted bills for this period.</p>}
   {!historyLoading&&!historyError&&historyView==='uploads'&&history.map(job=><div key={job.job_id}><p>Upload: {job.status}</p>{job.reason&&<p>{job.reason}</p>}{job.retryable&&job.status!=='needs_attention'&&<p>Processing has been inactive for at least 35 minutes. You can safely retry the saved upload.</p>}{write&&(job.retryable||job.status==='needs_attention')&&<button className="button secondary" disabled={busy} onClick={()=>retryUpload(job.job_id)}>Retry saved upload</button>}<ul>{job.files.map((file:any,index:number)=><li key={index}>{file.filename} — {file.status}{file.reason&&<p>{file.reason}</p>}</li>)}</ul></div>)}
   {!historyLoading&&!historyError&&historyView==='deleted'&&deleted.map(invoice=><p key={invoice.invoice_id}>{invoice.filename} <button className="button secondary" disabled={busy} onClick={()=>restore(invoice)}>Restore for review</button></p>)}
  </section>
  <>
   {write?<section className="bill-drop bv-card" onDragOver={e=>e.preventDefault()} onDrop={e=>{e.preventDefault();upload(e.dataTransfer.files)}}><FileUp size={28}/><h2>{GST.drop}</h2><label className="button primary">{GST.upload}<input className="visually-hidden" aria-label={GST.upload} type="file" multiple accept=".pdf,.jpg,.jpeg,.png,.xlsx,.csv" disabled={busy} onChange={e=>{upload(e.target.files);e.target.value=''}}/></label><p><Link href="/api/gst/bills/template.xlsx">{GST.template}</Link></p><small>{GST.maxFiles}</small></section>:<p>{GST.readOnly}</p>}
   {!!jobs.length&&<ul className="upload-progress" aria-live="polite">{jobs.map((j,i)=><li key={i}><strong>{j.filename}</strong><span>{j.status==='reading'?GST.reading:j.status==='ready'?GST.ready:GST.attention}</span>{j.reason&&<p>{j.reason}</p>}{j.invoice_ids?.map((id:string)=><button className="button quiet" key={id} onClick={()=>open(id)}>{GST.review}</button>)}</li>)}</ul>}
   <section className="bv-card bill-register-card"><div className="bill-management-toolbar"><label htmlFor="bill-status">{GST.filter}</label><select id="bill-status" aria-label={GST.filter} value={status} onChange={e=>setStatus(e.target.value)}><option value="">{GST.all}</option>{['extracted','needs_review','confirmed','rejected'].map(s=><option key={s} value={s}>{GST.status[s]}</option>)}</select><Link className="button secondary" href={`/api/gst/bills/export?period=${period}&format=xlsx`}>{GST.export}</Link></div>
   {loading?<div className="skeleton skeleton-table" aria-label={GST.loading}/>:!bills.length?<p className="empty-state">{GST.none}</p>:<div className="table-scroll bills-table"><table><thead><tr>{[GST.supplier,GST.invoiceNo,GST.date,GST.taxable,GST.tax,GST.total,GST.itc,GST.actions].map(h=><th key={h}>{h}</th>)}</tr></thead><tbody>{bills.map(b=><tr key={b.invoice_id} onClick={()=>open(b.invoice_id)}><td data-label={GST.supplier}>{b.supplier_legal_name||'—'}<small className="gstin-text">{b.supplier_gstin}</small></td><td data-label={GST.invoiceNo}><small>{b.filename}</small><span>{b.invoice_number||'—'}</span></td><td data-label={GST.date}>{b.invoice_date?new Date(`${b.invoice_date}T12:00:00Z`).toLocaleDateString('en-IN'):'—'}</td><td data-label={GST.taxable} className="money">{money(b.totals.taxable_value)}</td><td data-label={GST.tax} className="money">{['cgst','sgst','igst','cess'].map(h=><small key={h}>{GST.fields[h]} {money(b.totals[h])}</small>)}</td><td data-label={GST.total} className="money">{money(b.totals.invoice_total)}</td><td data-label={GST.itc}><span className="chip">{GST.status[b.status]}</span><small>{GST.status[b.itc.eligibility]}</small></td><td><button className="button quiet" onClick={e=>{e.stopPropagation();open(b.invoice_id)}}>{GST.review}</button></td></tr>)}</tbody></table></div>}</section>
  </>
  {selected&&<dialog ref={dialog} className="bill-review-drawer" aria-labelledby="bill-review-title" onCancel={event=>{event.preventDefault();close()}}>
   {message&&<p className="notice" role="status">{message}</p>}
   <div className="section-heading"><button className="button quiet" disabled={busy} onClick={close}>{GST.back}</button><span className="chip">{GST.status[selected.status]}</span></div>
   <div className="invoice-review"><section className="bv-card invoice-form"><h2 id="bill-review-title">{GST.invoice}: {selected.invoice_number||'New bill'}</h2><p className="muted">{GST.inputHint}</p><div className="account-form">{['supplier_gstin','supplier_legal_name','supplier_address','recipient_gstin','recipient_legal_name','recipient_address','invoice_number','invoice_date','place_of_supply_state_code'].map(f=>input(f,selected[f],v=>save({[f]:v}),f==='invoice_date'?'date':'text'))}
    <label>{GST.direction}<select disabled={!write||busy} value={selected.direction} onChange={e=>save({direction:e.target.value})}><option value="purchase">{GST.purchase}</option><option value="sale">{GST.sale}</option></select></label>
    <label>{GST.type}<select disabled={!write||busy} value={selected.invoice_type} onChange={e=>save({invoice_type:e.target.value})}>{[['tax_invoice',GST.taxInvoice],['bill_of_supply',GST.billOfSupply],['debit_note',GST.debitNote],['credit_note',GST.creditNote]].map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label>
    <label>{GST.reverseCharge}<input type="checkbox" checked={selected.reverse_charge} disabled={!write||busy} onChange={e=>save({reverse_charge:e.target.checked})}/></label>
   {selected.reverse_charge&&['admin','tax_admin'].includes(data.user?.role)&&<label>{GST.paymentReference}<input value={selected.reverse_charge_paid_reference} disabled={busy} onChange={e=>save({reverse_charge_paid_reference:e.target.value})}/></label>}</div><h3>{GST.lineItems}</h3>{selected.line_items.map((line:any,index:number)=><fieldset key={index}><legend>{index+1}</legend><div className="bill-line-fields">{Object.keys(line).map(f=>input(f,line[f],v=>save({line_items:selected.line_items.map((l:any,i:number)=>i===index?{...l,[f]:v}:l)})))}</div>{write&&<button className="button quiet" disabled={busy} onClick={()=>save({line_items:selected.line_items.filter((_:any,i:number)=>i!==index)})}>{GST.remove}</button>}</fieldset>)}
   {write&&<button className="button secondary" disabled={busy} onClick={()=>save({line_items:[...selected.line_items,{description:'',hsn_sac:'',quantity:'1',unit:'NOS',taxable_value:'0',gst_rate:'0',cgst:'0',sgst:'0',igst:'0',cess:'0'}]})}>{GST.addLine}</button>}
   <h3>{GST.total}</h3>{write&&<button className="button secondary" disabled={busy||!selected.line_items.length} onClick={sumLines}>Sum line totals</button>}<div className="account-form">{Object.keys(selected.totals).map(f=>input(f,selected.totals[f],v=>save({totals:{...selected.totals,[f]:v}})))}</div>
   {selected.rejection_reason&&<p>Recorded rejection reason: {selected.rejection_reason}</p>}
   {write&&selected.status!=='rejected'&&<label>Rejection reason<textarea value={rejectionReason} maxLength={1000} disabled={busy} onChange={event=>setRejectionReason(event.target.value)}/></label>}
   <ul className="review-reasons">{selected.review_reasons.map((r:string)=><li key={r}>{GST.reasons[r]||GST.attention}</li>)}</ul><p>{GST.confirmNote}</p><div className="filing-actions">{write&&<><button className="button secondary" disabled={busy||!dirty} onClick={saveChanges}>Save changes</button><button className="button quiet" disabled={busy} onClick={remove}>Delete bill</button><button className="button primary" disabled={busy||(!dirty&&(selected.status==='confirmed'||selected.status==='rejected'))} onClick={()=>decision('confirm')}>{GST.confirm}</button><button className="button quiet" disabled={busy||selected.status==='rejected'} onClick={()=>decision('reject')}>{GST.reject}</button></>}</div></section>
   <aside className="bv-card original-bill"><h2>{GST.original}</h2><Link href={`/api/gst/bills/${selected.invoice_id}/original`} target="_blank">{GST.originalDownload}</Link>{/\.(pdf|png|jpe?g)$/i.test(selected.extraction.raw_ref)?<iframe title={GST.original} src={`/api/gst/bills/${selected.invoice_id}/original`}/>:<p>{GST.spreadsheetOriginal}</p>}</aside></div>
  </dialog>}
 </>
}
