import {test,expect} from '../../frontend/node_modules/@playwright/test'

test.beforeEach(async({request,context,baseURL})=>{
 test.skip(Boolean(process.env.BV_TEST_URL),'Synthetic local fixture only')
 await request.post('http://127.0.0.1:8103/__test__/reset')
 await context.addCookies([{name:'session',value:'local-browser-test',url:baseURL!}])
})

test('source preview separates trips from invoices and quarantines invalid amounts',async({page})=>{
 await page.goto('/bills?period=2026-09')
 await page.getByText('Bulk source intake',{exact:true}).click()
 await page.getByLabel('Source system',{exact:true}).selectOption('driver')
 await page.getByLabel('Source file',{exact:true}).setInputFiles({name:'synthetic.json',mimeType:'application/json',
  buffer:Buffer.from(JSON.stringify([{source_record_id:'trip-1',event_type:'trip',payment_amount:'100.00'},
   {source_record_id:'trip-2',event_type:'trip',payment_amount:'NaN'}]))})
 await page.getByRole('button',{name:'Preview import',exact:true}).click()
 await expect(page.getByText('1 valid records; 1 duplicate, conflicting or invalid rows.')).toBeVisible()
 await expect(page.getByText(/Row 2: quarantined/)).toBeVisible()
 await expect(page.locator('.bills-table tbody tr')).toHaveCount(0)
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000})
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy()
  await page.screenshot({path:`../artifacts/gst_new_v3/intake-${width}.png`,fullPage:true})
 }
})

test('rejection correction retains evidence and cannot bypass missing GSTIN validation',async({page})=>{
 await page.goto('/bills?period=2026-09')
 await expect(page.getByLabel('Loading bills')).toHaveCount(0)
 const csv='Supplier GSTIN,Invoice Number,Invoice Date (DD-MM-YYYY),HSN/SAC,Description,Taxable Value,GST Rate %,CGST,SGST,IGST,Cess,Invoice Total,Place of Supply (State Code),Reverse Charge (Y/N)\n33ABCDE1234F1Z1,V3-CORRECTION,01-09-2026,8703,Synthetic item,1000,18,90,90,0,0,1180,33,N'
 await page.getByLabel('Upload bills',{exact:true}).setInputFiles({name:'synthetic.csv',mimeType:'text/csv',buffer:Buffer.from(csv)})
 await page.locator('.bills-table tr').filter({hasText:'V3-CORRECTION'}).getByRole('button',{name:'Review',exact:true}).click()
 await expect(page.getByRole('heading',{name:'GST comparison',exact:true})).toBeVisible()
 await page.getByLabel('Rejection category',{exact:true}).selectOption('supplier_mismatch')
 await page.getByLabel('Rejection reason',{exact:true}).fill('Supplier name needs a correction.')
 await page.getByRole('button',{name:'Reject',exact:true}).click()
 await expect(page.getByRole('button',{name:'Request correction',exact:true})).toBeVisible()
 await page.getByLabel('Correction reason',{exact:true}).fill('Correct supplier from original evidence.')
 await page.getByRole('button',{name:'Request correction',exact:true}).click()
 await expect(page.getByText('Edit the bill fields and save changes before resubmitting.')).toBeVisible()
 await page.getByLabel('Supplier legal name',{exact:true}).fill('Synthetic corrected supplier')
 await page.getByRole('button',{name:'Save changes',exact:true}).click()
 await expect(page.getByRole('button',{name:'Resubmit corrected bill',exact:true})).toBeVisible()
 await page.getByLabel('Correction reason',{exact:true}).fill('Supplier corrected; validation must still apply.')
 await page.getByRole('button',{name:'Resubmit corrected bill',exact:true}).click()
 await expect(page.getByRole('button',{name:'Resubmit corrected bill',exact:true})).toHaveCount(0)
 await expect(page.getByText('Add your business GSTIN in Client profile before confirming this bill.')).toBeVisible()
 await page.getByRole('button',{name:'Confirm bill',exact:true}).click()
 await expect(page.getByText('Resolve the highlighted bill details before confirming.')).toBeVisible()
 await expect(page.locator('.bills-table tr').filter({hasText:'V3-CORRECTION'})).not.toContainText('Confirmed')
 await expect(page.getByRole('link',{name:'View Original Bill',exact:true})).toBeVisible()
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000})
  expect(await page.locator('.bill-review-drawer').evaluate(el=>el.scrollWidth<=el.clientWidth)).toBeTruthy()
  await page.screenshot({path:`../artifacts/gst_new_v3/correction-${width}.png`,fullPage:true})
 }
})
