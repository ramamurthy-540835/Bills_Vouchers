import {test,expect} from '../../frontend/node_modules/@playwright/test'

test.beforeEach(async({request,context,baseURL})=>{
 test.skip(Boolean(process.env.BV_TEST_URL),'Synthetic local extraction diagnostics only')
 await request.post('http://127.0.0.1:8103/__test__/reset')
 await context.addCookies([{name:'session',value:'local-browser-test',url:baseURL!}])
})

test('partial extraction keeps valid fields, leaves uncertain values blank and records explicit review',async({page,request})=>{
 await request.post('http://127.0.0.1:8103/__test__/auto-review')
 const list=await(await request.get('http://127.0.0.1:8103/api/gst/bills?period=2026-09')).json()
 let invoice={...list.invoices[0],extraction:{...list.invoices[0].extraction,document_flags:['field_issue:invalid:totals.invoice_total']}}
 let patch:any
 await page.route(`**/api/gst/bills/${invoice.invoice_id}`,async route=>{
  if(route.request().method()==='PATCH'){
   patch=route.request().postDataJSON()
   invoice={...invoice,...patch,version:invoice.version+1,extraction:{...invoice.extraction,document_flags:[]}}
   delete (invoice as any).reviewed_extraction_fields
  }
  return route.fulfill({json:invoice})
 })
 await page.goto('/bills?period=2026-09')
 await page.locator('.bills-table tbody tr').first().getByRole('button',{name:'Review'}).click()
 const dialog=page.getByRole('dialog')
 await expect(dialog.getByRole('region',{name:'Extraction results'})).toContainText('Valid extracted fields have been retained')
 const unknown=dialog.locator('input[aria-invalid=true]')
 await expect(unknown).toHaveCount(1)
 await expect(unknown).toHaveValue('')
 await unknown.fill('1180.00')
 await dialog.getByRole('button',{name:'Save changes',exact:true}).click()
 await expect.poll(()=>patch?.reviewed_extraction_fields).toEqual(['totals.invoice_total'])
 expect(patch.supplier_legal_name).toBe(list.invoices[0].supplier_legal_name)
 expect(patch.line_items).toEqual(list.invoices[0].line_items)
 await expect(dialog.locator('input[aria-invalid=true]')).toHaveCount(0)
})

test('failed extraction files are separate, show actionable reasons and retain private original access',async({page})=>{
 let retried=false
 await page.route('**/api/gst/bills/intelligence?*',async route=>{
  const original=await(await route.fetch()).json()
  return route.fulfill({json:{...original,upload_issue_count:retried?0:1,upload_issues:retried?[]:[{job_id:'synthetic-failure',file_index:0,filename:'factory-original.jpg',code:'reading_timeout',message:'Document reading timed out. Your original is saved. Retry extraction.',retryable:true,original_url:'/api/gst/bills/upload/synthetic-failure/original/0'}]}})
 })
 await page.route('**/api/gst/bills/upload/synthetic-failure/retry',route=>{retried=true;return route.fulfill({json:{job_id:'synthetic-failure',status:'completed',files:[]}})})
 await page.goto('/bills?period=2026-09')
 const problems=page.getByRole('region',{name:'Upload processing issues'})
 await expect(problems).toContainText('factory-original.jpg')
 await expect(problems).toContainText('timed out')
 const original=problems.getByRole('link',{name:'View original'})
 await expect(original).toHaveAttribute('href','/api/gst/bills/upload/synthetic-failure/original/0')
 await expect(original).toHaveAttribute('target','_blank')
 await page.setViewportSize({width:390,height:900})
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy()
 await page.screenshot({path:'../artifacts/diagnostics-2026-11-09/extraction-issues-mobile.png',fullPage:true})
 await problems.getByRole('button',{name:'Retry extraction'}).click()
 await expect(problems).toHaveCount(0)
})

test('failed bill-list loads show retry instead of a false empty register',async({page})=>{
 let failed=true
 await page.route(/\/api\/gst\/bills\?period=/,route=>failed?route.fulfill({status:503,json:{error:{message:'Synthetic bill storage unavailable'}}}):route.continue())
 await page.goto('/bills?period=2026-09')
 const register=page.locator('.bill-register-card')
 await expect(register.getByRole('alert')).toContainText('Synthetic bill storage unavailable')
 await expect(register.locator('.empty-state')).toHaveCount(0)
 failed=false
 await register.getByRole('button',{name:'Retry loading bills'}).click()
 await expect(register.getByRole('alert')).toHaveCount(0)
 await expect(register.locator('.empty-state')).toBeVisible()
})

test('replacement-line acknowledgement remains actionable after reopening',async({page,request})=>{
 await request.post('http://127.0.0.1:8103/__test__/auto-review')
 const list=await(await request.get('http://127.0.0.1:8103/api/gst/bills?period=2026-09')).json()
 let invoice={...list.invoices[0],extraction:{...list.invoices[0].extraction,document_flags:['field_issue:missing:line_items.99.cgst']}}
 let patch:any
 await page.route(`**/api/gst/bills/${invoice.invoice_id}`,route=>{
  if(route.request().method()==='PATCH'){patch=route.request().postDataJSON();invoice={...invoice,version:invoice.version+1,extraction:{...invoice.extraction,document_flags:[]}}}
  return route.fulfill({json:invoice})
 })
 await page.goto('/bills?period=2026-09')
 await page.locator('.bills-table tbody tr').first().getByRole('button',{name:'Review'}).click()
 const dialog=page.getByRole('dialog')
 await dialog.getByRole('checkbox',{name:/I checked the replacement line items/}).check()
 await expect(dialog.getByRole('button',{name:'Save changes',exact:true})).toBeEnabled()
 await dialog.getByRole('button',{name:'Save changes',exact:true}).click()
 await expect.poll(()=>patch?.reviewed_extraction_fields).toEqual(['line_items'])
 expect(patch.line_items).toEqual(list.invoices[0].line_items)
})
