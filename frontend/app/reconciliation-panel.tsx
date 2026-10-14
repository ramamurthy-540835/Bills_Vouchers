'use client'
import {useEffect, useState} from 'react'
import Link from 'next/link'
import ReconciliationReview from './reconciliation-review'

const labels:Record<string,string> = {exact:'Exact match',within_tolerance:'Within ₹1 per-head tolerance',amount_mismatch:'Amount mismatch',date_mismatch:'Date mismatch — review required',ambiguous:'Ambiguous — duplicate candidates',missing_statement:'Missing from statement',missing_book:'Missing from confirmed purchases',incomplete_identity:'Incomplete identity',incomplete_amounts:'Incomplete amounts',unsupported_document:'Document type not supported by B2B matching'}
const heads = ['taxable_value','cgst','sgst','igst','cess']

export default function ReconciliationPanel({period,refreshKey,onReviewSaved}:{period:string;refreshKey:unknown;onReviewSaved?:()=>void}) {
 const [message,setMessage]=useState('')
 const [data,setData]=useState<any>(null),[error,setError]=useState(''),[filter,setFilter]=useState('exceptions'),[retry,setRetry]=useState(0)
 useEffect(()=>{
  const controller=new AbortController();setData(null);setError('')
  fetch(`/api/gst/bills/reconciliation?period=${encodeURIComponent(period)}`,{signal:controller.signal,cache:'no-store'})
   .then(async response=>{if(!response.ok)throw Error('Could not load reconciliation evidence.');return response.json()})
   .then(setData).catch(e=>{if(e.name!=='AbortError')setError(e.message)})
  return ()=>controller.abort()
 },[period,refreshKey,retry])
 const rows=(data?.cases||[]).filter((row:any)=>filter==='all'||(filter==='exceptions'?row.status!=='exact':row.status===filter))
 return <section className="bv-card" style={{minWidth:0,maxWidth:'100%'}} aria-labelledby="reconciliation-evidence-title">
  <h2 id="reconciliation-evidence-title">Reconciliation evidence</h2>{message&&<p role="status">{message}</p>}
  <p>Compare confirmed purchases against the imported B2B statement. Date-only candidates and duplicate candidates require investigation. This comparison does not approve or change ITC.</p>
  {error?<div role="alert">{error} <button className="button secondary" onClick={()=>setRetry(value=>value+1)}>Retry reconciliation</button></div>:!data?<p role="status">Loading reconciliation evidence…</p>:<>
   <p>{data.confirmed_purchase_count} confirmed purchases · {data.statement_count} statement records</p>
   <label>Show reconciliation cases <select style={{display:'block',width:'100%',maxWidth:'100%'}} value={filter} onChange={e=>setFilter(e.target.value)}><option value="exceptions">Exceptions and rounding differences</option><option value="all">All records</option>{Object.entries(labels).map(([key,label])=><option key={key} value={key}>{label} ({data.counts[key]||0})</option>)}</select></label>
   {!rows.length?<p>No cases for this filter. {data.statement_count===0?'No statement records are available for this period.':''}</p>:<div className="table-scroll"><table><thead><tr><th>Supplier GSTIN</th><th>Invoice</th><th>Date</th><th>Comparison</th><th>Evidence and differences</th></tr></thead><tbody>{rows.map((row:any)=><tr key={row.id}>
    <td>{row.supplier_gstin||'Missing'}</td><td>{row.invoice_id?<Link href={`/bills?period=${encodeURIComponent(period)}&invoice=${encodeURIComponent(row.invoice_id)}`}>{row.invoice_number||'Missing invoice number'}</Link>:row.invoice_number}</td><td>{row.invoice_date||'Missing'}</td><td>{labels[row.status]||row.status}</td>
    <td><details><summary>Compare evidence for {row.invoice_number||'unnamed invoice'}</summary><p>Differences are books minus statement, in rupees. Missing amounts remain blank.</p><table><thead><tr><th>Amount</th><th>Books</th><th>Statement</th><th>Difference</th></tr></thead><tbody>{heads.map(head=><tr key={head}><th>{head.replace('_',' ').toUpperCase()}</th><td>{row.book_amounts?.[head]??'—'}</td><td>{row.statement_amounts?.[head]??'—'}</td><td>{row.differences?.[head]??'—'}</td></tr>)}</tbody></table>
    {row.statement_candidates.map((candidate:any)=><div key={candidate.position}><p>Statement row {candidate.position+1}: {candidate.invoice_number}, {candidate.invoice_date||'date missing'}. ITC marked available: {candidate.itc_available===true?'Yes':'No or not supplied'}.</p><p>{heads.map(head=>`${head.toUpperCase()}: ${candidate.amounts[head]??'missing'}`).join(' · ')}</p>{/^[a-f0-9]{64}$/.test(candidate.source_sha256||'')?<Link href={`/api/gst/bills/gstr2b/${candidate.source_sha256}/original?period=${encodeURIComponent(period)}`}>Download source statement</Link>:<p>Original statement provenance unavailable.</p>}</div>)}
    <ReconciliationReview key={`${row.id}:${data.source_hash}:${row.review?.version||0}`} row={row} period={period} sourceHash={data.source_hash} canReview={Boolean(data.can_review)} onSaved={()=>{setMessage('Review recorded. Financial calculations are unchanged.');setRetry(value=>value+1);onReviewSaved?.()}}/></details></td></tr>)}</tbody></table></div>}
  </>}
 </section>
}
