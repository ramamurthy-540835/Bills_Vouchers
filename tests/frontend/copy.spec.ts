import {test,expect} from '../../frontend/node_modules/@playwright/test'

test.beforeEach(async({context,request,baseURL})=>{
 if(process.env.BV_TEST_URL){
  const result=await request.post('/api/auth/login',{data:{email:process.env.BV_TEST_EMAIL,password:process.env.BV_TEST_PASSWORD}})
  expect(result.ok()).toBeTruthy()
  await context.addCookies((await request.storageState()).cookies)
 }else await context.addCookies([{name:'session',value:'local-browser-test',url:baseURL!}])
})

test('GST Easy copy, tooltips, glossary, navigation and bills empty state',async({page})=>{
 await page.goto('/gst/workspace?period=2026-09')
 await expect(page.getByRole('heading',{name:'GST Easy',exact:true})).toBeVisible()
 await expect(page.getByRole('navigation',{name:'Main navigation'}).getByRole('link',{name:'GST Easy',exact:true})).toBeVisible()
 await expect(page.locator('.metric-card .term-tip summary')).toHaveCount(4)
 await expect(page.locator('body')).not.toContainText(/Finance Control Plane|Estimated cash|Actual customer records|Umesh|27AAPFU0939F1ZV/)
 // The CA caption intentionally retains the technical term from the centralized copy module.
 await expect(page.locator('.metric-card > span')).not.toContainText([/Eligible ITC/])
 await page.getByRole('button',{name:'Understand these terms',exact:true}).click()
 await expect(page.getByRole('dialog')).toBeVisible()
 await expect(page.getByRole('dialog')).toContainText('GST Liability on Sales − Usable ITC')
 await page.getByRole('button',{name:'Close',exact:true}).click()
 await page.screenshot({path:'../artifacts/v3/gst-easy.png',fullPage:true})
 await page.goto('/bills?period=2026-09')
 await expect(page.getByRole('heading',{name:'Bills',exact:true})).toBeVisible()
 await expect(page.getByText('Drop your purchase bills here — PDF, photo, Excel or CSV')).toBeVisible()
 await expect(page.getByRole('link',{name:'Download the Excel template'})).toBeVisible()
 await expect(page.locator('body')).not.toContainText(/Finance Control Plane|Eligible ITC|Estimated cash|Actual customer records|BigQuery|run_id/)
 await page.screenshot({path:'../artifacts/v3/bills.png',fullPage:true})
 const response=await page.request.get('/documents?period=2026-09',{maxRedirects:0})
 expect(response.status()).toBe(301)
 expect(response.headers().location).toContain('/bills')
})

test('local upload accepts CSV, presents canonical review and blocks missing GSTIN confirmation',async({page})=>{
 test.skip(Boolean(process.env.BV_TEST_URL),'Never upload test records to the live customer workspace')
 await page.goto('/bills?period=2026-09')
 await expect(page.getByLabel('Loading bills')).toHaveCount(0)
 const csv='Supplier GSTIN,Invoice Number,Invoice Date (DD-MM-YYYY),HSN/SAC,Description,Taxable Value,GST Rate %,CGST,SGST,IGST,Cess,Invoice Total,Place of Supply (State Code),Reverse Charge (Y/N)\n33ABCDE1234F1Z1,LOCAL-TEST,01-09-2026,8703,Vehicle,1000,18,90,90,0,0,1180,33,N'
 const invoiceNumber=`T-${Date.now().toString().slice(-10)}`
 await page.getByLabel('Upload bills',{exact:true}).setInputFiles({name:'local-test.csv',mimeType:'text/csv',buffer:Buffer.from(csv.replace('LOCAL-TEST',invoiceNumber))})
 await expect(page.getByText(invoiceNumber,{exact:true})).toBeVisible()
 await page.locator('.bills-table tr').filter({hasText:invoiceNumber}).getByRole('button',{name:'Review',exact:true}).click()
 await expect(page.getByRole('heading',{name:'GST invoice',exact:true})).toBeVisible()
 await expect(page.getByText('Add your business GSTIN in Client profile before confirming this bill.')).toBeVisible()
 await page.getByLabel('Supplier legal name',{exact:true}).fill('Reviewed supplier')
 await page.getByLabel('Supplier legal name',{exact:true}).press('Tab')
 await expect(page.getByText('Bill updated. Checks have been refreshed.')).toBeVisible()
 await page.getByRole('button',{name:'Confirm bill',exact:true}).click()
 await expect(page.getByText('Resolve the highlighted bill details before confirming.')).toBeVisible()
 await page.getByRole('button',{name:'Reject',exact:true}).click()
 await expect(page.locator('.section-heading .chip').filter({hasText:'Rejected'})).toBeVisible()
})
