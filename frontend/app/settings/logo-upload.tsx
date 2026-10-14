'use client'
import {useState} from 'react'

export default function LogoUpload({editable}:{editable:boolean}){
 const [busy,setBusy]=useState(false),[message,setMessage]=useState(''),[revision,setRevision]=useState(0),[missing,setMissing]=useState(false)
 async function upload(file:File|undefined){
  if(!file)return
  if(file.size>2*1024*1024){setMessage('Choose a logo up to 2 MB.');return}
  setBusy(true);setMessage('')
  try{const csrf=await fetch('/api/auth/csrf');const {token}=await csrf.json();const body=new FormData();body.append('file',file);const response=await fetch('/api/settings/profile/logo',{method:'POST',headers:{'x-csrf-token':token},body});const result=await response.json();if(!response.ok)throw Error(result.error?.message||result.detail||'Logo upload failed.');setMissing(false);setRevision(Date.now());setMessage('Logo saved.')}
  catch(error){setMessage((error as Error).message)}finally{setBusy(false)}
 }
 return <section className="bv-card"><h2>Business logo</h2>{!missing&&<img src={`/api/settings/profile/logo?v=${revision}`} alt="Business logo" width={160} style={{objectFit:'contain',maxHeight:120}} onError={()=>setMissing(true)}/>}<p>PNG, JPEG or WebP, up to 2 MB.</p>{editable&&<label className="button secondary">{busy?'Uploading…':'Upload logo'}<input className="visually-hidden" aria-label="Upload logo" type="file" accept="image/png,image/jpeg,image/webp" disabled={busy} onChange={event=>{upload(event.target.files?.[0]);event.target.value=''}}/></label>}{message&&<p role="status">{message}</p>}</section>
}
