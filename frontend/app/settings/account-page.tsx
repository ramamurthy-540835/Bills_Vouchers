import {headers} from 'next/headers'
import {redirect} from 'next/navigation'
import Workspace from '../workspace'
import AccountForm from './account-form'
import OnboardingForm from './onboarding-form'
import MembersForm from './members-form'
import CustomerForm from './customer-form'
export default async function AccountPage({section}:{section:string}){
 const response=await fetch(`${process.env.BACKEND_URL||'http://localhost:8000'}/api/settings/account`,{headers:{cookie:(await headers()).get('cookie')||''},cache:'no-store'})
 if(response.status===401)redirect('/login')
 const data=response.ok?await response.json():null
 return <Workspace view={section} initial={data}>{data&&(section==='onboarding'?<OnboardingForm data={data}/>:section==='members'?<MembersForm/>:<AccountForm data={data} section={section}/>)}{data&&section==='profile'&&data.can_edit_profile&&<CustomerForm/>}</Workspace>
}
