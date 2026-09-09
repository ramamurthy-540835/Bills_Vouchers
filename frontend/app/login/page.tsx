"use client"
import { FormEvent, useState } from 'react'
import { useRouter } from 'next/navigation'
export default function Login() {
  const router=useRouter(); const [email,setEmail]=useState('stephenraj040899@gmail.com'); const [password,setPassword]=useState(''); const [error,setError]=useState(''); const [busy,setBusy]=useState(false)
  async function submit(e:FormEvent){e.preventDefault();setBusy(true);setError('');try{const r=await fetch('/api/auth/login',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({email,password})});const text=await r.text();let data:any={};try{data=text?JSON.parse(text):{}}catch{}if(!r.ok){setError(data.detail||data.message||'Login failed ('+r.status+')');return}router.push('/')}catch{setError('Finance backend is unavailable. Start the API and try again.')}finally{setBusy(false)}}
  return <main className="auth"><div className="auth-card"><div className="brand-mark">BV</div><p className="eyebrow">BIGQUERY FINANCE</p><h1>Welcome back</h1><p className="muted">GST bills, vouchers and evidence in one workspace.</p><form onSubmit={submit}><label>Email or username<input value={email} onChange={e=>setEmail(e.target.value)} type="text" required /></label><label>Password<input value={password} onChange={e=>setPassword(e.target.value)} type="password" required /></label>{error&&<div className="error">{error}</div>}<button disabled={busy}>{busy?'Signing in…':'Sign in'}</button></form><small>Use stephenraj or your registered email.</small></div></main>
}
