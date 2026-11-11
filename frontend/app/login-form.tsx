"use client"
import PasswordInput from './password-input'
import { FormEvent, useState } from 'react'
import Link from 'next/link'
export default function LoginForm({admin=false}:{admin?:boolean}) {
  const [email,setEmail]=useState(''); const [password,setPassword]=useState(''); const [error,setError]=useState(''); const [busy,setBusy]=useState(false)
  const [verificationRequired,setVerificationRequired]=useState(false),[message,setMessage]=useState('')
  async function submit(e:FormEvent){
    e.preventDefault();if(busy)return;setBusy(true);setError('');setMessage('');setVerificationRequired(false)
    try{
      const r=await fetch(admin?'/api/auth/admin/login':'/api/auth/login',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({email,password}),signal:AbortSignal.timeout(45000)})
      const data=await r.json().catch(()=>({}))
      if(!r.ok){
        setVerificationRequired(r.status===403&&(data.error?.code==='email_verification_required'||/verify your email/i.test(String(data.detail||''))))
        setError(data.error?.message||data.detail?.message||data.detail||data.message||'Login failed ('+r.status+')');return
      }
      // Start the authenticated workspace from the fresh cookie, including when
      // the router has cached a previous signed-out workspace redirect.
      window.location.assign(data.must_change_password?'/settings':data.access_mode==='admin'?'/admin/workspace':'/gst/workspace')
    }catch{setError('Sign-in could not be completed. Please try again. Your entered details have been kept.')}
    finally{setBusy(false)}
  }
  async function resend(){
    if(busy)return;setBusy(true);setError('');setMessage('')
    try{
      const r=await fetch('/api/auth/request-link',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({email,purpose:'verify'}),signal:AbortSignal.timeout(45000)})
      const data=await r.json().catch(()=>({}))
      if(!r.ok)throw Error(data.error?.message||data.detail?.message||data.detail||'The verification request could not be completed. Please retry.')
      setMessage(data.message||'If this account can receive a link, an email will arrive shortly.')
    }catch(err){setError(err instanceof Error?err.message:'Please try again.')}
    finally{setBusy(false)}
  }
  return <main className="auth"><div className="auth-card"><div className="brand-mark">BV</div><p className="eyebrow">BILLS & VOUCHERS</p><h1>{admin?'Administrator sign-in':'Welcome back'}</h1><p className="muted">{admin?'For separately provisioned platform administrators.':'Sign in to your business workspace.'}</p><form onSubmit={submit}><label>Email<input value={email} onChange={e=>{setEmail(e.target.value);setVerificationRequired(false);setMessage('')}} type="email" autoComplete="username" required /></label><label>Password<PasswordInput autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)} required /></label>{error&&<div role="alert" className="error">{error}</div>}{message&&<p role="status">{message}</p>}<button disabled={busy}>{busy?'Signing in…':'Sign in'}</button>{verificationRequired&&<><button type="button" disabled={busy} onClick={resend}>Resend verification email</button><p>Open the newest verification email within 30 minutes, verify your address, then sign in. Check your spam folder if it does not arrive.</p></>}</form><p><Link href="/forgot-password">Forgot password?</Link> · <Link href="/verify-email">Verify email</Link></p><p>{admin?<Link href="/login">Client sign-in</Link>:<>New here? <Link href="/register">Create an account</Link></>}</p></div></main>
}


