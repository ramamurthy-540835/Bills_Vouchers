'use client'
import {useEffect,useState} from 'react'
import Link from 'next/link'
import {FileSearch} from 'lucide-react'
import BackToReportsButton from './back-to-reports-button'

import {reportGroups,reportEntries,ReportResponse} from '../lib/report-catalog'
const kinds:Record<string,string>={purchases:'Purchase register',sales:'Sales register',invoices:'Invoice listing',tax:'Tax-head summary',itc:'ITC decisions',reconciliation:'GSTR-2B reconciliation',audit:'Audit history',...Object.fromEntries(reportEntries.map(item=>[item.kind,item.title]))}
const filterLabels:Record<string,string>={party:'Supplier / Customer',invoice_type:'Invoice type',eligibility:'ITC status',matching:'Matching status',source:'Mismatch direction'}
const filterKeys=['q','party','invoice_type','eligibility','matching','source','date_from','date_to','sort']

export default function ReportsPanel({period,money,reportKind,businessName,gstin}:{period:string;money:(value:unknown)=>string;reportKind?:string;businessName?:string;gstin?:string}){
 const [kind,setKind]=useState(reportKind||'purchases'),[scope,setScope]=useState('month'),[offset,setOffset]=useState(0)
 const [filters,setFilters]=useState<Record<string,string>>({})
 const entry=reportEntries.find(item=>item.kind===kind)
 const [report,setReport]=useState<ReportResponse|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[retry,setRetry]=useState(0),[notice,setNotice]=useState('')
 useEffect(()=>{
  const query=new URLSearchParams(window.location.search)
  const initialKind=query.get('kind'),initialScope=query.get('range')
  setFilters(Object.fromEntries(filterKeys.filter(key=>query.has(key)).map(key=>[key,query.get(key)!])))
  if(!reportKind&&initialKind&&kinds[initialKind])setKind(initialKind)
  if(initialScope&&['month','quarter','financial_year'].includes(initialScope))setScope(initialScope)
 },[])
 useEffect(()=>{
  const controller=new AbortController();setReport(null);setError('');setNotice('')
  const query=new URLSearchParams({period,kind,scope_name:scope,offset:String(offset),...filters})
  fetch(`/api/gst/bills/reports?${query}`,{cache:'no-store',signal:AbortSignal.any([controller.signal,AbortSignal.timeout(25000)])})
   .then(async response=>{if(response.status===401)throw Error('Your session expired. Sign in again.');const value=await response.json();if(!response.ok)throw Error(value.error?.message||value.detail?.message||(typeof value.detail==='string'?value.detail:null)||'Could not load this report.');return value})
   .then(setReport).catch(e=>{if(e.name!=='AbortError')setError(e.message)})
  const url=new URL(window.location.href);for(const key of filterKeys){if(filters[key])url.searchParams.set(key,filters[key]);else url.searchParams.delete(key)};url.searchParams.set('kind',kind);url.searchParams.set('range',scope);window.history.replaceState(null,'',url)
  return ()=>controller.abort()
 },[period,kind,scope,offset,retry,filters])
 async function download(format:string){setBusy(true);setError('');setNotice('');try{
  const query=new URLSearchParams({period,kind,scope_name:scope,format,...filters})
  const response=await fetch(`/api/gst/bills/reports?${query}`,{cache:'no-store'})
  if(!response.ok){const value=await response.json();throw Error(value.error?.message||value.detail||'Export failed.')}
  const url=URL.createObjectURL(await response.blob()),a=document.createElement('a')
  a.href=url;a.download=`GST-Easy-${kind}-${period}-${scope}.${format}`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)
  setNotice('Report downloaded. It was regenerated from the current authorized evidence.')
 }catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 return <section className="bv-card reports-page" aria-label="Business reports" style={{minWidth:0,maxWidth:'100%'}}>
  <p>View and analyze your business GST, invoices, credit and reconciliation details.</p>
  <p><strong>{businessName||report?.business_name||'Selected business'}</strong>{(gstin||report?.gstin)&&` | GSTIN: ${gstin||report?.gstin}`} | {period}</p>
  {reportKind?<header className="report-detail-header"><div><h2>{entry?.title}</h2><p>{entry?.description}</p></div><BackToReportsButton period={period} range={scope}/></header>:<div className="report-catalog" aria-label="Report categories">{reportGroups.map(group=><section key={group.title}><h2>{group.title}</h2>{group.items.map(item=><Link key={item.kind} href={`/reports/${item.slug}?period=${period}&range=${scope}`} aria-label={`Open report: ${item.title}`}><span>{item.title}</span><small>{item.description}</small><span>Open report</span></Link>)}</section>)}</div>}

  <div className="filing-actions" style={{minWidth:0}}>
   <label style={{minWidth:0,maxWidth:'100%'}}>Report<select aria-label="Report" style={{maxWidth:'100%'}} value={kind} disabled={busy} onChange={e=>{const target=reportEntries.find(item=>item.kind===e.target.value);if(reportKind){window.location.assign(target?`/reports/${target.slug}?period=${period}&range=${scope}`:`/reports?kind=${e.target.value}&period=${period}&range=${scope}`)}else{setKind(e.target.value);setOffset(0)}}}>{Object.entries(kinds).map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label>
   <label style={{minWidth:0,maxWidth:'100%'}}>Reporting period<select aria-label="Reporting period" style={{maxWidth:'100%'}} value={scope} disabled={busy} onChange={e=>{setScope(e.target.value);setOffset(0)}}><option value="month">Selected month</option><option value="quarter">Quarter containing selected month</option><option value="financial_year">Financial year containing selected month</option></select></label>
   <button className="button secondary" disabled={busy} onClick={()=>setRetry(value=>value+1)}>Refresh report</button>
  </div>
  {error&&<div role="alert"><p>{error}</p><button className="button secondary" onClick={()=>setRetry(value=>value+1)}>Retry report</button></div>}
  {notice&&<p role="status">{notice}</p>}
  {!report&&!error&&<p role="status">Loading report…</p>}
  {report&&<>
   {!reportKind&&<h2>{report.title}</h2>}<p>{report.periods[0]} to {report.periods.at(-1)} · {report.row_count} rows · {report.source_invoice_count} source invoices</p>
   <div className="filing-actions">{report?.can_export===false?<p className="muted">Synthetic demo reports are view-only. Financial exports and filing remain restricted.</p>:<><button className="button secondary" disabled={busy} onClick={()=>download('xlsx')}>Download Excel</button><button className="button secondary" disabled={busy} onClick={()=>download('csv')}>Download CSV</button>{kind==='tax'&&<button className="button secondary" disabled={busy} onClick={()=>download('pdf')}>Download PDF summary</button>}</>}</div>
   {report.warnings?.map(message=><p className="notice" key={message}>{message}</p>)}
   {kind!=='cash'&&<form key={JSON.stringify(filters)} className="filing-actions" onSubmit={event=>{event.preventDefault();const values=new FormData(event.currentTarget);setFilters(Object.fromEntries([...values.entries()].filter(([,value])=>Boolean(value)).map(([key,value])=>[key,String(value)])));setOffset(0)}}>
    <label>Search invoices<input name="q" defaultValue={filters.q||''} maxLength={200}/></label>
    {['party','invoice_type','eligibility','matching','source'].filter(key=>report.filter_options?.[key]?.length).map(key=><label key={key}>{filterLabels[key]}<select name={key} aria-label={filterLabels[key]} defaultValue={filters[key]||''}><option value="">All</option>{report.filter_options![key].map(value=><option key={value} value={value}>{value}</option>)}</select></label>)}
    {report.columns.includes('Invoice date')&&<><label>From date<input name="date_from" type="date" defaultValue={filters.date_from||''}/></label><label>To date<input name="date_to" type="date" defaultValue={filters.date_to||''}/></label></>}
    <label>Sort rows<select name="sort" defaultValue={filters.sort||''}><option value="">Source order</option>{report.columns.flatMap(column=>[<option key={column} value={column}>{column} ascending</option>,<option key={'-'+column} value={'-'+column}>{column} descending</option>])}</select></label>
    <button className="button secondary" type="submit">Apply filters</button><button className="button quiet" type="button" onClick={()=>{setFilters({});setOffset(0)}}>Clear filters</button>
   </form>}
   {report.summary&&Object.keys(report.summary).length>0&&<details open><summary>Filtered row totals (INR)</summary><div className="recon-list">{Object.entries(report.summary).map(([key,value])=><div key={key}><span>{key}</span><strong>{money(value)}</strong></div>)}</div></details>}
   <section className="report-information" aria-labelledby="report-information-title"><h3 id="report-information-title">Report Information</h3><p>{['pending','invoices','audit','reconciliation','mismatches','unmatched'].includes(kind)?'Showing review records and available evidence for the selected business and reporting period.':'Showing confirmed financial records for the selected business and reporting period.'}</p><dl className="report-context"><div><dt>Business</dt><dd>{businessName||report.business_name||'Selected business'}</dd></div><div><dt>Reporting period</dt><dd>{report.periods[0]} to {report.periods.at(-1)}</dd></div><div><dt>Data source</dt><dd>Canonical GST bills and available statement evidence</dd></div>{report.generated_at&&<div><dt>Report generated</dt><dd>{report.generated_at}</dd></div>}</dl>
   <details className="financial-disclosure"><summary>Calculation details &amp; data limitations</summary>{report.note.split(/(?<=\.)\s+/).map((note,index)=><p key={index}>{note}</p>)}
   {report.detail_summary?.filter(row=>Object.keys(row.values).length>0).map(row=><section key={row.period}><h4>{row.period} full-period context</h4><div className="recon-list">{Object.entries(row.values).map(([key,value])=><div key={key}><span>{key}</span><strong>{/^-?\d+(\.\d+)?$/.test(value)?money(value):value}</strong></div>)}</div></section>)}
   </details></section>
   {kind==='credit'&&<p>Eligible classifications alone are not a credit claim. The monthly estimate also applies statement matching, credit availability and credit-note rules. Unmatched positive invoices do not contribute to usable credit.</p>}
   {report.monthly_summary?.length>0&&<div className="table-scroll"><table aria-label="Monthly financial context"><thead><tr><th>Month</th><th>Usable ITC</th><th>Output GST</th><th>Estimated cash</th><th>Purchases without ITC</th></tr></thead><tbody>{report.monthly_summary.map((row:any)=><tr key={row.period}><td>{row.period}</td>{['eligible_credit','output_tax','cash_required','non_gst'].map(key=><td key={key}>{row.confirmed_count?money(row.totals[key]):'\u2014'}</td>)}</tr>)}</tbody></table></div>}
   {report.monthly_summary?.length>0&&<details><summary>Tax-head calculation context</summary><div className="table-scroll"><table><thead><tr><th>Month</th><th>Tax head</th><th>Usable credit</th><th>Output GST</th><th>Estimated cash</th></tr></thead><tbody>{report.monthly_summary.flatMap((row:any)=>['igst','cgst','sgst','cess'].map(head=><tr key={`${row.period}-${head}`}><td>{row.period}</td><td>{head.toUpperCase()}</td>{['credit','output','cash'].map(key=><td key={key}>{row.confirmed_count?money(row.heads[key][head]):'\u2014'}</td>)}</tr>))}</tbody></table></div></details>}
   {report.monthly_cash_scenarios?.length>0&&<details><summary>Monthly cash scenarios</summary><div className="table-scroll"><table><thead><tr><th>Month</th><th>Recorded credit</th><th>Matched credit</th><th>Eligibility checked</th><th>No credit</th></tr></thead><tbody>{report.monthly_cash_scenarios.map((row:any)=><tr key={row.period}>{['period','recorded','matched','eligible','noCredit'].map(key=><td key={key}>{row[key]}</td>)}</tr>)}</tbody></table></div></details>}
   {!report.row_count?<div className="financial-empty" role="status"><FileSearch size={28} aria-hidden/><h3>No records found</h3><p>No records are available for the selected business and reporting period.</p><Link className="button secondary" href={`/bills?period=${period}`}>View Bills &amp; Vouchers</Link></div>:<div className="table-scroll"><table><thead><tr>{report.columns.map((column:string)=><th key={column}>{column}</th>)}</tr></thead><tbody>{report.rows.map((row:string[],index:number)=><tr key={index}>{row.map((value:string,column:number)=><td key={column}>{report.columns[column]==='Invoice ID'&&value?<><Link href={`/bills?period=${encodeURIComponent(row[0])}&invoice=${encodeURIComponent(value)}`}>Open invoice / review</Link>{report.evidence_ids?.includes(value)&&<><br/><a href={`/api/gst/bills/${encodeURIComponent(value)}/original`} target="_blank" rel="noreferrer">View original</a></>}</>:report.columns[column]==='Case ID'&&value?<Link href={`/gst/filing?period=${encodeURIComponent(row[0])}&case=${encodeURIComponent(value)}#reconciliation`}>Review exception</Link>:report.columns[column]==='Statement evidence'?value.split(', ').filter(digest=>/^[a-f0-9]{64}$/.test(digest)).map(digest=><a key={digest} href={`/api/gst/bills/gstr2b/${digest}/original?period=${encodeURIComponent(row[0])}`} target="_blank" rel="noreferrer">View statement</a>):value}</td>)}</tr>)}</tbody></table></div>}
   {(offset>0||report.has_more)&&<div className="filing-actions"><button className="button secondary" disabled={busy||offset===0} onClick={()=>setOffset(value=>Math.max(0,value-100))}>Previous rows</button><span>Rows {offset+1}–{Math.min(offset+100,report.row_count)}</span><button className="button secondary" disabled={busy||!report.has_more} onClick={()=>setOffset(value=>value+100)}>Next rows</button></div>}
   <details className="financial-disclosure"><summary>Data Sources &amp; Report Provenance</summary><dl className="report-context"><div><dt>Business</dt><dd>{businessName||report.business_name||'Selected business'}</dd></div><div><dt>Period</dt><dd>{report.periods.join(', ')}</dd></div><div><dt>Source</dt><dd>Canonical GST bills and available statement evidence</dd></div><div><dt>Applied filters</dt><dd>{Object.entries(filters).map(([key,value])=>`${filterLabels[key]||key}: ${value}`).join('; ')||'No additional filters'}</dd></div></dl><p>Generated: {report.generated_at}</p><p style={{overflowWrap:'anywhere'}}>Report fingerprint: {report.report_hash}</p><p>Excel includes invoice IDs, versions and source fingerprints. Exports regenerate current evidence and may differ if records change.</p></details>
  </>}
 </section>
}
