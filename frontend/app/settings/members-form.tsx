'use client'
import {FormEvent,useEffect,useState} from 'react'

export default function MembersForm(){
 const [data,setData]=useState<any>(null),[error,setError]=useState(''),[message,setMessage]=useState(''),[busy,setBusy]=useState(false)
 async function load(){const response=await fetch('/api/settings/members');const result=await response.json();if(!response.ok)throw Error(result.error?.message||result.detail||'Could not load workspace access.');setData(result)}
 useEffect(()=>{load().catch(e=>setError(e.message))},[])
 async function mutation(path:string,method:string,body?:object){
  setBusy(true);setError('');setMessage('')
  try{const csrf=await fetch('/api/auth/csrf');const {token}=await csrf.json();const response=await fetch(path,{method,headers:{'content-type':'application/json','x-csrf-token':token},body:body?JSON.stringify(body):undefined});const result=await response.json();if(!response.ok)throw Error(result.error?.message||result.detail||'Could not update access.');setMessage(method==='POST'?'Invitation queued for email delivery.':'Access revoked.');await load()}
  catch(e){setError(e instanceof Error?e.message:'Could not update access.')}finally{setBusy(false)}
 }
 function invite(event:FormEvent<HTMLFormElement>){event.preventDefault();mutation('/api/settings/invitations','POST',Object.fromEntries(new FormData(event.currentTarget)))}
 return <section className="bv-card"><h2>Workspace access</h2>{error&&<p role="alert" className="error">{error}</p>}{message&&<p role="status">{message}</p>}
 {!data&&!error&&<p role="status">Loading workspace access…</p>}{data&&<>
 <form className="account-form" onSubmit={invite}><label>Invitation email<input name="email" type="email" autoComplete="email" required maxLength={254}/></label><label>Access role<select name="role" defaultValue="viewer"><option value="viewer">Read-only viewer</option><option value="accountant">Accountant / tax preparer</option><option value="tax_admin">Tax administrator</option></select></label><div className="wide"><button className="button primary" disabled={busy}>Send invitation</button><p>Invitations expire after 48 hours. The recipient must sign in with this verified email address.</p></div></form>
 <h3>Current members</h3><div className="table-scroll"><table><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Actions</th></tr></thead><tbody>{data.members.map((member:any)=><tr key={member.user_id}><td>{member.full_name}</td><td>{member.email}</td><td>{member.access_role}</td><td>{member.access_role!=='owner'&&<button className="button secondary" disabled={busy} onClick={()=>{if(window.confirm(`Revoke workspace access for ${member.email}?`))mutation('/api/settings/members/'+encodeURIComponent(member.user_id),'DELETE')}}>Revoke access</button>}</td></tr>)}</tbody></table></div>
 <h3>Invitations</h3>{!data.invitations.length?<p>No invitations yet.</p>:<div className="table-scroll"><table><thead><tr><th>Email</th><th>Role</th><th>Status</th><th>Actions</th></tr></thead><tbody>{data.invitations.map((invitation:any)=><tr key={invitation.id}><td>{invitation.email}</td><td>{invitation.role}</td><td>{invitation.accepted_at?'Accepted':invitation.revoked_at?'Revoked':new Date(invitation.expires_at).getTime()<Date.now()?'Expired':'Pending'}</td><td>{!invitation.accepted_at&&!invitation.revoked_at&&<button className="button secondary" disabled={busy} onClick={()=>mutation('/api/settings/invitations/'+encodeURIComponent(invitation.id),'DELETE')}>Revoke invitation</button>}</td></tr>)}</tbody></table></div>}
 </>}</section>
}
