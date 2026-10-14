'use client'

import Link from 'next/link'
import {FormEvent, useEffect, useState} from 'react'
import PasswordInput from './password-input'

export default function IdentityForm({mode}:{mode:'verify'|'reset'|'request'}) {
 const [token,setToken]=useState(''), [busy,setBusy]=useState(false), [message,setMessage]=useState(''), [error,setError]=useState(''), [complete,setComplete]=useState(false)
 useEffect(()=>{
  const value=new URLSearchParams(window.location.hash.slice(1)).get('token')||''
  setToken(value)
  if(value)window.history.replaceState(null,'',window.location.pathname)
 },[])
 async function submit(event:FormEvent<HTMLFormElement>){
  event.preventDefault()
  const values=Object.fromEntries(new FormData(event.currentTarget))
  const consuming=Boolean(token)&&mode!=='request'
  if(consuming&&mode==='reset'&&values.password!==values.confirm){setError('Passwords do not match.');return}
  setBusy(true);setError('');setMessage('')
  try{
   const path=consuming?(mode==='verify'?'verify-email':'reset-password'):'request-link'
   const response=await fetch('/api/auth/'+path,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({...values,token,purpose:mode==='verify'?'verify':'reset'})})
   const result=await response.json()
   if(!response.ok)throw Error(result.error?.message||result.detail||'Please try again.')
   setMessage(result.message);if(consuming){setComplete(true);setToken('')}
  }catch(err){setError(err instanceof Error?err.message:'Please try again.')}
  finally{setBusy(false)}
 }
 return <main className="auth"><div className="auth-card"><h1>{mode==='verify'?'Verify your email':mode==='reset'?'Reset password':'Forgot password'}</h1>
  <p>{mode==='verify'?'Check your inbox for a verification link. You must verify your email before signing in.':'Request a single-use recovery link using your account email.'}</p>
  {!complete&&<form onSubmit={submit}>
   {!token&&<label>Email<input type="email" name="email" autoComplete="email" required maxLength={254}/></label>}
   {token&&mode==='reset'&&<><label>New password<PasswordInput name="password" autoComplete="new-password" required minLength={12}/></label><label>Confirm password<PasswordInput name="confirm" autoComplete="new-password" required minLength={12}/></label><p>Use 12 or more characters with uppercase, lowercase and a number, up to 72 UTF-8 bytes.</p></>}
   <button disabled={busy}>{busy?'Please wait…':token?(mode==='verify'?'Verify email':'Reset password'):'Send link'}</button>
  </form>}
  {error&&<p role="alert" className="error">{error}</p>}{message&&<p role="status">{message}</p>}
  <p><Link href="/login">Sign in</Link></p></div></main>
}
