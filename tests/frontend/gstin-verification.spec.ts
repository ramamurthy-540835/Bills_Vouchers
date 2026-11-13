import {test,expect} from '../../frontend/node_modules/@playwright/test'
test.beforeEach(async({context,request,baseURL})=>{
 test.skip(Boolean(process.env.BV_TEST_URL),'Local synthetic browser fixtures only')
 await request.post('http://127.0.0.1:8103/__test__/reset')
 await context.addCookies([{name:'session',value:'local-browser-test',url:baseURL!}])
})
test('GST profile offers manual official portal checking without a live provider feature',async({page})=>{
 let providerCalls=0
 await page.route('**/api/businesses/current/**',route=>{providerCalls++;return route.fulfill({status:404,json:{detail:'Not found'}})})
 await page.goto('/settings/profile')
 await expect(page.getByText('GSTIN format',{exact:true})).toBeVisible()
 await expect(page.getByText(/does not perform an automatic government lookup/i)).toBeVisible()
 await expect(page.getByRole('button',{name:/verify gstin/i})).toHaveCount(0)
 await expect(page.getByText(/GSP Integration|Direct GSTN Filing|Coming Soon|Method B/i)).toHaveCount(0)
 const link=page.getByRole('link',{name:'Check taxpayer on the official GST portal'})
 await expect(link).toHaveAttribute('href','https://services.gst.gov.in/services/searchtp')
 await expect(link).toHaveAttribute('rel','noopener noreferrer')
 await expect(page.getByText(/Opening the portal does not mark this account verified/i)).toBeVisible()
 expect(providerCalls).toBe(0)
 await page.setViewportSize({width:390,height:844})
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy()
})
