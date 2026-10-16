"use client"
import {useId,useState} from 'react'

function normalizeWebsite(value:string){
 const trimmed=value.trim()
 if(!trimmed||trimmed.length>2000||/[\s\\]/u.test(trimmed))throw Error('Enter a valid website URL without spaces, such as https://www.example.com.')
 let url:URL
 try{url=new URL(trimmed.includes('://')?trimmed:`https://${trimmed}`)}catch{throw Error('Enter a valid website URL, such as https://www.example.com.')}
 const labels=url.hostname.split('.')
 if(!['http:','https:'].includes(url.protocol)||url.username||url.password||!['','80','443'].includes(url.port)||url.hostname.length>253||labels.length<2||['local','localhost','internal'].includes(labels.at(-1)!)||/^\d+$/.test(labels.at(-1)!)||labels.some(label=>!/^([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)$/.test(label)))throw Error('Use an http:// or https:// public website domain without login credentials or a custom port.')
 return url.href
}
export default function WebsiteEditor({profile,clientId,editable,onSaved}:{profile:any;clientId:string;editable:boolean;onSaved:(profile:any)=>void}){
 const id=useId()
 let initial='';try{if(profile.website_url)initial=normalizeWebsite(profile.website_url)}catch{}
 const [saved,setSaved]=useState(initial),[value,setValue]=useState(initial),[editing,setEditing]=useState(!initial),[busy,setBusy]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState(''),[needsRefresh,setNeedsRefresh]=useState(false)
 async function refresh(){
  const response=await fetch('/api/settings/account',{cache:'no-store'})
  if(!response.ok)throw Error('Website saved, but the updated profile could not be loaded. Retry loading it before making further changes.')
  const data=await response.json()
  if(data.client_id!==clientId)throw Error('The selected business changed. Reload this page before continuing.')
  const next=normalizeWebsite(data.profile.website_url)
  onSaved(data.profile);setSaved(next);setValue(next);setEditing(false);setNeedsRefresh(false);setMessage('Company website saved successfully.')
 }
 async function save(event:React.FormEvent){
  event.preventDefault();setError('');setMessage('')
  let normalized:string
  try{normalized=normalizeWebsite(value)}catch(e){setError((e as Error).message);return}
  setBusy(true)
  try{
   const csrf=await fetch('/api/auth/csrf');if(!csrf.ok)throw Error('Please sign in again.')
   const {token}=await csrf.json()
   const response=await fetch('/api/settings/profile',{method:'POST',headers:{'content-type':'application/json','x-csrf-token':token},body:JSON.stringify({client_id:clientId,profile_id:profile.profile_id,website_url:normalized})})
   const result=await response.json()
   if(!response.ok)throw Error(result.error?.message||result.detail?.message||(typeof result.detail==='string'?result.detail:'Could not save the website. Please retry.'))
   setNeedsRefresh(true);await refresh()
  }catch(e){setError(e instanceof Error?e.message:'Could not save the website. Please retry.')}finally{setBusy(false)}
 }
 return <div className="settings-subsection website-editor"><h3>Company Website</h3><p className="settings-note">Add or update your company website.</p>
 <span className="settings-badge">{saved?'Saved':'Not saved'}</span>
 {saved&&<div className="website-saved"><span>Saved Website</span><p>{saved}</p></div>}
 {editable&&editing?<form onSubmit={save} noValidate><label htmlFor={id}>Website URL</label><input id={id} type="text" inputMode="url" autoComplete="url" placeholder="https://www.example.com" value={value} maxLength={2000} disabled={busy||needsRefresh} aria-invalid={Boolean(error)} aria-describedby={error?`${id}-error`:undefined} onChange={event=>{setValue(event.target.value);setError('')}}/>
 <div className="settings-actions"><button className="button primary" disabled={busy||needsRefresh}>{busy?'Saving...':'Save Website'}</button><button type="button" className="button primary" disabled={busy||needsRefresh} onClick={()=>{setValue(saved);setEditing(!saved);setError('');setMessage('')}}>Cancel</button></div></form>:<div className="settings-actions">{editable&&<button type="button" className="button primary" onClick={()=>{setEditing(true);setError('');setMessage('')}}>Edit Website</button>}{saved&&<a className="button primary" href={saved} target="_blank" rel="noopener noreferrer">Open Website</a>}</div>}
 {needsRefresh&&<button type="button" className="button primary" disabled={busy} onClick={async()=>{setBusy(true);setError('');try{await refresh()}catch(e){setError((e as Error).message)}finally{setBusy(false)}}}>Reload saved website</button>}
 {error&&<p id={`${id}-error`} role="alert">{error}</p>}{message&&<p role="status">{message}</p>}
 <p className="settings-note">Saving a website does not verify ownership.</p></div>
}
