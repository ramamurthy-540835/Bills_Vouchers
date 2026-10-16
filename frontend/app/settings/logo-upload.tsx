"use client"
import {useState,useRef,useEffect} from 'react'
import {Upload} from 'lucide-react'

export default function LogoUpload({editable,businessName='Your business'}:{editable:boolean;businessName?:string}){
 const [busy,setBusy]=useState(false),[message,setMessage]=useState(''),[error,setError]=useState('')
 const [revision,setRevision]=useState(0),[source,setSource]=useState<string|null>(null),[loading,setLoading]=useState(true),[loadError,setLoadError]=useState('')
 const picker=useRef<HTMLInputElement>(null),pending=useRef(false)
 const initials=businessName.trim().split(/\s+/).slice(0,2).map(word=>word[0]).join('').toUpperCase()
 useEffect(()=>{
  const controller=new AbortController();let objectUrl=''
  setLoading(true);setLoadError('');setSource(null)
  fetch(`/api/settings/profile/logo?v=${revision}`,{cache:'no-store',signal:controller.signal}).then(async response=>{
   if(response.status===404)return
   if(!response.ok)throw Error('Business logo could not be loaded. Please retry.')
   const blob=await response.blob();if(controller.signal.aborted)return
   objectUrl=URL.createObjectURL(blob);setSource(objectUrl)
  }).catch(e=>{if(!controller.signal.aborted)setLoadError(e.message)}).finally(()=>{if(!controller.signal.aborted)setLoading(false)})
  return()=>{controller.abort();if(objectUrl)URL.revokeObjectURL(objectUrl)}
 },[revision])
 async function mutate(file?:File){
  if(!editable||pending.current)return
  pending.current=true;setBusy(true);setError('');setMessage('')
  try{
   if(file){
    if(file.size>2*1024*1024)throw Error('Choose a logo up to 2 MB.')
    const bytes=new Uint8Array(await file.slice(0,12).arrayBuffer())
    const png=[137,80,78,71,13,10,26,10].every((value,index)=>bytes[index]===value)
    const jpeg=bytes[0]===255&&bytes[1]===216&&bytes[2]===255
    const webp=String.fromCharCode(...bytes.slice(0,4))==='RIFF'&&String.fromCharCode(...bytes.slice(8,12))==='WEBP'
    if(!png&&!jpeg&&!webp)throw Error('Choose a PNG, JPEG or WebP image. SVG and other formats are not supported.')
   }
   const csrf=await fetch('/api/auth/csrf');if(!csrf.ok)throw Error('Please sign in again before changing the logo.')
   const {token}=await csrf.json();const body=file?new FormData():undefined;if(file)body!.append('file',file)
   const response=await fetch('/api/settings/profile/logo',{method:file?'POST':'DELETE',headers:{'x-csrf-token':token},body})
   const result=await response.json()
   if(!response.ok)throw Error(result.error?.message||result.detail?.message||(typeof result.detail==='string'?result.detail:'Logo could not be saved. Please retry.'))
   setRevision(value=>value+1);setMessage(file?'Logo saved.':'Logo removed.');window.dispatchEvent(new Event('workspace-logo-changed'))
  }catch(e){setError(e instanceof Error?e.message:'Logo could not be saved. Please retry.')}finally{pending.current=false;setBusy(false)}
 }
 return <section className="bv-card business-logo-card" aria-label="Business Branding">
  <h2>Business Branding</h2><p className="business-logo-description">Manage the logo displayed for your business.</p>
  <div className="business-logo-row">
   <div className="business-logo-preview">{source?<img src={source} alt="Business logo" title={`${businessName} logo`} width={88} height={88} onError={()=>{setSource(null);setLoadError('Business logo could not be displayed. Please retry.')}}/>:<span aria-hidden="true">{initials||'B'}</span>}</div>
   <div className="business-logo-details"><h3>Business Logo</h3><p>{loading?'Loading logo...':loadError?'Logo unavailable':source?'Current business logo':'No logo uploaded'}</p><small>PNG, JPEG, WebP &middot; Maximum 2 MB</small>{!editable&&<small>Read-only access</small>}</div>
   <div className="business-logo-actions">{editable&&<><input ref={picker} hidden aria-label="Choose business logo" type="file" accept="image/png,image/jpeg,image/webp" disabled={busy||loading} onChange={event=>{const file=event.target.files?.[0];event.target.value='';if(file)void mutate(file)}}/><button type="button" className="button" disabled={busy||loading} onClick={()=>picker.current?.click()}><Upload size={16} aria-hidden="true"/>{busy?'Saving...':source?'Replace Logo':'Upload Logo'}</button>{source&&<button type="button" className="button" disabled={busy||loading} onClick={()=>{if(window.confirm('Remove the current business logo?'))void mutate()}}>Remove Logo</button>}</>}{loadError&&<button type="button" className="button" disabled={busy||loading} onClick={()=>setRevision(value=>value+1)}>Retry</button>}</div>
  </div>
  {loadError&&<p role="alert">{loadError}</p>}{error&&<p role="alert">{error}</p>}{message&&<p role="status">{message}</p>}
 </section>
}
