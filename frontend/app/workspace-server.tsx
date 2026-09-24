import { cookies, headers } from 'next/headers'
import { redirect } from 'next/navigation'
import Workspace from './workspace'
export async function WorkspacePage({view,searchParams}: {view:string;searchParams?:Promise<{period?:string;scenario?:string;tab?:string;scope?:string}>}) {
  const jar=await cookies()
  if(!jar.has('session')) redirect('/login')
  // Preserve signed cookie bytes; cookies().toString() URL-encodes base64 padding.
  const cookie=(await headers()).get('cookie')||''
  const query=await searchParams
  const endpoint=view==='gstworkspace'?'gst/workspace':view==='demo'?'demo/data':['overview','assistant'].includes(view)?'dashboard':'workspace'
  const params=new URLSearchParams({...query?.period?{period:query.period}:{},...view==='demo'&&query?.scenario?{scenario:query.scenario}:{},...view==='gstworkspace'&&query?.scope?{scope:query.scope}:{}})
  let response:Response|undefined, data:any=null
  try {
    response=await fetch(`${process.env.BACKEND_URL||'http://localhost:8000'}/api/${endpoint}?${params}`,{headers:{cookie},cache:'no-store',signal:AbortSignal.timeout(25000)})
    if(response.ok) data=await response.json()
  } catch {}
  if(response?.status===401) redirect('/login')
  if(response?.status===403){const err=await response.json().catch(()=>({}));if(err.error?.code==='password_change_required')redirect('/settings')}
  if(view==='demo'&&data)data={...data.dashboard,user:data.user,clients:[],demo_bundle:data,demo_lab:true,demo_tab:query?.tab}
  return <Workspace key={`${view}-${data?.client_id}-${data?.period}-${data?.scope||''}`} view={view} initial={data}/>
}
