import {notFound} from 'next/navigation'
import {WorkspacePage} from '../../workspace-server'
import {reportEntries} from '../../../lib/report-catalog'
export default async function Page({params,searchParams}:{params:Promise<{report:string}>;searchParams:Promise<{period?:string;range?:string}>}){
 const {report}=await params
 const entry=reportEntries.find(item=>item.slug===report)
 if(!entry)notFound()
 return <WorkspacePage view="reports" reportKind={entry.kind} searchParams={searchParams}/>
}
