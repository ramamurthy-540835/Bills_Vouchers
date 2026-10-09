'use client'
import {useState} from 'react'
import Link from 'next/link'
import {GST} from '../lib/copy/gst'
import GstEasyDashboard from './gst-easy-dashboard'

export default function ReturnsCredit({initial,money}:{initial:any;money:(v:unknown)=>string}){
 const [data,setData]=useState(initial),[busy,setBusy]=useState(false),[message,setMessage]=useState('')
 async function importStatement(file:File|undefined){if(!file)return;setBusy(true);setMessage('');try{
  const csrf=await fetch('/api/auth/csrf');const token=(await csrf.json()).token
  const r=await fetch(`/api/gst/bills/gstr2b?period=${data.period}`,{method:'POST',headers:{'x-csrf-token':token,'content-type':'application/json'},body:await file.text()})
  if(!r.ok){const error=await r.json();throw Error(error.error?.message||error.detail?.message||GST.failed)}
  const refreshed=await fetch(`/api/gst/bills/dashboard?period=${data.period}`);if(!refreshed.ok)throw Error(GST.failed)
  setData(await refreshed.json());setMessage(GST.imported2b)
 }catch(e){setMessage((e as Error).message)}finally{setBusy(false)}}
 return <><div className="section-heading">{data.can_write&&<label className="button primary">{GST.import2b}<input className="visually-hidden" aria-label={GST.import2b} type="file" accept=".json" disabled={busy} onChange={e=>{importStatement(e.target.files?.[0]);e.target.value=''}}/></label>}<Link className="button secondary" href={`/api/gst/bills/working-papers?period=${data.period}`}>{GST.workingPapers}</Link></div>{message&&<p className="notice" role="status">{message}</p>}<GstEasyDashboard data={data} money={money}/><section className="bv-card"><h2>{GST.reconciliation}</h2><div className="recon-list">{Object.entries(data.matches||{}).map(([k,v])=><div key={k}><span>{GST.matchLabels[k]}</span><strong>{String(v)}</strong></div>)}</div></section><section className="bv-card"><h2>{GST.decisions}</h2>{!data.decisions?.length?<p>{GST.noDecisions}</p>:<div className="table-scroll"><table><thead><tr>{[GST.supplier,GST.invoiceNo,GST.fields.description,GST.reconciliation,GST.itc,GST.tax,GST.ruleDetails].map(h=><th key={h}>{h}</th>)}</tr></thead><tbody>{data.decisions.map((d:any,i:number)=><tr key={i}><td>{d.supplier_name}</td><td>{d.invoice_number}</td><td>{d.description}</td><td>{GST.matchLabels[d.matching]}</td><td>{GST.eligibilityLabels[d.eligibility]}</td><td className="money">{money(d.tax)}</td><td><details><summary>{GST.ruleDetails}</summary>{d.rule}</details></td></tr>)}</tbody></table></div>}</section></>
}
