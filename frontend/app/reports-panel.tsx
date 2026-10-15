'use client'
import {useEffect,useState} from 'react'
import Link from 'next/link'

const kinds:Record<string,string>={purchases:'Purchase register',sales:'Sales register',invoices:'Invoice listing',tax:'Tax-head summary',itc:'ITC decisions',reconciliation:'GSTR-2B reconciliation',audit:'Audit history'}

export default function ReportsPanel({period}:{period:string}){
 const [kind,setKind]=useState('purchases'),[scope,setScope]=useState('month'),[offset,setOffset]=useState(0)
 const [report,setReport]=useState<any>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[retry,setRetry]=useState(0),[notice,setNotice]=useState('')
 useEffect(()=>{
  const query=new URLSearchParams(window.location.search)
  const initialKind=query.get('kind'),initialScope=query.get('range')
  if(initialKind&&kinds[initialKind])setKind(initialKind)
  if(initialScope&&['month','quarter','financial_year'].includes(initialScope))setScope(initialScope)
 },[])
 useEffect(()=>{
  const controller=new AbortController();setReport(null);setError('');setNotice('')
  const query=new URLSearchParams({period,kind,scope_name:scope,offset:String(offset)})
  fetch(`/api/gst/bills/reports?${query}`,{cache:'no-store',signal:controller.signal})
   .then(async response=>{const value=await response.json();if(!response.ok)throw Error(value.error?.message||value.detail||'Could not load this report.');return value})
   .then(setReport).catch(e=>{if(e.name!=='AbortError')setError(e.message)})
  const url=new URL(window.location.href);url.searchParams.set('kind',kind);url.searchParams.set('range',scope);window.history.replaceState(null,'',url)
  return ()=>controller.abort()
 },[period,kind,scope,offset,retry])
 async function download(format:string){setBusy(true);setError('');setNotice('');try{
  const query=new URLSearchParams({period,kind,scope_name:scope,format})
  const response=await fetch(`/api/gst/bills/reports?${query}`,{cache:'no-store'})
  if(!response.ok){const value=await response.json();throw Error(value.error?.message||value.detail||'Export failed.')}
  const url=URL.createObjectURL(await response.blob()),a=document.createElement('a')
  a.href=url;a.download=`GST-Easy-${kind}-${period}-${scope}.${format}`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)
  setNotice('Report downloaded. It was regenerated from the current authorized evidence.')
 }catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 return <section className="bv-card" aria-label="Business reports" style={{minWidth:0,maxWidth:'100%'}}>
  <p>Review your canonical bills and their supporting evidence. These working reports are not GST filing exports.</p>
  <div className="filing-actions" style={{minWidth:0}}>
   <label style={{minWidth:0,maxWidth:'100%'}}>Report<select aria-label="Report" style={{maxWidth:'100%'}} value={kind} disabled={busy} onChange={e=>{setKind(e.target.value);setOffset(0)}}>{Object.entries(kinds).map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label>
   <label style={{minWidth:0,maxWidth:'100%'}}>Reporting period<select aria-label="Reporting period" style={{maxWidth:'100%'}} value={scope} disabled={busy} onChange={e=>{setScope(e.target.value);setOffset(0)}}><option value="month">Selected month</option><option value="quarter">Quarter containing selected month</option><option value="financial_year">Financial year containing selected month</option></select></label>
  </div>
  {error&&<div role="alert"><p>{error}</p><button className="button secondary" onClick={()=>setRetry(value=>value+1)}>Retry report</button></div>}
  {notice&&<p role="status">{notice}</p>}
  {!report&&!error&&<p role="status">Loading report…</p>}
  {report&&<>
   <h2>{report.title}</h2><p>{report.periods[0]} to {report.periods.at(-1)} · {report.row_count} rows · {report.source_invoice_count} source invoices</p>
   <div className="filing-actions"><button className="button secondary" disabled={busy} onClick={()=>download('xlsx')}>Download Excel</button><button className="button secondary" disabled={busy} onClick={()=>download('csv')}>Download CSV</button>{kind==='tax'&&<button className="button secondary" disabled={busy} onClick={()=>download('pdf')}>Download PDF summary</button>}</div>
   <p className="muted">{report.note}</p>
   {!report.row_count?<p>No records for this report and period.</p>:<div className="table-scroll"><table><thead><tr>{report.columns.map((column:string)=><th key={column}>{column}</th>)}</tr></thead><tbody>{report.rows.map((row:string[],index:number)=><tr key={index}>{row.map((value:string,column:number)=><td key={column}>{report.columns[column]==='Invoice ID'&&value?<Link href={`/bills?period=${encodeURIComponent(row[0])}&invoice=${encodeURIComponent(value)}`}>{value}</Link>:value}</td>)}</tr>)}</tbody></table></div>}
   {(offset>0||report.has_more)&&<div className="filing-actions"><button className="button secondary" disabled={busy||offset===0} onClick={()=>setOffset(value=>Math.max(0,value-100))}>Previous rows</button><span>Rows {offset+1}–{Math.min(offset+100,report.row_count)}</span><button className="button secondary" disabled={busy||!report.has_more} onClick={()=>setOffset(value=>value+100)}>Next rows</button></div>}
   <details><summary>Report provenance</summary><p>Generated: {report.generated_at}</p><p style={{overflowWrap:'anywhere'}}>Report fingerprint: {report.report_hash}</p><p>Excel includes invoice IDs, versions and source fingerprints. Exports regenerate current evidence and may differ if records change.</p></details>
  </>}
 </section>
}
