"use client"
import { FormEvent, useState } from 'react'
import { useRouter } from 'next/navigation'
export default function Login() {
  const router=useRouter(); const [email,setEmail]=useState('admin@local'); const [password,setPassword]=useState('ChangeMe123!'); const [error,setError]=useState(''); const [busy,setBusy]=useState(false)
  async function submit(e:FormEvent){e.preventDefault();setBusy(true);setError('');const r=await fetch('/api/auth/login',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({email,password})});setBusy(false);if(!r.ok){setError((await r.json()).detail||'Login failed');return}router.push('/')}
  return <main className="auth"><div className="auth-card"><div className="brand-mark">BV</div><p className="eyebrow">BIGQUERY FINANCE</p><h1>Welcome back</h1><p className="muted">GST bills, vouchers and evidence in one workspace.</p><form onSubmit={submit}><label>Email<input value={email} onChange={e=>setEmail(e.target.value)} type="email" required /></label><label>Password<input value={password} onChange={e=>setPassword(e.target.value)} type="password" required /></label>{error&&<div className="error">{error}</div>}<button disabled={busy}>{busy?'Signing in…':'Sign in'}</button></form><small>Change the bootstrap password before production deployment.</small></div></main>
}
