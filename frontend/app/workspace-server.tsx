import {backendFetch} from '../lib/backend-fetch'
import { cookies, headers } from 'next/headers'
import { redirect } from 'next/navigation'
import Workspace from './workspace'
import {navigation,canAccessMenuItem} from '../lib/navigation'
export async function WorkspacePage({view,searchParams,reportKind}: {view:string;reportKind?:string;searchParams?:Promise<{period?:string;scenario?:string;tab?:string;scope?:string;range?:string}>}) {
  const jar=await cookies()
  if(!jar.has('session')) redirect('/login')
  // Preserve signed cookie bytes; cookies().toString() URL-encodes base64 padding.
  const cookie=(await headers()).get('cookie')||''
  const query=await searchParams
  const endpoint=['gstworkspace','overview','bills','filing','assistant','search','reports'].includes(view)?'gst/bills/dashboard':view==='demo'?'demo/data':'workspace'
  const params=new URLSearchParams({...query?.period?{period:query.period}:{},...view==='demo'&&query?.scenario?{scenario:query.scenario}:{},...view==='gstworkspace'&&query?.scope?{scope:query.scope}:{}})
  if(view==='gstworkspace'&&query?.range)params.set('scope_name',query.range)
  let response:Response|undefined, data:any=null
  let identity:Response|undefined
  try {
    const base=process.env.BACKEND_URL||'http://localhost:8000'
    // Independent authenticated snapshots may load together. The client identity
    // equality and permission checks below still gate rendering of financial data.
    const results=await Promise.allSettled([
      backendFetch(`${base}/api/${endpoint}?${params}`,{headers:{cookie},cache:'no-store',signal:AbortSignal.timeout(25000)}),
      backendFetch(`${base}/api/settings/account`,{headers:{cookie},cache:'no-store',signal:AbortSignal.timeout(25000)}),
    ])
    response=results[0].status==='fulfilled'?results[0].value:undefined
    identity=results[1].status==='fulfilled'?results[1].value:undefined
    if(response?.ok) data=await response.json()
  } catch {}
  if(response?.status===401) redirect('/login')
  if(response?.status===403){const err=await response.json().catch(()=>({}));if(err.error?.code==='password_change_required')redirect('/settings');if(err.error?.code==='mobile_verification_required')redirect('/settings/account')}
  if(view==='demo'&&data)data={...data.dashboard,user:data.user,clients:[],demo_bundle:data,demo_lab:true,demo_tab:query?.tab}
  if(data){
    let access:any=null
    try{
      if(identity?.ok)access=await identity.json()
    }catch{}
    const item=navigation.find(item=>item.id===view)
    if(access&&item&&!canAccessMenuItem(access,item))redirect('/gst/workspace')
    // Never combine financial data with a different workspace's identity snapshot.
    if(!access||(view!=='demo'&&data.client_id!==access.client_id))data=null
    else data={...data,navigation_client_id:access.client_id,user:access.user,permissions:access.permissions,is_owner:access.is_owner,clients:access.clients,can_write:data.can_write===true}
  }
  return <Workspace key={`${view}-${data?.client_id}-${data?.period}-${data?.scope_name||''}`} view={view} initial={data?{...data,report_kind:reportKind}:null}/>
}
