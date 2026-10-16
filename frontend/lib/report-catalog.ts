export const reportGroups=[
 {title:'GST & ITC Reports',items:[
  {kind:'credit',slug:'usable-itc',title:'Usable Input Tax Credit',description:'Confirmed purchase tax, eligibility decisions and statement matching.'},
  {kind:'liability',slug:'gst-liability',title:'GST Liability on Sales',description:'Confirmed sales, signed notes and output tax by head.'},
  {kind:'cash',slug:'cash-requirement',title:'Estimated GST Cash Requirement',description:'Four credit scenarios and the existing tax-head set-off calculation.'},
  {kind:'without_itc',slug:'purchases-without-itc',title:'Purchases Without ITC',description:'Non-creditable or unestablished purchase credit, with reasons.'}]},
 {title:'Invoice & Reconciliation Reports',items:[
  {kind:'pending',slug:'pending-reviews',title:'Pending Bill Reviews',description:'Extracted invoices requiring review or correction.'},
  {kind:'mismatches',slug:'reconciliation-mismatches',title:'Reconciliation Mismatches',description:'Book and statement differences, candidates and review evidence.'},
  {kind:'unmatched',slug:'unmatched-invoices',title:'Unmatched Invoices',description:'Records missing from books or an imported statement.'}]},
 {title:'Sales & Purchase Reports',items:[
  {kind:'sales',slug:'sales-register',title:'Sales Register',description:'Confirmed sales invoices and signed credit notes.'},
  {kind:'purchases',slug:'purchase-register',title:'Purchase Register',description:'Confirmed purchases, eligibility and statement matching.'}]},
] as const
export const reportEntries=reportGroups.flatMap(group=>[...group.items])
export type ReportKind=typeof reportEntries[number]['kind']
export type ReportResponse={can_export?:boolean;kind:string;title:string;client_id:string;business_name?:string;gstin?:string;periods:string[];columns:string[];rows:string[][];row_count:number;source_invoice_count:number;has_more:boolean;note:string;generated_at:string;report_hash:string;warnings?:string[];evidence_ids?:string[];detail_summary?:{period:string;values:Record<string,string>}[];summary?:Record<string,string>;filter_options?:Record<string,string[]>;monthly_summary:{period:string;confirmed_count:number;totals:Record<string,string>;heads:Record<string,Record<string,string>>}[];monthly_cash_scenarios:Record<string,string>[]}
