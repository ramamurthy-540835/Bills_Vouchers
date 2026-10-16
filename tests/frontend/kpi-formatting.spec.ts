import {test,expect} from '../../frontend/node_modules/@playwright/test'
import {formatINR,formatCount} from '../../frontend/lib/format-values'

// Restore the local owner workspace after read-only business-switch checks.
test.afterEach(async({request})=>{
 if(!process.env.BV_TEST_URL)await request.post('http://127.0.0.1:8103/api/workspace/client',{data:{client_id:'browser-client'}})
})

const rupee='\u20b9'
test('exact INR and count formatting distinguishes zero from unavailable',()=>{
 for(const [value,expected] of [['0',`${rupee}0.00`],['1000',`${rupee}1,000.00`],['25500',`${rupee}25,500.00`],['148750.50',`${rupee}1,48,750.50`],['1250000',`${rupee}12,50,000.00`],['-1000.25',`-${rupee}1,000.25`],['9007199254740993.12',`${rupee}9,00,71,99,25,47,40,993.12`],['1.999',`${rupee}2.00`]]) expect(formatINR(value)).toBe(expected)
 expect(formatINR(0)).toBe(`${rupee}0.00`)
 for(const value of [null,undefined,'',NaN,Infinity,'invalid',{},Number.MAX_SAFE_INTEGER+1]){
  expect(formatINR(value)).toBe('Unavailable')
  expect(formatCount(value)).toBe('Unavailable')
 }
 expect(formatCount(0)).toBe('0')
 expect(formatCount('1250')).toBe('1,250')
 expect(formatCount('25.0')).toBe('25')
 expect(formatCount('1.5')).toBe('Unavailable')
 expect(formatCount('-1')).toBe('Unavailable')
})

test('all nine KPI cards preserve formatting through refresh and loading',async({page,request,context,baseURL})=>{
 test.skip(Boolean(process.env.BV_TEST_URL),'Local fixtures only')
 await request.post('http://127.0.0.1:8103/__test__/reset')
 await context.addCookies([{name:'session',value:'local-browser-test',url:baseURL!}])
 await page.goto('/gst/workspace?period=2026-09')
 const grid=page.getByRole('region',{name:'GST summary'})
 await expect(grid.locator('.metric-card')).toHaveCount(9)
 const original=await (await page.request.get('/api/gst/bills/dashboard?period=2026-09')).json()
 let payload={...original,confirmed_count:0,totals:{eligible_credit:'0',output_tax:'1000',cash_required:'148750.50',non_gst:'-25500.00'},confirmed_sales:'1250000',confirmed_purchases:'0',review_count:0,mismatch_count:1250,unmatched_count:25}
 let release: (()=>void)|undefined
 let delayed=false
 await page.route('**/api/gst/bills/dashboard?**',async route=>{
  if(delayed)await new Promise<void>(resolve=>{release=resolve})
  await route.fulfill({json:payload})
 })
 await page.getByRole('button',{name:'Refresh dashboard',exact:true}).click()
 await expect(grid.locator('.metric-card>strong')).toHaveText([`${rupee}0.00`,`${rupee}1,000.00`,`${rupee}1,48,750.50`,`-${rupee}25,500.00`,`${rupee}12,50,000.00`,`${rupee}0.00`,'0','1,250','25'])
 delayed=true
 await page.getByRole('button',{name:'Refresh dashboard',exact:true}).click()
 await expect(grid).toHaveAttribute('aria-busy','true')
 await expect(grid.getByRole('status')).toHaveCount(9)
 payload={...original,totals:{},confirmed_sales:null,confirmed_purchases:null,review_count:null,mismatch_count:null,unmatched_count:null}
 await expect.poll(()=>Boolean(release)).toBe(true)
 release!()
 await expect(grid.locator('.metric-card>strong')).toHaveText(Array(9).fill('Unavailable'))
 await expect(grid).toHaveAttribute('aria-busy','false')
 await page.unroute('**/api/gst/bills/dashboard?**')
 await page.reload()
 await expect(grid.locator('.metric-card>strong')).toHaveText([formatINR(original.totals?.eligible_credit),formatINR(original.totals?.output_tax),formatINR(original.totals?.cash_required),formatINR(original.totals?.non_gst),formatINR(original.confirmed_sales),formatINR(original.confirmed_purchases),formatCount(original.review_count),formatCount(original.mismatch_count),formatCount(original.unmatched_count)])
 await page.getByLabel('Account menu',{exact:true}).click()
 await page.getByLabel('Switch business',{exact:true}).selectOption('browser-readonly')
 await expect(page.getByLabel('Selected business',{exact:true})).toHaveText('Synthetic Read Only')
 const switched=await (await page.request.get('/api/gst/bills/dashboard?period=2026-09')).json()
 expect(switched.client_id).toBe('browser-readonly')
 await expect(grid.locator('.metric-card>strong')).toHaveText([formatINR(switched.totals?.eligible_credit),formatINR(switched.totals?.output_tax),formatINR(switched.totals?.cash_required),formatINR(switched.totals?.non_gst),formatINR(switched.confirmed_sales),formatINR(switched.confirmed_purchases),formatCount(switched.review_count),formatCount(switched.mismatch_count),formatCount(switched.unmatched_count)])
})
