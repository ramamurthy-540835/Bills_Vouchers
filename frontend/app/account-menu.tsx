'use client'
import Link from 'next/link'
import {useEffect,useRef} from 'react'
import {usePathname} from 'next/navigation'
import {ChevronDown} from 'lucide-react'
import {getVisibleAccountMenu,workspaceDestination} from '../lib/navigation'
export default function AccountMenu({data,request,action}:{data:any;request:(path:string,body?:any)=>Promise<any>;action:(fn:()=>Promise<void>)=>Promise<void>}){
 const menu=useRef<HTMLDetailsElement>(null),path=usePathname()
 const close=()=>{if(menu.current)menu.current.open=false}
 useEffect(()=>{close()},[path])
 useEffect(()=>{const outside=(event:PointerEvent)=>{if(!menu.current?.contains(event.target as Node))close()};document.addEventListener('pointerdown',outside);return()=>document.removeEventListener('pointerdown',outside)},[])
 const user=data?.user
 const initials=(user?.full_name||user?.email||'?').trim().split(/\s+/).slice(0,2).map((p:string)=>p[0]).join('').toUpperCase()
 return <details ref={menu} className="account-menu" onKeyDown={event=>{if(event.key==='Escape'){close();menu.current?.querySelector('summary')?.focus()}}}>
 <summary aria-label="Account menu"><span className="avatar">{initials}</span><ChevronDown size={16}/></summary>
 <div className="account-popover"><div className="account-contact"><strong>{user?.full_name}</strong><small>{user?.email}</small><span>{data?.profile?.legal_name}</span></div><hr/>
 {getVisibleAccountMenu(data).map(item=><Link key={item.id} href={item.route} onClick={close}><item.icon size={16} aria-hidden/> {item.label}</Link>)}
 {data?.clients?.length>1&&<label>Switch business<select aria-label="Switch business" value={data.client_id} onChange={event=>{const id=event.target.value;action(async()=>{await request('/api/workspace/client',{client_id:id});const response=await fetch('/api/settings/account',{cache:'no-store'});if(!response.ok)throw new Error('Unable to load the selected business. Reload to try again.');const fresh=await response.json();if(fresh.client_id!==id)throw new Error('Business access changed. Reload to continue.');close();window.location.assign(workspaceDestination(fresh,new URL(window.location.href)))})}}>{data.clients.map((client:any)=><option key={client.id} value={client.id}>{client.name}</option>)}</select></label>}
 <hr/><button onClick={()=>action(async()=>{await request('/api/auth/logout');close();window.location.href='/login'})}>Logout</button></div></details>
}
