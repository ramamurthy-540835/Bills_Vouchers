import {backendFetch} from '../../lib/backend-fetch'
import {headers} from 'next/headers'
import {redirect} from 'next/navigation'
import Workspace from '../workspace'
import AccountForm from './account-form'
import OnboardingForm from './onboarding-form'
import MembersForm from './members-form'
import CustomerForm from './customer-form'
import Link from 'next/link'
import HelpContent from './help-content'
export default async function AccountPage({section}:{section:string}){
 const response=await backendFetch(`${process.env.BACKEND_URL||'http://localhost:8000'}/api/settings/account`,{headers:{cookie:(await headers()).get('cookie')||''},cache:'no-store'})
 if(response.status===401)redirect('/login')
 if(section==='notifications')redirect('/help')
 if(section==='profile'&&!response.ok&&response.status!==403)return <main className="auth"><section className="auth-card"><h1>Business Profile</h1><p role="alert">Business information could not be loaded. Please retry.</p><a className="button primary" href="/settings/profile">Retry</a></section></main>
 const data=response.ok?await response.json():null
 const required:Record<string,string>={members:'manage_members',customers:'create_customer',onboarding:'edit_profile',administration:'platform_admin'}
 if(!data||required[section]&&!data.permissions?.includes(required[section]))return <main className="auth"><section className="auth-card"><h1>Access denied</h1><p>You do not have permission to open this page.</p><Link href="/gst/workspace">Return to your workspace</Link></section></main>
 let administration:any=null
 if(section==='administration'){
  const result=await backendFetch(`${process.env.BACKEND_URL||'http://localhost:8000'}/api/admin/workspace`,{headers:{cookie:(await headers()).get('cookie')||''},cache:'no-store'})
  if(!result.ok)return <main className="auth"><h1>Administration unavailable</h1><p>Your access could not be verified. Refresh or sign in again.</p></main>
  administration=await result.json()
 }
 return <Workspace view={section} initial={data}>
 {section==='onboarding'?<OnboardingForm data={data}/>:section==='members'?<MembersForm/>:section==='customers'?<CustomerForm userId={data.user.id}/>:section==='help'?<HelpContent permissions={data.permissions||[]}/>:section==='administration'?<section className="bv-card"><h2>Selected workspace administration</h2><p>This view covers only your selected authorized business. Platform access does not grant access to all customer data.</p><h3>Workspace memberships</h3><div className="table-scroll"><table><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th></tr></thead><tbody>{administration.members.map((member:any,index:number)=><tr key={index}><td>{member.full_name}</td><td>{member.email}</td><td>{member.access_role}</td><td>{member.is_active?'Active':'Revoked'}</td></tr>)}</tbody></table></div><h3>Recent profile activity</h3>{administration.events.length?<ul>{administration.events.map((event:any,index:number)=><li key={index}>{event.action} — {event.created_at}</li>)}</ul>:<p>No profile activity recorded.</p>}</section>:<AccountForm data={data} section={section}/>}
 </Workspace>
}
