import Link from 'next/link'

export default function CustomerDashboard({data,money}:{data:any;money:(value:unknown)=>string}) {
  const summary=data.summary,totals=data.totals,period=data.period
  const filingHref=data.sample?`/demo?scenario=${data.scenario||'mixed'}&period=${period}&tab=filing`:`/gst/workspace?period=${period}`
  return <>
    <section className="overview-intro"><div><p className="eyebrow">YOUR MONTH AT A GLANCE</p><h2>{data.profile?.legal_name||'Your business'}</h2><p>Your tax position for {period}, based on validated financial entries.</p><Link href={filingHref}>View your GST statement →</Link></div><div><span className="chip success">{data.validated_invoices||0} validated invoices</span><p className="muted">{data.updated_at?`Figures updated ${new Date(data.updated_at).toLocaleDateString('en-IN')}`:'Awaiting validated figures'}</p></div></section>
    {!summary||!totals?<section className="bv-card empty-state"><h2>No validated figures yet</h2><p>Your financial dashboard will appear when validated entries are available for this period. Bills awaiting review are excluded.</p></section>:<>
      <section className="metric-grid">{[['Eligible input credit',totals.eligible_credit,'Available after credit adjustments','green'],['Output tax',totals.output_tax,'Including ECO cash-only liability','blue'],['Cash required',totals.cash_required,'After tax-head set-off','amber'],['Input tax recorded',totals.input_tax,'From validated purchase entries','green']].map(([label,value,detail,tone])=><div className={`metric-card ${tone}`} key={label}><span>{label}</span><strong>{money(value)}</strong><small>{detail}</small></div>)}</section>
      <div className="filing-grid"><section className="bv-card"><h2>Your tax position</h2><p className="muted">Credit and liability by tax head.</p><div className="table-scroll"><table><thead><tr><th>Tax head</th><th>Eligible credit</th><th>Output tax</th><th>ECO liability</th><th>Cash required</th></tr></thead><tbody>{['igst','cgst','sgst','cess'].map(h=><tr key={h}><td className="uppercase">{h}</td>{['eligible_by_head','output_by_head','eco_by_head','cash_by_head'].map(k=><td className="money" key={k}>{money(summary[k]?.[h]||'0')}</td>)}</tr>)}</tbody></table></div></section>
      <section className="bv-card"><h2>Credit adjustments</h2><p className="muted">Amounts excluded from currently eligible credit.</p><div className="recon-list">{[['blocked','Blocked credit'],['deferred','Deferred credit'],['reversal','Credit reversals']].map(([key,label])=><div key={key}><span>{label}</span><strong>{money(totals[key])}</strong></div>)}<div><span>Non-GST purchases</span><strong>{money(summary.non_gst||'0')}</strong></div></div><Link href={filingHref}>View credit decisions →</Link></section></div>
    </>}
  </>
}
