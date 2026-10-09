import {GST_TEXT} from '../lib/copy/gst'
import {GST} from '../lib/copy/gst'
import {FileText} from 'lucide-react'
export const sampleReason=GST_TEXT.text197
export function SampleActions(){return <div className="filing-actions">{[GST.workingPapers,GST_TEXT.text198,GST_TEXT.text37].map(t=><span title={sampleReason} key={t}><button className="button secondary" disabled aria-label={t}>{t}</button></span>)}</div>}
export function Comparison({summary,money}:{summary:any;money:(v:any)=>string}){return <section aria-label={GST_TEXT.text199}><h2>{GST.compare}</h2><div className="comparison-grid">{[['as_booked',GST.recorded],['restricted_2b',GST.matched],['fully_compliant',GST.eligible],['if_late_file',GST.noCredit]].map(([k,label])=><div className="comparison-card" key={k}><span>{label}</span><strong>{money(summary?.[k])}</strong></div>)}</div><p className="muted">{GST_TEXT.text200}</p></section>}
export function Delta({value,period,sample}:{value?:string;period:string;sample?:boolean}){const [year,month]=period.split('-').map(Number),prior=new Date(Date.UTC(year,month-2,1)).toLocaleDateString('en-IN',{month:'short',timeZone:'UTC'});return <small className={value?'metric-delta':'muted'}>{value?`${value.startsWith('-')?'▼':'▲'} ${value.replace('-','')}% vs ${prior}`:sample?GST_TEXT.text201:`No comparison for ${prior}`}</small>}
export function EmptyState({text,href,label}:{text:string;href:string;label:string}){return <div className="empty-state"><FileText size={24}/><p>{text}</p><a className="button secondary" href={href}>{label}</a></div>}
