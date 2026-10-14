'use client'
import PasswordInput from '../password-input'
import Link from 'next/link'
import {FormEvent, useState} from 'react'
import {useRouter} from 'next/navigation'

export default function Register() {
 const router=useRouter(),[busy,setBusy]=useState(false),[error,setError]=useState(''),[password,setPassword]=useState('')
 const passwordReady=password.length>=12&&/[A-Z]/.test(password)&&/[a-z]/.test(password)&&/[0-9]/.test(password)&&new TextEncoder().encode(password).length<=72
 async function submit(event:FormEvent<HTMLFormElement>){
  event.preventDefault();const values=Object.fromEntries(new FormData(event.currentTarget))
  if(values.password!==values.confirm){setError('Passwords do not match.');return}
  setBusy(true);setError('')
  try{const response=await fetch('/api/auth/register',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(values)});const result=await response.json();if(!response.ok)throw Error(result.error?.message||result.detail?.message||result.detail||'Registration failed.');router.push('/verify-email');router.refresh()}
  catch(error){setError(error instanceof Error?error.message:'Registration failed.')}
  finally{setBusy(false)}
 }
 return <main className="auth"><div className="auth-card"><div className="brand-mark">BV</div><h1>Create your account</h1><p className="muted">Register your business to upload and review bills.</p><form onSubmit={submit}>
  <label>Full name<input name="full_name" autoComplete="name" required maxLength={120}/></label>
  <label>Email<input name="email" type="email" autoComplete="email" required maxLength={254}/></label>
  <label>Country code<input name="country_code" type="tel" autoComplete="tel-country-code" defaultValue="+91" required pattern="\+[1-9][0-9]{0,2}" maxLength={4}/></label>
  <label>Mobile number<input name="mobile_number" type="tel" inputMode="numeric" autoComplete="tel-national" required pattern="[0-9]{4,14}" maxLength={14}/></label>
  <label>Business name<input name="business_name" required maxLength={200}/></label>
  <label>Business GSTIN (optional)<input name="gstin" minLength={15} maxLength={15}/></label>
  <label>Password<PasswordInput name="password" value={password} onChange={event=>setPassword(event.target.value)} autoComplete="new-password" required minLength={12} aria-describedby="password-guidance"/></label>
  <small>At least 12 characters, including uppercase, lowercase and a number. Maximum 72 UTF-8 bytes.</small>
  <p id="password-guidance" role="status">{password?(passwordReady?'Password meets the requirements.':'Add the required length and character types.'):''}</p>
  <label>Confirm password<PasswordInput name="confirm"  autoComplete="new-password" required minLength={12}/></label>
  {error&&<p role="alert" className="error">{error}</p>}<button disabled={busy}>{busy?'Creating account…':'Register'}</button>
 </form><p>Already registered? <Link href="/login">Sign in</Link></p></div></main>
}
