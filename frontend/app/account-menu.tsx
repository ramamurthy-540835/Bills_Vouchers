'use client'
import {GST_TEXT} from '../lib/copy/gst'

import Link from 'next/link'
import {ChevronDown} from 'lucide-react'
export default function AccountMenu({data,request,action}:{data:any;request:(path:string,body?:any)=>Promise<any>;action:(fn:()=>Promise<void>)=>Promise<void>}){
 const user=data?.user, profile=data?.profile
 const initials=(user?.full_name||user?.email||'?').trim().split(/\s+/).slice(0,2).map((p:string)=>p[0]).join('').toUpperCase()
 return <details className="account-menu" onKeyDown={e=>{if(e.key===GST_TEXT.text189)e.currentTarget.open=false}}><summary aria-label={GST_TEXT.text190}><span className="avatar">{initials}</span><ChevronDown size={16}/></summary><div className="account-popover"><div className="account-contact"><strong>{profile?.legal_name||GST_TEXT.text191}</strong><span>{profile?.contact_person||user?.full_name||GST_TEXT.text192}</span><small>{profile?.contact_phone||profile?.contact_mobile||user?.mobile_number||GST_TEXT.text193}</small><small>{profile?.contact_email||user?.email||GST_TEXT.text194}</small></div><hr/><Link href="/settings/account">{GST_TEXT.text24}</Link><Link href="/settings/onboarding">Business onboarding</Link><Link href="/settings/members">Workspace access</Link><Link href="/settings/profile">{GST_TEXT.text25}</Link><Link href="/settings/notifications">{GST_TEXT.text26}</Link>{data?.clients?.length>1&&<label>{GST_TEXT.text195}<select aria-label={GST_TEXT.text195} value={data.client_id} onChange={e=>action(async()=>{await request('/api/workspace/client',{client_id:e.target.value});window.location.reload()})}>{data.clients.map((c:any)=><option key={c.id} value={c.id}>{c.name}</option>)}</select></label>}<hr/><button onClick={()=>action(async()=>{await request('/api/auth/logout');window.location.href='/login'})}>{GST_TEXT.text196}</button></div></details>
}
