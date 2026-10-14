'use client'
import Link from 'next/link'
import {FormEvent, useState} from 'react'
import {useRouter} from 'next/navigation'

export default function Register() {
 const router=useRouter(),[busy,setBusy]=useState(false),[error,setError]=useState('')
 async function submit(event:FormEvent<HTMLFormElement>){
  event.preventDefault();const values=Object.fromEntries(new FormData(event.currentTarget))
  if(values.password!==values.confirm){setError('Passwords do not match.');return}
  setBusy(true);setError('')
  try{const response=await fetch('/api/auth/register',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(values)});const result=await response.json();if(!response.ok)throw Error(result.error?.message||result.detail?.message||result.detail||'Registration failed.');router.push('/');router.refresh()}
  catch(error){setError(error instanceof Error?error.message:'Registration failed.')}
  finally{setBusy(false)}
 }
 return <main className="auth"><div className="auth-card"><div className="brand-mark">BV</div><h1>Create your account</h1><p className="muted">Register your business to upload and review bills.</p><form onSubmit={submit}>
  <label>Your name<input name="full_name" autoComplete="name" required maxLength={120}/></label>
  <label>Email<input name="email" type="email" autoComplete="email" required maxLength={254}/></label>
  <label>Business name<input name="business_name" required maxLength={200}/></label>
  <label>Business GSTIN<input name="gstin" required minLength={15} maxLength={15}/></label>
  <label>Password<input name="password" type="password" autoComplete="new-password" required minLength={12}/></label>
  <small>At least 12 characters, including uppercase, lowercase and a number.</small>
  <label>Confirm password<input name="confirm" type="password" autoComplete="new-password" required minLength={12}/></label>
  {error&&<p role="alert" className="error">{error}</p>}<button disabled={busy}>{busy?'Creating account…':'Register'}</button>
 </form><p>Already registered? <Link href="/login">Sign in</Link></p></div></main>
}
