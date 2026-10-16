"use client"
import {useState} from 'react'
import Link from 'next/link'

export default function BusinessList({data}:{data:any}){
 const [busy,setBusy]=useState(false),[error,setError]=useState('')
 async function switchBusiness(id:string){
  setBusy(true);setError('')
  try{
   const csrf=await fetch('/api/auth/csrf');if(!csrf.ok)throw Error('Please sign in again.')
   const {token}=await csrf.json()
   const response=await fetch('/api/workspace/client',{method:'POST',headers:{'content-type':'application/json','x-csrf-token':token},body:JSON.stringify({client_id:id})})
   if(!response.ok)throw Error('Unable to switch business. Please retry.')
   const account=await fetch('/api/settings/account',{cache:'no-store'})
   if(!account.ok||(await account.json()).client_id!==id)throw Error('Business access changed. Refresh to continue.')
   window.location.assign('/settings/profile'+window.location.search)
  }catch(e){setError(e instanceof Error?e.message:'Unable to switch business.')}finally{setBusy(false)}
 }
 return <section className="bv-card business-list-section" aria-labelledby="business-list-title">
  <div className="business-section-header"><div><h2 id="business-list-title">My Businesses</h2><p>View and manage businesses linked to your account.</p></div>{data.permissions?.includes('create_customer')&&<Link className="button primary" href="/settings/customers">+ Add Business</Link>}</div>
  <div className="business-list">{(data.clients||[]).map((client:any)=>{
   const active=client.id===data.client_id
   return <article className="business-list-card" key={client.id}>
    <div className="business-card-heading"><h3>{client.name}</h3><div className="business-card-badge">{active&&<span className="business-active">Active business</span>}</div></div>
    <div className="business-card-details">{active?<><p><span>GST registration</span>{data.profile?.gstin||data.profile?.registration_type||'Not provided'}</p><p><span>Your role</span>{data.is_owner?'Business owner':data.user.role==='viewer'?'Read-only viewer':data.user.role==='tax_admin'?'Accountant':'Business member'}</p></>:<p>Switch to view registration details and your business permissions.</p>}</div>
    <div className="business-card-actions">{active?<a className="button secondary" href="#business-details">{data.permissions?.includes('edit_profile')?'Edit Profile':'View Profile'}</a>:<button className="button secondary" disabled={busy} onClick={()=>switchBusiness(client.id)}>Switch to Business<span className="visually-hidden"> {client.name}</span></button>}</div>
   </article>
  })}</div>
  {!data.clients?.length&&<p>No linked businesses. Add a business to get started.</p>}
  {error&&<p role="alert">{error}</p>}
 </section>
}
