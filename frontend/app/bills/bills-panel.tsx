'use client'
import {useCallback,useEffect,useState} from 'react'
import Link from 'next/link'
import {FileUp} from 'lucide-react'
import {GST} from '../../lib/copy/gst'
import {money} from '../workspace'

async function api(path:string,method='GET',body?:any){
 const headers:Record<string,string>={}
 if(method!=='GET'){
  const csrf=await fetch('/api/auth/csrf');headers['x-csrf-token']=(await csrf.json()).token
  if(!(body instanceof FormData))headers['content-type']='application/json'
 }
 const response=await fetch(`/api/gst/bills${path}`,{method,headers,body:body instanceof FormData?body:body?JSON.stringify(body):undefined})
 if(!response.ok){const error=await response.json().catch(()=>({}));throw Error(error.error?.message||error.detail?.message||GST.failed)}
 return response.json()
}
export default function BillsPanel({data}:{data:any}){
 const [bills,setBills]=useState<any[]>([]),[selected,setSelected]=useState<any>(null),[jobs,setJobs]=useState<any[]>([]),[status,setStatus]=useState(''),[message,setMessage]=useState(''),[busy,setBusy]=useState(false),[loading,setLoading]=useState(true)
 const period=data.period,write=data.can_write
 const reload=useCallback(async()=>{const result=await api(`?period=${period}&status=${status}`);setBills(result.invoices);setLoading(false)},[period,status])
 useEffect(()=>{reload().catch(e=>{setMessage(e.message);setLoading(false)})},[reload])
 async function upload(files:FileList|File[]|null){
  if(!files?.length||busy)return
  if(files.length>20){setMessage(GST.maxFiles);return}
  setBusy(true);setMessage('');setJobs(Array.from(files).map(f=>({filename:f.name,status:'reading'})))
  try{const completed:any[]=[];for(const file of Array.from(files)){const body=new FormData();body.append('files',file);const result=await api(`/upload?period=${period}`,'POST',body);completed.push(...result.files);setJobs([...completed,...Array.from(files).slice(completed.length).map(f=>({filename:f.name,status:'reading'}))]);await reload()}}
  catch(e){setMessage(e instanceof Error?e.message:GST.failed);setJobs(Array.from(files).map(f=>({filename:f.name,status:'needs_attention'})))}finally{setBusy(false)}
 }
 async function open(id:string){try{setSelected(await api(`/${id}`));setMessage('')}catch(e){setMessage((e as Error).message)}}
 async function save(body:any){if(!selected||!write)return;setBusy(true);setMessage('');try{setSelected(await api(`/${selected.invoice_id}`,'PATCH',body));await reload();setMessage(GST.saved)}catch(e){setMessage((e as Error).message)}finally{setBusy(false)}}
 async function decision(action:string){setBusy(true);setMessage('');try{setSelected(await api(`/${selected.invoice_id}/${action}`,'POST'));await reload()}catch(e){setMessage((e as Error).message)}finally{setBusy(false)}}
 const labels=GST.fields
 const input=(field:string,value:any,onSave:(value:string)=>void,type='text')=><label key={field}>{labels[field]}<input aria-label={labels[field]} key={`${selected?.version}-${field}-${String(value)}`} defaultValue={value??''} type={type} disabled={!write||busy} onBlur={e=>{if(e.target.value!==String(value??''))onSave(e.target.value)}}/></label>
 return <>
  {message&&<p className="notice" role="status">{message}</p>}
  {!selected?<>
   {write?<section className="bill-drop bv-card" onDragOver={e=>e.preventDefault()} onDrop={e=>{e.preventDefault();upload(e.dataTransfer.files)}}><FileUp size={28}/><h2>{GST.drop}</h2><label className="button primary">{GST.upload}<input className="visually-hidden" aria-label={GST.upload} type="file" multiple accept=".pdf,.jpg,.jpeg,.png,.xlsx,.csv" disabled={busy} onChange={e=>{upload(e.target.files);e.target.value=''}}/></label><p><Link href="/api/gst/bills/template.xlsx">{GST.template}</Link></p><small>{GST.maxFiles}</small></section>:<p>{GST.readOnly}</p>}
   {!!jobs.length&&<ul className="upload-progress" aria-live="polite">{jobs.map((j,i)=><li key={i}><strong>{j.filename}</strong><span>{j.status==='reading'?GST.reading:j.status==='ready'?GST.ready:GST.attention}</span>{j.reason&&<p>{j.reason}</p>}{j.invoice_ids?.map((id:string)=><button className="button quiet" key={id} onClick={()=>open(id)}>{GST.review}</button>)}</li>)}</ul>}
   <section className="bv-card"><div className="section-heading"><label>{GST.filter}<select value={status} onChange={e=>setStatus(e.target.value)}><option value="">{GST.all}</option>{['extracted','needs_review','confirmed','rejected'].map(s=><option key={s} value={s}>{GST.status[s]}</option>)}</select></label><Link className="button secondary" href={`/api/gst/bills/export?period=${period}&format=xlsx`}>{GST.export}</Link></div>
   {loading?<div className="skeleton skeleton-table" aria-label={GST.loading}/>:!bills.length?<p className="empty-state">{GST.none}</p>:<div className="table-scroll bills-table"><table><thead><tr>{[GST.supplier,GST.invoiceNo,GST.date,GST.taxable,GST.tax,GST.total,GST.itc,GST.actions].map(h=><th key={h}>{h}</th>)}</tr></thead><tbody>{bills.map(b=><tr key={b.invoice_id} onClick={()=>open(b.invoice_id)}><td data-label={GST.supplier}>{b.supplier_legal_name||'—'}<small className="gstin-text">{b.supplier_gstin}</small></td><td data-label={GST.invoiceNo}>{b.invoice_number||'—'}</td><td data-label={GST.date}>{b.invoice_date?new Date(`${b.invoice_date}T12:00:00Z`).toLocaleDateString('en-IN'):'—'}</td><td data-label={GST.taxable} className="money">{money(b.totals.taxable_value)}</td><td data-label={GST.tax} className="money">{['cgst','sgst','igst','cess'].map(h=><small key={h}>{GST.fields[h]} {money(b.totals[h])}</small>)}</td><td data-label={GST.total} className="money">{money(b.totals.invoice_total)}</td><td data-label={GST.itc}><span className="chip">{GST.status[b.status]}</span><small>{GST.status[b.itc.eligibility]}</small></td><td><button className="button quiet" onClick={e=>{e.stopPropagation();open(b.invoice_id)}}>{GST.review}</button></td></tr>)}</tbody></table></div>}</section>
  </>:<>
   <div className="section-heading"><button className="button quiet" onClick={()=>setSelected(null)}>{GST.back}</button><span className="chip">{GST.status[selected.status]}</span></div>
   <div className="invoice-review"><section className="bv-card invoice-form"><h2>{GST.invoice}</h2><p className="muted">{GST.inputHint}</p><div className="account-form">{['supplier_gstin','supplier_legal_name','supplier_address','recipient_gstin','recipient_legal_name','recipient_address','invoice_number','invoice_date','place_of_supply_state_code'].map(f=>input(f,selected[f],v=>save({[f]:v}),f==='invoice_date'?'date':'text'))}
    <label>{GST.direction}<select disabled={!write||busy} value={selected.direction} onChange={e=>save({direction:e.target.value})}><option value="purchase">{GST.purchase}</option><option value="sale">{GST.sale}</option></select></label>
    <label>{GST.type}<select disabled={!write||busy} value={selected.invoice_type} onChange={e=>save({invoice_type:e.target.value})}>{[['tax_invoice',GST.taxInvoice],['bill_of_supply',GST.billOfSupply],['debit_note',GST.debitNote],['credit_note',GST.creditNote]].map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label>
    <label>{GST.reverseCharge}<input type="checkbox" checked={selected.reverse_charge} disabled={!write||busy} onChange={e=>save({reverse_charge:e.target.checked})}/></label>
   </div><h3>{GST.lineItems}</h3>{selected.line_items.map((line:any,index:number)=><fieldset key={`${selected.version}-${index}`}><legend>{index+1}</legend><div className="bill-line-fields">{Object.keys(line).map(f=>input(f,line[f],v=>save({line_items:selected.line_items.map((l:any,i:number)=>i===index?{...l,[f]:v}:l)})))}</div>{write&&<button className="button quiet" disabled={busy} onClick={()=>save({line_items:selected.line_items.filter((_:any,i:number)=>i!==index)})}>{GST.remove}</button>}</fieldset>)}
   {write&&<button className="button secondary" disabled={busy} onClick={()=>save({line_items:[...selected.line_items,{description:'',hsn_sac:'',quantity:'1',unit:'NOS',taxable_value:'0',gst_rate:'0',cgst:'0',sgst:'0',igst:'0',cess:'0'}]})}>{GST.addLine}</button>}
   <h3>{GST.total}</h3><div className="account-form">{Object.keys(selected.totals).map(f=>input(f,selected.totals[f],v=>save({totals:{...selected.totals,[f]:v}})))}</div>
   <ul className="review-reasons">{selected.review_reasons.map((r:string)=><li key={r}>{GST.reasons[r]||GST.attention}</li>)}</ul><p>{GST.confirmNote}</p><div className="filing-actions">{write&&<><button className="button primary" disabled={busy||selected.status==='confirmed'||selected.status==='rejected'} onClick={()=>decision('confirm')}>{GST.confirm}</button><button className="button quiet" disabled={busy||selected.status==='rejected'} onClick={()=>decision('reject')}>{GST.reject}</button></>}</div></section>
   <aside className="bv-card original-bill"><h2>{GST.original}</h2><Link href={`/api/gst/bills/${selected.invoice_id}/original`} target="_blank">{GST.originalDownload}</Link><iframe title={GST.original} src={`/api/gst/bills/${selected.invoice_id}/original`}/></aside></div>
  </>}
 </>
}
