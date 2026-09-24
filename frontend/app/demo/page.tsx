import {WorkspacePage} from '../workspace-server'
export default function Page({searchParams}:{searchParams:Promise<{period?:string}>}){return <WorkspacePage view="demo" searchParams={searchParams}/>}
