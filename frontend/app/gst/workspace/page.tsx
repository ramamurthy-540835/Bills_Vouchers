import { WorkspacePage } from '../../workspace-server'
export default function Page({searchParams}:{searchParams:Promise<{period?:string;scope?:string}>}){return <WorkspacePage view="gstworkspace" searchParams={searchParams}/>}
