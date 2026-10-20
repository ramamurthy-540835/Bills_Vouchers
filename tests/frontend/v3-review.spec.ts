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

test('source column mapping previews renamed fields without creating bills',async({page})=>{
 await page.goto('/bills?period=2026-09')
 await page.getByText('Bulk source intake',{exact:true}).click()
 await page.getByLabel('Source file',{exact:true}).setInputFiles({name:'mapped.csv',mimeType:'text/csv',
  buffer:Buffer.from('External ID,Event,Amount\ntrip-1,trip,100.00\n')})
 await page.getByText('Map source columns (3 ignored)',{exact:true}).click()
 await page.getByLabel('Map External ID',{exact:true}).selectOption('source_record_id')
 await page.getByLabel('Map Event',{exact:true}).selectOption('event_type')
 await page.getByLabel('Map Amount',{exact:true}).selectOption('payment_amount')
 await page.getByRole('button',{name:'Preview import',exact:true}).click()
 await expect(page.getByText('1 valid records; 0 duplicate, conflicting or invalid rows.')).toBeVisible()
 await expect(page.locator('.bills-table tbody tr')).toHaveCount(0)
})

test('saved source reconciliation explains conflicts and retains invoice review links',async({page})=>{
 // Browser rendering fixture only; storage/calculation are tested separately.
 const analysis={observed_at:'2026-10-20T12:00:00Z',counts:{matched:1,ambiguous_reference:1},
  records:[{source_record_id:'vendor-1',status:'matched',message:'Source values match.',href:'/bills?period=2026-09&invoice=synthetic'},
   {source_record_id:'driver-1',status:'ambiguous_reference',message:'Resolve conflicting trip references.'}]}
 await page.route('**/api/gst/bills/intake/**',async route=>{
  const path=new URL(route.request().url()).pathname
  let body:any
  if(path.endsWith('/reconcile'))body=analysis
  else if(path.endsWith('/reconciliations'))body={snapshots:[]}
  else if(path.endsWith('/batches'))body={batches:[{batch_id:'batch-1',created_at:'2026-10-20'}]}
  else body={batch_id:'batch-1',records:[{source_record_id:'vendor-1',source_system:'vendor',source_version:1,status:'staged'}]}
  await route.fulfill({json:body})
 })
 await page.goto('/bills?period=2026-09')
 await page.getByText('Bulk source intake',{exact:true}).click()
 await page.getByRole('button',{name:'Import history',exact:true}).click()
 await page.getByRole('button',{name:'View import',exact:true}).click()
 await expect(page.getByRole('link',{name:'Download original source',exact:true})).toHaveAttribute('href','/api/gst/bills/intake/batches/batch-1/original')
 await page.getByRole('button',{name:'Reconcile with invoices',exact:true}).click()
 await expect(page.getByRole('heading',{name:'Reconciliation results',exact:true})).toBeVisible()
 await expect(page.getByText(/Resolve conflicting trip references/)).toBeVisible()
 await expect(page.getByRole('link',{name:'Review invoice',exact:true})).toHaveAttribute('href','/bills?period=2026-09&invoice=synthetic')
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000})
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy()
  await page.screenshot({path:`../artifacts/gst_new_v3/source-reconciliation-${width}.png`,fullPage:true})
 }
 await page.unrouteAll({behavior:'wait'})
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
 await page.getByRole('button',{name:'Back to bills',exact:true}).click()
 await page.getByRole('button',{name:'Open correction queue',exact:true}).click()
 const queue=page.getByRole('region',{name:'Bill correction queue',exact:true})
 await expect(queue.getByRole('heading',{name:'V3-CORRECTION',exact:true})).toBeVisible()
 await page.getByLabel('Correction state',{exact:true}).selectOption('resubmitted')
 await expect(queue.getByText('No bills match this correction state for the selected period.')).toBeVisible()
 await page.getByLabel('Correction state',{exact:true}).selectOption('rejected')
 await queue.getByRole('button',{name:'Review correction',exact:true}).click()
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
 await page.getByRole('button',{name:'Back to bills',exact:true}).click()
 await page.getByLabel('Correction state',{exact:true}).selectOption('resubmitted')
 await expect(queue.getByRole('heading',{name:'V3-CORRECTION',exact:true})).toBeVisible()
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000})
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy()
  await page.screenshot({path:`../artifacts/gst_new_v3/correction-queue-${width}.png`,fullPage:true})
 }
})

test('correction queue shows real errors and supports retry without fake empty results',async({page})=>{
 let failed=true
 await page.route('**/api/gst/bills/corrections?**',route=>route.fulfill(failed?
  {status:503,json:{detail:'Queue temporarily unavailable'}}:
  {json:{invoices:[],next_offset:null}}))
 await page.goto('/bills?period=2026-09')
 await page.getByRole('button',{name:'Open correction queue',exact:true}).click()
 const queue=page.getByRole('region',{name:'Bill correction queue',exact:true})
 await expect(queue.getByRole('alert')).toContainText('Queue temporarily unavailable')
 await expect(queue.getByText('No bills match this correction state for the selected period.')).toHaveCount(0)
 failed=false
 await queue.getByRole('button',{name:'Retry correction queue',exact:true}).click()
 await expect(queue.getByText('No bills match this correction state for the selected period.')).toBeVisible()
 await page.unrouteAll({behavior:'wait'})
})
