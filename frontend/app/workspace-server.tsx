import { cookies, headers } from 'next/headers'
import { redirect } from 'next/navigation'
import Workspace from './workspace'
export async function WorkspacePage({view,searchParams}: {view:string;searchParams?:Promise<{period?:string}>}) {
  const jar=await cookies()
  if(!jar.has('session')) redirect('/login')
  // Preserve signed cookie bytes; cookies().toString() URL-encodes base64 padding.
  const cookie=(await headers()).get('cookie')||''
  const query=await searchParams
  let response:Response|undefined, data:any=null
  try {
    response=await fetch(`${process.env.BACKEND_URL||'http://localhost:8000'}/api/workspace${query?.period?'?period='+encodeURIComponent(query.period):''}`,{headers:{cookie},cache:'no-store',signal:AbortSignal.timeout(25000)})
    if(response.ok) data=await response.json()
  } catch {}
  if(response?.status===401) redirect('/login')
  if(response?.status===403){const err=await response.json().catch(()=>({}));if(err.error?.code==='password_change_required')redirect('/settings')}
  return <Workspace view={view} initial={data}/>
}
