"use client"
import PasswordInput from './password-input'
import { FormEvent, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
export default function LoginForm({admin=false}:{admin?:boolean}) {
  const router=useRouter(); const [email,setEmail]=useState(''); const [password,setPassword]=useState(''); const [error,setError]=useState(''); const [busy,setBusy]=useState(false)
  async function submit(e:FormEvent){e.preventDefault();setBusy(true);setError('');try{const r=await fetch(admin?'/api/auth/admin/login':'/api/auth/login',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({email,password})});const text=await r.text();let data:any={};try{data=text?JSON.parse(text):{}}catch{}if(!r.ok){setError(data.error?.message||data.detail||data.message||'Login failed ('+r.status+')');return}router.push(data.must_change_password?'/settings':data.access_mode==='admin'?'/admin/workspace':'/gst/workspace')}catch{setError('Sign-in is temporarily unavailable. Please try again.')}finally{setBusy(false)}}
  return <main className="auth"><div className="auth-card"><div className="brand-mark">BV</div><p className="eyebrow">BILLS & VOUCHERS</p><h1>{admin?'Administrator sign-in':'Welcome back'}</h1><p className="muted">{admin?'For separately provisioned platform administrators.':'Sign in to your business workspace.'}</p><form onSubmit={submit}><label>Email<input value={email} onChange={e=>setEmail(e.target.value)} type="email" autoComplete="username" required /></label><label>Password<PasswordInput autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)} required /></label>{error&&<div className="error">{error}</div>}<button disabled={busy}>{busy?'Signing in…':'Sign in'}</button></form><p><Link href="/forgot-password">Forgot password?</Link> ? <Link href="/verify-email">Verify email</Link></p><p>{admin?<Link href="/login">Client sign-in</Link>:<>New here? <Link href="/register">Create an account</Link></>}</p></div></main>
}


