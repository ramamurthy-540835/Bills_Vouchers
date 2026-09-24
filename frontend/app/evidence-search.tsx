'use client'
import {FormEvent,useRef,useState} from 'react'

export default function EvidenceSearch({period,scenario,onSelect,money}:{period:string;scenario?:string;onSelect?:(doc:any)=>void;money:(value:unknown)=>string}){
 const [q,setQ]=useState(''),[status,setStatus]=useState(''),[minimum,setMinimum]=useState(''),[maximum,setMaximum]=useState(''),[data,setData]=useState<any>(null),[busy,setBusy]=useState(false),[error,setError]=useState('')
 const sequence=useRef(0)
 async function search(offset=0){const id=++sequence.current;setBusy(true);setError('');try{
  const query=new URLSearchParams({period,q,status,minimum,maximum,offset:String(offset),limit:'20',...(scenario?{scenario}:{})})
  const response=await fetch(`/api/${scenario?'demo':'pipeline'}/search?${query}`);const result=await response.json();if(!response.ok)throw Error(result.error?.message||result.detail||'Search failed.')
  if(sequence.current===id)setData(result)
 }catch(e){if(sequence.current===id)setError(e instanceof Error?e.message:'Search failed.')}finally{if(sequence.current===id)setBusy(false)}}
 function submit(e:FormEvent){e.preventDefault();search()}
 return <section className="bv-card"><h2>Search documents</h2><p className="muted">Find suppliers, invoice numbers, dates and filenames. Filter by review status or invoice total.</p><form className="evidence-filters" onSubmit={submit}>
 <label>Search text<input aria-label="Search documents" value={q} onChange={e=>setQ(e.target.value)} maxLength={250} placeholder="Supplier, invoice or keyword"/></label>
 <label>Status<select value={status} onChange={e=>setStatus(e.target.value)}><option value="">All statuses</option><option value="validated">Validated</option><option value="needs_review">Needs review</option><option value="failed">Failed</option></select></label>
 <label>Minimum ₹<input inputMode="decimal" value={minimum} onChange={e=>setMinimum(e.target.value)}/></label><label>Maximum ₹<input inputMode="decimal" value={maximum} onChange={e=>setMaximum(e.target.value)}/></label><button className="button primary" disabled={busy}>{busy?'Searching…':'Search'}</button></form>
 {error&&<p role="alert" className="notice">{error}</p>}{!data?<p className="empty-state">Enter a search or choose filters to explore this period.</p>:<><p role="status" className="muted">{data.total} results · {data.searched_count} documents searched{data.scope?` · ${data.scope}`:''}</p>{!data.results.length?<p className="empty-state">No matching documents. Try a different keyword or amount range.</p>:<div className="table-scroll"><table><thead><tr><th>Invoice</th><th>Supplier</th><th>Total</th><th>Status</th><th/></tr></thead><tbody>{data.results.map((doc:any)=><tr key={doc.doc_id}><td>{doc.silver?.invoice_no||doc.original_filename}</td><td>{doc.silver?.supplier_name||'Not extracted'}</td><td className="money">{money(doc.silver?.total)}</td><td>{doc.silver?.validation_status?.replaceAll('_',' ')||'Queued'}</td><td>{onSelect?<button className="button quiet" onClick={()=>onSelect(doc)}>View</button>:<a href={`/documents/${doc.doc_id}?period=${period}`}>Review →</a>}</td></tr>)}</tbody></table></div>}<div className="pagination"><button disabled={busy||data.offset===0} onClick={()=>search(Math.max(0,data.offset-20))}>Previous</button><span>Page {Math.floor(data.offset/20)+1}</span><button disabled={busy||data.offset+20>=data.total} onClick={()=>search(data.offset+20)}>Next</button></div></>}
 </section>
}
