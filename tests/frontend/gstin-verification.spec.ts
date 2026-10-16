import {test,expect} from '../../frontend/node_modules/@playwright/test'
test.beforeEach(async({context,request,baseURL})=>{
 test.skip(Boolean(process.env.BV_TEST_URL),'Local synthetic registration fixtures only')
 await request.post('http://127.0.0.1:8103/__test__/reset')
 await context.addCookies([{name:'session',value:'local-browser-test',url:baseURL!}])
})
test('Manual check is honest and has no automatic verification action',async({page})=>{
 await page.goto('/settings/profile')
 const panel=page.getByLabel('GST registration verification',{exact:true})
 await expect(panel.getByText('Automatic verification not configured',{exact:true})).toBeVisible()
 await expect(page.getByRole('button',{name:'Verify GSTIN',exact:true})).toHaveCount(0)
 const link=page.getByRole('link',{name:'Check taxpayer on the official GST portal'})
 await expect(link).toHaveAttribute('href','https://services.gst.gov.in/services/searchtp')
 await expect(link).toHaveAttribute('rel','noopener noreferrer')
 await expect(panel).toContainText('do not verify GSTIN ownership')
 await panel.screenshot({path:'../artifacts/gst_easy/gstin-manual-desktop.png'})
 await page.setViewportSize({width:390,height:844})
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy()
 await panel.screenshot({path:'../artifacts/gst_easy/gstin-manual-mobile.png'})
})
test('Configured provider states and errors remain separate from ownership',async({page})=>{
 let state:any={state:'not_checked',checksum_valid:true,automatic_available:true,can_verify:true}
 await page.route('**/api/businesses/current/gstin-verification',route=>route.fulfill({json:state}))
 await page.route('**/api/businesses/current/verify-gstin',route=>{
  expect(route.request().postData()).toBeNull()
  expect(route.request().headers()['x-csrf-token']).toBeTruthy()
  state={...state,state:'mismatch',source:'Synthetic test provider',checked_at:'2026-10-17T12:00:00Z',fresh:true,taxpayer_found:true,registration_status:'active',business_name_match:false,record:{found:true,legal_name:'Different Company'}}
  return route.fulfill({json:state})
 })
 await page.goto('/settings/profile');await page.getByRole('button',{name:'Verify GSTIN',exact:true}).click()
 const panel=page.getByLabel('GST registration verification',{exact:true})
 await expect(panel.getByText('Details mismatch',{exact:true})).toBeVisible()
 await expect(panel.getByText('Does not match',{exact:true})).toBeVisible()
 await panel.getByText('Provider details and comparison').click()
 await expect(panel.getByText('Different Company',{exact:true})).toBeVisible()
 await panel.screenshot({path:'../artifacts/gst_easy/gstin-mismatch.png'})
 for(const [value,label] of [['verified','Verified against provider'],['inactive','Inactive or cancelled registration'],['stale','Verification expired or profile changed'],['failed','Verification failed'],['not_found','Taxpayer record not found']]){
  state={...state,state:value};await page.reload();await expect(panel.getByText(label,{exact:true})).toBeVisible()
 }
 await page.unroute('**/api/businesses/current/verify-gstin')
 await page.route('**/api/businesses/current/verify-gstin',route=>route.fulfill({status:429,json:{detail:'Please retry later.'}}))
 await page.getByRole('button',{name:'Verify GSTIN',exact:true}).click()
 await expect(panel.getByRole('alert')).toHaveText('Please retry later.')
 state={state:'not_configured',automatic_available:false,can_verify:false,checksum_valid:false}
 await page.getByRole('button',{name:'Switch to Business Synthetic Read Only',exact:true}).click()
 await expect(page.getByLabel('Legal name',{exact:true})).toHaveValue('Synthetic Read Only')
 await expect(panel.getByText('Automatic verification not configured',{exact:true})).toBeVisible()
 await expect(panel.getByRole('button',{name:'Verify GSTIN'})).toHaveCount(0)
 await expect(panel).not.toContainText('Different Company')
})
