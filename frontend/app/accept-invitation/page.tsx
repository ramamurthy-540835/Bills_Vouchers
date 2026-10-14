'use client'
import Link from 'next/link'
import {useEffect,useState} from 'react'

export default function AcceptInvitation(){
 const [token,setToken]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState(''),[accepted,setAccepted]=useState(false)
 useEffect(()=>{setToken(new URLSearchParams(window.location.hash.slice(1)).get('token')||'');window.history.replaceState(null,'',window.location.pathname)},[])
 async function accept(){setBusy(true);setError('');try{const csrf=await fetch('/api/auth/csrf');if(!csrf.ok)throw Error('Sign in with the invited email, verify it, then return to this tab.');const {token:csrfToken}=await csrf.json();const response=await fetch('/api/settings/invitations/accept',{method:'POST',headers:{'content-type':'application/json','x-csrf-token':csrfToken},body:JSON.stringify({token})});const result=await response.json();if(!response.ok)throw Error(result.error?.message||result.detail||'Could not accept invitation.');setAccepted(true);setToken('')}catch(e){setError(e instanceof Error?e.message:'Could not accept invitation.')}finally{setBusy(false)}}
 return <main className="auth"><div className="auth-card"><h1>Workspace invitation</h1><p>Use the verified email address that received this invitation.</p>{accepted?<><p role="status">Invitation accepted.</p><Link className="button primary" href="/gst/workspace">Open workspace</Link></>:<><p><Link href="/login" target="_blank" rel="noopener">Sign in in a new tab</Link> or <Link href="/register" target="_blank" rel="noopener">create an account</Link>, then return here.</p><button disabled={busy||!token} onClick={accept}>{busy?'Accepting…':'Accept invitation'}</button>{!token&&<p>Open the original link from your invitation email.</p>}</>}{error&&<p role="alert" className="error">{error}</p>}</div></main>
}
