'use client'
import {useState} from 'react'

export default function LogoUpload({editable}:{editable:boolean}){
 const [busy,setBusy]=useState(false),[message,setMessage]=useState(''),[revision,setRevision]=useState(0),[missing,setMissing]=useState(false)
 async function upload(file:File|undefined){
  if(!file)return
  if(file.size>2*1024*1024){setMessage('Choose a logo up to 2 MB.');return}
  setBusy(true);setMessage('')
  try{const csrf=await fetch('/api/auth/csrf');const {token}=await csrf.json();const body=new FormData();body.append('file',file);const response=await fetch('/api/settings/profile/logo',{method:'POST',headers:{'x-csrf-token':token},body});const result=await response.json();if(!response.ok)throw Error(result.error?.message||result.detail||'Logo upload failed.');setMissing(false);setRevision(Date.now());setMessage('Logo saved.');window.dispatchEvent(new Event('workspace-logo-changed'))}
  catch(error){setMessage((error as Error).message)}finally{setBusy(false)}
 }
 async function remove(){
  if(!window.confirm('Remove the current business logo?'))return
  setBusy(true);setMessage('')
  try{const csrf=await fetch('/api/auth/csrf');const {token}=await csrf.json();const response=await fetch('/api/settings/profile/logo',{method:'DELETE',headers:{'x-csrf-token':token}});const result=await response.json();if(!response.ok)throw Error(result.error?.message||result.detail||'Could not remove the logo.');setMissing(true);setMessage('Logo removed.');window.dispatchEvent(new Event('workspace-logo-changed'))}
  catch(error){setMessage((error as Error).message)}finally{setBusy(false)}
 }
 return <section className="bv-card"><h2>Business logo</h2>{!missing&&<img src={`/api/settings/profile/logo?v=${revision}`} alt="Business logo" width={160} style={{objectFit:'contain',maxHeight:120}} onError={()=>setMissing(true)}/>}<p>PNG, JPEG or WebP, up to 2 MB.</p>{editable&&<label className="button secondary">{busy?'Uploading…':'Upload logo'}<input className="visually-hidden" aria-label="Upload logo" type="file" accept="image/png,image/jpeg,image/webp" disabled={busy} onChange={event=>{upload(event.target.files?.[0]);event.target.value=''}}/></label>}{editable&&!missing&&<button type="button" className="button secondary" disabled={busy} onClick={remove}>Remove logo</button>}{message&&<p role="status">{message}</p>}</section>
}
