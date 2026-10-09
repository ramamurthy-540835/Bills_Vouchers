import {GST_TEXT} from '../lib/copy/gst'
import {GST} from '../lib/copy/gst'
import Link from 'next/link'
import {Comparison,Delta} from './v7-panels'

export default function CustomerDashboard({data,money}:{data:any;money:(value:unknown)=>string}) {
  const summary=data.summary,totals=data.totals,period=data.period
  const filingHref=`/gst/workspace?period=${period}`
  return <>
    <section className="metric-grid overview-kpis">{[[GST.credit,totals?.eligible_credit,GST.creditDetail,'green'],[GST.liability,totals?.output_tax,GST.liabilityDetail,'blue'],[GST.cash,totals?.cash_required,GST.cashDetail,'amber'],[GST.nonGst,summary?.non_gst,GST_TEXT.text69,'green']].map(([label,value,detail,tone])=><div className={`metric-card ${tone}`} key={label}><span>{label}</span><strong>{summary&&totals?money(value):'—'}</strong><Delta value={data.deltas?.[String(label)]} period={period} sample={data.sample}/><small>{summary&&totals?detail:`No documents for ${period}`}</small></div>)}</section>
    {!summary||!totals?<><section className="bv-card empty-state"><h2>{GST_TEXT.text70}</h2><p>{GST_TEXT.text71}</p><Link className="button primary" href={`/documents?period=${period}`}>{GST_TEXT.text72}</Link></section><div className="filing-grid"><section className="bv-card"><h2>{GST_TEXT.text73}</h2><p className="muted">{GST_TEXT.text74}</p><div className="chart-placeholder" aria-label={GST_TEXT.text75}>{GST_TEXT.text76}</div></section><section className="bv-card"><h2>{GST_TEXT.text77}</h2><p className="muted">{GST_TEXT.text78}</p><div className="chart-placeholder" aria-label={GST_TEXT.text79}>{GST_TEXT.text80}</div></section></div></>:<>
      <Comparison summary={summary} money={money}/><div className="filing-grid"><section className="bv-card"><h2>{GST_TEXT.text81}</h2><p className="muted">{GST_TEXT.text82}</p><div className="table-scroll"><table><thead><tr><th>{GST_TEXT.text83}</th><th>{GST_TEXT.text84}</th><th>{GST.liability}</th><th>{GST_TEXT.text85}</th><th>{GST_TEXT.text86}</th></tr></thead><tbody>{['igst','cgst','sgst','cess'].map(h=><tr key={h}><td className="uppercase">{h}</td>{['eligible_by_head','output_by_head','eco_by_head','cash_by_head'].map(k=><td className="money" key={k}>{money(summary[k]?.[h]||'0')}</td>)}</tr>)}</tbody></table></div></section>
      <section className="bv-card"><h2>{GST_TEXT.text87}</h2><p className="muted">{GST_TEXT.text88}</p><div className="recon-list">{[['blocked',GST_TEXT.text89],['deferred',GST_TEXT.text90],['reversal',GST_TEXT.text91]].map(([key,label])=><div key={key}><span>{label}</span><strong>{money(totals[key])}</strong></div>)}<div><span>{GST.nonGst}</span><strong>{money(summary.non_gst||'0')}</strong></div></div><Link href={filingHref}>{GST_TEXT.text92}</Link></section></div>
    </>}
  </>
}
