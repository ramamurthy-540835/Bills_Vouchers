// A revision tag shares its service's Cloud Run OIDC audience, not its hostname.
export function backendIdentityMatches(expected: string, audience: string): boolean {
 if(expected===audience)return true
 try{
  const target=new URL(expected), identity=new URL(audience)
  if(target.origin!==expected||identity.origin!==audience||target.protocol!=='https:'||identity.protocol!=='https:')return false
  if(target.port||identity.port||!identity.hostname.endsWith('.run.app'))return false
  const suffix='---'+identity.hostname
  if(!target.hostname.endsWith(suffix))return false
  const tag=target.hostname.slice(0,-suffix.length)
  return /^[a-z][a-z0-9-]{0,62}$/.test(tag)
 }catch{return false}
}
