import {test,expect} from '../../frontend/node_modules/@playwright/test'
import {backendIdentityMatches} from '../../frontend/lib/backend-identity'

test('Cloud Run audience accepts only the same service and its revision tags',()=>{
 const service='https://gst-easy-v2-api-foovqasysa-el.a.run.app'
 expect(backendIdentityMatches(service,service)).toBe(true)
 expect(backendIdentityMatches(service.replace('https://','https://auto-review---'),service)).toBe(true)
 for(const target of [
  'https://auto-review---gst-easy-v3-api-foovqasysa-el.a.run.app',
  service+'.evil.example',
  'https://auto-review---'+new URL(service).hostname+'.evil.example',
  service.replace('https://','http://auto-review---'),
  service.replace('https://','https://auto-review---')+':8443',
 ])expect(backendIdentityMatches(target,service)).toBe(false)
 expect(backendIdentityMatches('https://auto-review---example.com','https://example.com')).toBe(false)
 expect(backendIdentityMatches(service,service+'/other')).toBe(false)
})
