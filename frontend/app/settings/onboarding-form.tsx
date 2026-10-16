'use client'
import {useState} from 'react'
import Link from 'next/link'
import CompanyChecks from './company-checks'
import LogoUpload from './logo-upload'

export default function OnboardingForm({data}:{data:any}){
 const [profile,setProfile]=useState({...data.profile,contact_phone:data.profile?.contact_phone||data.user.mobile_number||''}),[step,setStep]=useState(0),[busy,setBusy]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState('')
 const [checks,setChecks]=useState(data.company_checks)
 const editable=data.can_edit_profile
 const field=(key:string,label:string,type='text')=><label key={key}>{label}<input type={type} value={profile[key]||''} maxLength={key==='gstin'?15:200} readOnly={!editable} onChange={event=>setProfile({...profile,[key]:['gstin','pan'].includes(key)?event.target.value.toUpperCase():event.target.value})}/></label>
 const select=(key:string,label:string,values:string[])=><div key={key}><label htmlFor={`onboarding-${key}`}>{label}</label><select id={`onboarding-${key}`} value={profile[key]||''} disabled={!editable} onChange={event=>setProfile({...profile,[key]:event.target.value})}><option value="">Choose…</option>{values.map(value=><option key={value}>{value}</option>)}</select></div>
 async function save(complete=false){setBusy(true);setError('');setMessage('');try{
  const csrf=await fetch('/api/auth/csrf');const {token}=await csrf.json()
  const fields=['legal_name','trade_name','website_url','constitution','registration_type','filing_frequency','state_code','pan','principal_address','contact_person','contact_email','contact_phone']
  const body:any={client_id:data.client_id,profile_id:profile.profile_id,complete_onboarding:complete,...Object.fromEntries(fields.map(key=>[key,profile[key]||'']))}
  if((data.is_owner||['admin','tax_admin'].includes(data.user.role))&&(profile.gstin||profile.registration_type==='Unregistered'))body.gstin=profile.gstin||''
  const response=await fetch('/api/settings/profile',{method:'POST',headers:{'content-type':'application/json','x-csrf-token':token},body:JSON.stringify(body)});const result=await response.json()
  if(!response.ok)throw Error(result.error?.message||result.detail?.message||result.detail||'Could not save business details.')
  const refreshed=await fetch('/api/settings/account');if(!refreshed.ok)throw Error('Saved, but could not reload the profile. Refresh this page.')
  const saved=await refreshed.json();setProfile(saved.profile);setChecks(saved.company_checks);setMessage(complete?'Business onboarding completed.':'Progress saved.')
 }catch(e){setError(e instanceof Error?e.message:'Could not save.')}finally{setBusy(false)}}
 return <><section className="bv-card"><h2>Business onboarding</h2><p>{profile.onboarding_completed?'Your business profile is complete.':'Complete your business details before preparing GST records.'}</p>
 <nav aria-label="Onboarding steps" className="section-heading">{['Business','Registration','Address and contact'].map((label,index)=><button type="button" className="button secondary" key={label} aria-current={step===index?'step':undefined} onClick={()=>setStep(index)}>{index+1}. {label}</button>)}</nav>
 <form className="account-form" onSubmit={event=>{event.preventDefault();save(step===2)}}>
 {step===0&&<>{field('legal_name','Business legal name')}{field('trade_name','Trade name')}{field('website_url','Company website','url')}{select('constitution','Business type',['Proprietorship','Partnership','LLP','Company','Trust','Other'])}</>}
 {step===1&&<>{select('registration_type','GST registration type',['Regular','Composition','Unregistered'])}{field('gstin','GSTIN, where applicable')}{field('pan','PAN, where applicable')}{select('filing_frequency','Filing frequency',['monthly','quarterly'])}{field('state_code','Registration state code')}<p className="wide muted">GSTIN format checks do not verify government registration status. Leave GSTIN blank only for an unregistered business.</p></>}
 {step===2&&<>{field('principal_address','Business address')}{field('contact_person','Primary contact name')}{field('contact_email','Business email','email')}{field('contact_phone','Business mobile with country code','tel')}</>}
 <div className="wide"><button type="button" className="button secondary" disabled={busy||!editable} onClick={()=>save(false)}>Save progress</button> {step<2?<button type="button" className="button primary" onClick={()=>setStep(step+1)}>Next</button>:<button className="button primary" disabled={busy||!editable}>Complete onboarding</button>}</div>
 </form>{error&&<p role="alert" className="error">{error}</p>}{message&&<p role="status">{message}</p>}{profile.onboarding_completed&&<Link className="button primary" href="/gst/workspace">Open GST Easy</Link>}</section><CompanyChecks checks={checks}/><LogoUpload editable={editable}/></>
}
