import {WorkspacePage} from '../workspace-server'
export default function Page({searchParams}:{searchParams:Promise<{period?:string}>}){return <WorkspacePage view="assistant" searchParams={searchParams}/>}
