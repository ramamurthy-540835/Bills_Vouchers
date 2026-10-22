import 'server-only'
import {backendIdentityMatches} from './backend-identity'

// Opt-in Cloud Run authentication. Local and existing deployments remain unchanged.
export async function backendFetch(input:string,init:RequestInit={}){
 const audience=process.env.BACKEND_ID_TOKEN_AUDIENCE
 const headers=new Headers(init.headers)
 headers.delete('x-serverless-authorization')
 if(audience){
  const expected=new URL(process.env.BACKEND_URL!).origin
  if(new URL(input).origin!==expected||!backendIdentityMatches(expected,audience))throw new Error('Backend identity configuration mismatch')
  const endpoint='http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity?audience='+encodeURIComponent(audience)
  const token=await fetch(endpoint,{headers:{'Metadata-Flavor':'Google'},cache:'no-store',signal:AbortSignal.timeout(5000)})
  if(!token.ok)throw new Error('Backend identity unavailable')
  headers.set('X-Serverless-Authorization','Bearer '+await token.text())
 }
 return fetch(input,{...init,headers,redirect:'manual'})
}
