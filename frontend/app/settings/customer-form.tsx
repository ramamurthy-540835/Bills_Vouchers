'use client'
import {useRef,useState} from 'react'
import {useRouter} from 'next/navigation'
import Link from 'next/link'

export default function CustomerForm({userId}:{userId:string}){
 const router=useRouter()
 const locked=useRef(false),requestId=useRef('')
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[created,setCreated]=useState('')
 async function token(){const response=await fetch('/api/auth/csrf',{cache:'no-store'});if(!response.ok)throw Error('Please sign in again.');return (await response.json()).token}
 async function submit(event:React.FormEvent<HTMLFormElement>){
  event.preventDefault();if(locked.current)return
  const fields=Object.fromEntries(new FormData(event.currentTarget))
  locked.current=true;setBusy(true);setError('')
  try{
   if(!requestId.current){
    requestId.current=sessionStorage.getItem(`business-create:${userId}`)||crypto.randomUUID()
    sessionStorage.setItem(`business-create:${userId}`,requestId.current)
   }
   const response=await fetch('/api/settings/customers',{method:'POST',headers:{'content-type':'application/json','x-csrf-token':await token()},body:JSON.stringify({...fields,request_id:requestId.current})})
   const result=await response.json().catch(()=>({}))
   if(!response.ok){
    const detail=result.error?.message||result.detail
    throw Error(response.status===404?'Business creation is unavailable on this server. Please contact support; your entries have been kept.':typeof detail==='string'?detail:'Business creation could not be completed. Please retry.')
   }
   if(!result.saved||!result.client_id)throw Error('The server did not confirm business creation. Please retry.')
   sessionStorage.removeItem(`business-create:${userId}`);setCreated(result.client_id);router.refresh()
  }catch(e){setError(e instanceof Error?e.message:'Could not create business.')}finally{locked.current=false;setBusy(false)}
 }
 async function switchBusiness(){
  if(locked.current)return
  locked.current=true;setBusy(true);setError('')
  try{
   const response=await fetch('/api/workspace/client',{method:'POST',headers:{'content-type':'application/json','x-csrf-token':await token()},body:JSON.stringify({client_id:created})})
   if(!response.ok)throw Error('Business was created, but switching failed. Please retry or open My Businesses.')
   const account=await fetch('/api/settings/account',{cache:'no-store'})
   if(!account.ok||(await account.json()).client_id!==created)throw Error('Could not confirm the selected business. Please retry.')
   window.location.assign('/settings/onboarding'+window.location.search)
  }catch(e){setError(e instanceof Error?e.message:'Could not switch business.')}finally{locked.current=false;setBusy(false)}
 }
 return <section className="bv-card business-create"><h2>Add Business</h2><p>Create a business under your existing login, then complete its registration, address, contact and logo details.</p>
 {created?<><p role="status">Business created successfully. Your current business remains selected until you switch.</p><div className="business-create-actions"><Link className="button primary" href="/settings/profile">View My Businesses</Link><button className="button primary" disabled={busy} onClick={switchBusiness}>{busy?'Switching...':'Switch & Complete Onboarding'}</button></div></>:<form className="account-form" onSubmit={submit}>
 <label>Business Legal Name<input name="legal_name" required maxLength={200} disabled={busy}/></label>
 <label>Business GSTIN (optional)<input name="gstin" maxLength={15} disabled={busy}/></label>
 <label>Business Website (optional)<input name="website_url" type="url" placeholder="https://www.example.com" maxLength={2000} disabled={busy}/></label>
 <p className="wide muted">Use a full http:// or https:// website URL. GSTIN format validation does not verify government registration.</p>
 <div className="wide business-create-actions"><button className="button primary" disabled={busy}>{busy?'Creating business...':'Create Business'}</button><Link className="button secondary" href="/settings/profile">Cancel</Link></div>
 </form>}{error&&<p role="alert">{error}</p>}</section>
}
