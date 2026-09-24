"use client"

import { FormEvent, useState } from "react"
import { useRouter } from "next/navigation"

export default function Login() {
  const router = useRouter()
  const [email, setEmail] = useState("ai@aidirac.com")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError("")
    try {
      const response = await fetch("/api/auth/login", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ email, password }) })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) { setError(data.error?.message || data.detail || "Login failed"); return }
      router.push(data.must_change_password ? "/settings" : "/")
    } catch { setError("Finance backend is unavailable.") } finally { setBusy(false) }
  }
  return <main className="auth"><div className="auth-card"><div className="brand-mark">BV</div><p className="eyebrow">BIGQUERY FINANCE</p><h1>Welcome back</h1><p className="muted">GST bills, vouchers and evidence in one workspace.</p><form onSubmit={submit}><label>Email<input value={email} onChange={(event) => setEmail(event.target.value)} type="email" required /></label><label>Password<input value={password} onChange={(event) => setPassword(event.target.value)} type="password" required /></label>{error && <div className="error">{error}</div>}<button disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button></form><small>Use your registered email.</small></div></main>
}
