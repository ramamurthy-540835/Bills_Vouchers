import {cookies,headers} from 'next/headers'
import {redirect} from 'next/navigation'
import Workspace from '../../workspace'
import Review from './review'
export default async function Page({params,searchParams}:{params:Promise<{id:string}>;searchParams:Promise<{period?:string}>}){
 const jar=await cookies();if(!jar.has('session'))redirect('/login')
 const {id}=await params,{period}=await searchParams,query=period?'?period='+encodeURIComponent(period):''
 const options={headers:{cookie:(await headers()).get('cookie')||''},cache:'no-store' as const,signal:AbortSignal.timeout(25000)}
 const base=process.env.BACKEND_URL||'http://localhost:8000'
 let data:any=null,doc:any=null
 try{const [a,b]=await Promise.all([fetch(base+'/api/workspace'+query,options),fetch(base+'/api/pipeline/documents/'+encodeURIComponent(id)+query,options)]);if(a.status===401)redirect('/login');if(a.ok)data=await a.json();if(b.ok)doc=await b.json()}catch{}
 return <Workspace view="review" initial={data}>{doc?<Review doc={doc} period={data?.period} write={['client','tax_admin','admin'].includes(data?.user?.role)&&data?.filing?.state!=='locked'&&!data?.demo_fallback}/>:<section className="bv-card"><h2>Document unavailable</h2><p>This document is not available in your selected client and period.</p></section>}</Workspace>
}
