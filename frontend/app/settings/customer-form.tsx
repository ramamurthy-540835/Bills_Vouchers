'use client'
import {useState} from 'react'

export default function CustomerForm(){
 const [busy,setBusy]=useState(false),[error,setError]=useState('')
 async function submit(event:React.FormEvent<HTMLFormElement>){
  event.preventDefault()
  const fields=Object.fromEntries(new FormData(event.currentTarget))
  setBusy(true);setError('')
  try{
   let requestId=sessionStorage.getItem('customer-setup-request')
   if(!requestId){requestId=crypto.randomUUID();sessionStorage.setItem('customer-setup-request',requestId)}
   const csrf=await fetch('/api/auth/csrf');if(!csrf.ok)throw Error('Please sign in again.')
   const {token}=await csrf.json()
   const response=await fetch('/api/settings/customers',{method:'POST',headers:{'content-type':'application/json','x-csrf-token':token},body:JSON.stringify({...fields,request_id:requestId})})
   const result=await response.json()
   if(!response.ok)throw Error(result.error?.message||result.detail||'Could not create customer. Please retry.')
   sessionStorage.removeItem('customer-setup-request');window.location.href='/settings/onboarding'
  }catch(e){setError(e instanceof Error?e.message:'Could not create customer.')}finally{setBusy(false)}
 }
 return <section className="bv-card"><h2>Add customer profile</h2><p>Create a separate customer workspace with private document storage. You will be its owner; invite other users from Workspace access after setup.</p><form className="account-form" onSubmit={submit}>
 <label>Customer legal name<input name="legal_name" required maxLength={200} disabled={busy}/></label>
 <label>Customer GSTIN (optional)<input name="gstin" maxLength={15} disabled={busy}/></label>
 <label>Customer website (optional)<input name="website_url" type="url" placeholder="https://example.com" maxLength={2000} disabled={busy}/></label>
 <p className="wide muted">The customer profile and private document storage are set up automatically. GSTIN format validation does not verify government registration.</p>
 <div className="wide"><button className="button primary" disabled={busy}>{busy?'Setting up customer…':'Create customer profile'}</button></div>
 </form>{error&&<p role="alert">{error}</p>}</section>
}
