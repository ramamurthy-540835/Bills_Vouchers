'use client'
import {useEffect,useState} from 'react'
import Link from 'next/link'
import CompanyChecks from './company-checks'
import MobileVerification from './mobile-verification'
import PasswordInput from '../password-input'
import LogoUpload from './logo-upload'
import BusinessList from './business-list'
import WebsiteEditor from './website-editor'

export default function AccountForm({data,section}:{data:any;section:string}){
 const [name,setName]=useState(data.user.full_name||''),[mobile,setMobile]=useState(data.user.mobile_number||''),[profile,setProfile]=useState({...data.profile}),[password,setPassword]=useState(''),[confirm,setConfirm]=useState(''),[busy,setBusy]=useState(false),[message,setMessage]=useState('')
 useEffect(()=>{const key=`business-profile-saved:${data.client_id}`;if(section==='profile'&&sessionStorage.getItem(key)){sessionStorage.removeItem(key);setMessage('Business details saved successfully.')}},[data.client_id,section])
 const has=(permission:string)=>data.permissions?.includes(permission)
 async function save(path:string,body:any){setBusy(true);setMessage('');try{const csrf=await fetch('/api/auth/csrf');const {token}=await csrf.json();const response=await fetch(path,{method:'POST',headers:{'content-type':'application/json','x-csrf-token':token},body:JSON.stringify(body)});const result=await response.json();if(!response.ok)throw Error(result.error?.message||result.detail?.message||result.detail||'Could not save.');if(path==='/api/auth/password')window.location.href='/login';else {if(section==='profile')sessionStorage.setItem(`business-profile-saved:${data.client_id}`,'1');window.location.reload()}}catch(error){setMessage(error instanceof Error?error.message:'Could not save.')}finally{setBusy(false)}}
 const businessFields=[['legal_name','Legal name'],['trade_name','Trade name'],['contact_person','Contact person'],['contact_email','Contact email'],['contact_phone','Contact phone'],['principal_address','Registered address']]
 return <>{message&&<p role="status" className="notice">{message}</p>}
 {section==='me'&&<section className="bv-card"><h2>Your details</h2><form className="account-form" onSubmit={event=>{event.preventDefault();save('/api/settings/account',{full_name:name,mobile_number:mobile})}}>
 <label>Full Name<input required maxLength={120} value={name} onChange={event=>setName(event.target.value)}/></label>
 <label>Email Address<input readOnly type="email" value={data.user.email}/><small>{data.user.email_verified?'Email verified':'Email not verified'}</small></label>
 <label>Mobile Number<input type="tel" value={mobile} onChange={event=>setMobile(event.target.value)}/><small>{data.user.mobile_verified?'Mobile verified':'Mobile not verified'}. Changing this number requires verification again.</small></label>
 <div className="wide"><button className="button primary" disabled={busy}>Save personal details</button></div></form>
 <dl className="account-access"><dt>Assigned Business</dt><dd>{data.profile?.legal_name}</dd><dt>Account Role</dt><dd>{data.is_owner?'Business owner':data.user.role==='tax_admin'?'Accountant':data.user.role==='admin'?'Platform administrator':data.user.role==='viewer'?'Read-only viewer':'Business client'}</dd></dl><Link href="/settings/password">Change Password</Link></section>}
 {section==='account'&&<div className="settings-stack"><section className="bv-card settings-card"><h2>Account security</h2>
 <dl className="settings-rows"><div><dt>Login email</dt><dd>{data.user.email} <span className="settings-badge">{data.user.email_verified?'Verified':'Unverified'}</span></dd></div><div><dt>Email changes</dt><dd>Email changes require ownership verification and cannot be edited directly here.</dd></div><div><dt>Last sign-in</dt><dd>{data.user.last_sign_in?new Date(data.user.last_sign_in).toLocaleString('en-IN'):'Not yet recorded'}</dd></div></dl>
 <div className="settings-actions"><Link className="button secondary" href="/settings/me">Update personal contact details</Link><Link className="button secondary" href="/settings/password">Change Password</Link></div></section><MobileVerification mobile={data.user.mobile_number||''} verified={Boolean(data.user.mobile_verified)} available={Boolean(data.mobile_verification_available)}/></div>}
 {section==='password'&&<section className="bv-card"><h2>Change password</h2><form className="account-form" onSubmit={event=>{event.preventDefault();if(password!==confirm){setMessage('Passwords do not match.');return}save('/api/auth/password',{password})}}>
 <label>New password<PasswordInput required minLength={12} value={password} onChange={event=>setPassword(event.target.value)} autoComplete="new-password"/></label>
 <label>Confirm password<PasswordInput required value={confirm} onChange={event=>setConfirm(event.target.value)} autoComplete="new-password"/></label>
 <p className="wide">At least 12 characters, including uppercase, lowercase and a number. Changing your password signs you out.</p><div className="wide"><button className="button primary" disabled={busy}>Change password</button></div></form></section>}
 {section==='profile'&&<div className="business-profile-page"><BusinessList data={data}/><section className="bv-card" id="business-details"><h2>Business Information</h2><p>Update the identity and contact details for {data.profile?.legal_name||'your selected business'}.</p>
 <form id="business-details-form" className="account-form" onSubmit={event=>{event.preventDefault();save('/api/settings/profile',{client_id:data.client_id,profile_id:profile.profile_id,...Object.fromEntries(businessFields.map(([key])=>[key,profile[key]||'']))})}}>
 {[['Business identity',businessFields.slice(0,2)],['Address & Contact',businessFields.slice(2)]].map(([title,fields])=><fieldset className="wide business-fieldset" key={title as string}><legend>{title as string}</legend><div className="account-form">{(fields as string[][]).map(([key,label])=><label key={key}>{label}{key==='principal_address'?<textarea readOnly={!has('edit_profile')} placeholder="Not provided" value={profile[key]||''} onChange={event=>setProfile({...profile,[key]:event.target.value})}/>:<input readOnly={!has('edit_profile')} placeholder="Not provided" required={key==='legal_name'} type={key==='website_url'?'url':key==='contact_email'?'email':key==='contact_phone'?'tel':'text'} value={profile[key]||''} onChange={event=>setProfile({...profile,[key]:event.target.value})}/>}</label>)}</div></fieldset>)}
 </form></section>
 <section className="bv-card settings-card"><h2>Business Preferences</h2><p className="settings-intro">Manage registration details and workspace preferences for the selected business.</p>
 <dl className="settings-rows">{[['Business type',profile.constitution],['State code',profile.state_code],['GST registration type',profile.registration_type],['Filing frequency',profile.filing_frequency?profile.filing_frequency.charAt(0).toUpperCase()+profile.filing_frequency.slice(1):null]].map(([label,value])=><div key={label}><dt>{label}</dt><dd>{value||'Not provided'}</dd></div>)}</dl>
 <div className="settings-actions">{has('edit_profile')&&<><button className="button primary" form="business-details-form" disabled={busy}>Save business details</button><Link className="button" href="/settings/onboarding">Complete business onboarding and GST preferences</Link></>}{has('manage_members')&&<Link className="button" href="/settings/members">Manage your business team</Link>}</div>
 </section>
 <section className="bv-card"><h2>GST registration</h2><p>Format validation does not verify government registration.</p><form className="account-form" onSubmit={event=>{event.preventDefault();save('/api/settings/profile',{client_id:data.client_id,profile_id:profile.profile_id,gstin:profile.gstin})}}>
 <label>GSTIN<input maxLength={15} required readOnly={!has('edit_gstin')} value={profile.gstin||''} onChange={event=>setProfile({...profile,gstin:event.target.value.toUpperCase()})}/></label>
 {has('edit_gstin')&&<div className="wide"><button className="button primary" disabled={busy}>Save GSTIN</button></div>}</form></section><LogoUpload key={data.client_id} businessName={profile.legal_name} editable={has('edit_profile')}/><CompanyChecks key={`${data.client_id}:${profile.gstin||''}`} checks={data.company_checks} websiteEditor={<WebsiteEditor key={data.client_id} clientId={data.client_id} profile={profile} editable={has('edit_profile')} onSaved={saved=>setProfile({...profile,website_url:saved.website_url,profile_id:saved.profile_id})}/>}/></div>}
 </>
}
