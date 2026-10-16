'use client'
import {FormEvent, useState} from 'react'
import Link from 'next/link'

export default function MobileVerification({mobile,verified,available=false}:{mobile:string;verified:boolean;available?:boolean}) {
 const [challenge,setChallenge]=useState(''),[code,setCode]=useState(''),[busy,setBusy]=useState(false),[message,setMessage]=useState(''),[error,setError]=useState('')
 async function post(path:string,body:object){
  const csrf=await fetch('/api/auth/csrf');if(!csrf.ok)throw Error('Please sign in again.')
  const {token}=await csrf.json()
  const result=await fetch(path,{method:'POST',headers:{'content-type':'application/json','x-csrf-token':token},body:JSON.stringify(body)})
  const data=await result.json();if(!result.ok)throw Error(data.error?.message||data.detail||'Verification failed.')
  return data
 }
 async function start(){setBusy(true);setError('');setMessage('');try{const data=await post('/api/auth/mobile/start',{});setChallenge(data.challenge_id);setCode('');setMessage('Code sent. It expires in 10 minutes.')}catch(e){setError(e instanceof Error?e.message:'Could not send code.')}finally{setBusy(false)}}
 async function check(event:FormEvent){event.preventDefault();setBusy(true);setError('');try{await post('/api/auth/mobile/check',{challenge_id:challenge,code});window.location.reload()}catch(e){setError(e instanceof Error?e.message:'Could not verify code.')}finally{setBusy(false)}}
 return <section className="bv-card settings-card"><h2>Mobile verification</h2><p className="settings-intro">Verify and manage the mobile number linked to your account.</p>
 <dl className="settings-rows"><div><dt>Mobile number</dt><dd>{mobile||'Not provided'}</dd></div><div><dt>Verification status</dt><dd><span className="settings-badge">{verified?'Verified':'Unverified'}</span></dd></div></dl>
 {!verified&&!available&&<div className="settings-notice" role="status">SMS verification is currently unavailable. Your number remains unverified.</div>}
 <p className="settings-note">Changing the number will require verification again.</p>
 {!verified&&!available&&<div className="settings-actions"><Link className="button secondary" href="/help">Contact Support</Link></div>}
 {!verified&&available&&<><button type="button" className="button primary" disabled={busy||!mobile} onClick={start}>{busy?'Please wait…':challenge?'Send another code':'Send verification code'}</button>
 {challenge&&<form onSubmit={check} className="account-form"><label>Verification code<input value={code} onChange={e=>setCode(e.target.value)} autoComplete="one-time-code" inputMode="numeric" pattern="[0-9]{4,10}" required maxLength={10}/></label><button className="button primary" disabled={busy}>Verify mobile</button></form>}</>}
 {message&&<p role="status">{message}</p>}{error&&<p role="alert" className="error">{error}</p>}</section>
}
