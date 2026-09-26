'use client'
import {useRef, useState} from 'react'
import Link from 'next/link'
import {CircleHelp, FileUp} from 'lucide-react'
import {GST, TOOLTIPS, periodSummary} from '../lib/copy/gst'

export function TermTip({term,onLearn}:{term:string;onLearn:()=>void}){return <details className="term-tip"><summary aria-label={`${GST.help}: ${(GST as any)[term]}`}><CircleHelp size={16}/></summary><div role="tooltip"><p>{TOOLTIPS[term]}</p><button onClick={onLearn}>{GST.learn}</button></div></details>}

export default function GstEasyDashboard({data,money}:{data:any;money:(v:unknown)=>string}){
 const dialog=useRef<HTMLDialogElement>(null),[open,setOpen]=useState(false)
 const learn=()=>{setOpen(true);dialog.current?.showModal()}
 const totals=data.totals||{},hasData=data.confirmed_count>0
 const cards=[['credit','eligible_credit'],['liability','output_tax'],['cash','cash_required'],['nonGst','non_gst']]
 return <>
  <div className="section-heading"><div><span className="chip">{GST.uploaded}</span><p>{periodSummary(data.period,data.confirmed_count,data.review_count)}</p><small>{GST.view}</small></div><button className="button quiet" onClick={learn}><CircleHelp size={18}/>{GST.help}</button></div>
  <section className="metric-grid overview-kpis">{cards.map(([key,field])=><div className="metric-card" key={key}><span>{(GST as any)[key]}<TermTip term={key} onLearn={learn}/></span><strong>{hasData?money(totals[field]):'—'}</strong><small>{key==='credit'?GST.creditCaption:(GST as any)[`${key}Detail`]}</small></div>)}</section>
  {!data.bill_count&&<section className="bv-card empty-state"><FileUp size={24}/><p>{GST.empty}</p><Link className="button primary" href={`/bills?period=${data.period}`}>{GST.uploadFirst}</Link></section>}
  <section className="bv-card"><h2>{GST.compare}</h2><div className="recon-list">{['recorded','matched','eligible','noCredit'].map(key=><div key={key}><span>{(GST as any)[key]} <TermTip term={key} onLearn={learn}/></span><strong>{key==='matched'?GST.noMatching:hasData?money(key==='noCredit'?totals.output_tax:totals.cash_required):'—'}</strong></div>)}</div><p className="muted">{GST.matchingPending}</p></section>
  <section className="bv-card"><h2>{GST.sectionHeads}</h2><div className="table-scroll"><table><thead><tr><th>{GST.head}</th><th>{GST.creditShort}</th><th>{GST.liability}</th><th>{GST.cashShort}</th></tr></thead><tbody>{['igst','cgst','sgst','cess'].map(h=><tr key={h}><td>{GST.fields[h]}</td>{['credit','output','cash'].map(k=><td className="money" key={k}>{hasData?money(data.heads?.[k]?.[h]):'—'}</td>)}</tr>)}</tbody></table></div><p className="muted">{GST.formulaNote}</p></section>
  <dialog ref={dialog} className="glossary-drawer" onClose={()=>setOpen(false)} aria-label={GST.help}><button className="button quiet" onClick={()=>dialog.current?.close()}>{GST.close}</button><h2>{GST.help}</h2>{open&&<><p>{GST.formula}</p><p className="formula-values">{money(totals.output_tax)} − {money(totals.eligible_credit)} → {money(totals.cash_required)}</p><p>{GST.formulaNote}</p>{Object.entries(TOOLTIPS).map(([k,v])=><section key={k}><h3>{(GST as any)[k]}</h3><p>{v}</p></section>)}<h3>{GST.illustration}</h3><table><thead><tr><th>{GST.supplier}</th><th>{GST.tax}</th><th>{GST.appears}</th><th>{GST.usable}</th></tr></thead><tbody>{[['A','1000',true],['B','2000',false],['C','1500',true]].map(([name,amount,matched])=><tr key={String(name)}><td>{GST.supplier} {name}</td><td>{money(amount)}</td><td>{matched?GST.yes:GST.no}</td><td>{money(matched?amount:'0')}</td></tr>)}</tbody></table></> }</dialog>
 </>
}
