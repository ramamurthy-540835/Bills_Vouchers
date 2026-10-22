import {test,expect} from '../../frontend/node_modules/@playwright/test'

test.beforeEach(async({request,context,baseURL})=>{
 test.skip(Boolean(process.env.BV_TEST_URL),'Local synthetic uploads only')
 await request.post('http://127.0.0.1:8103/__test__/reset')
 await context.addCookies([{name:'session',value:'local-browser-test',url:baseURL!}])
})
test.afterEach(async({request})=>{
 if(!process.env.BV_TEST_URL)await request.post('http://127.0.0.1:8103/api/workspace/client',{data:{client_id:'browser-client'}})
})
for(const role of ['client','tax_admin','viewer'])test(`${role} upload entry points follow bill-write access`,async({page,request})=>{
 await request.post(`http://127.0.0.1:8103/__test__/role/${role}`)
 await page.goto('/gst/workspace?period=2026-09')
 const upload=page.getByRole('region',{name:'Manage your invoices'})
 await expect(upload).toHaveCount(role==='viewer'?0:1)
 if(role!=='viewer'){
  await expect(page.locator('[aria-label="Dashboard filters"]+section')).toHaveAttribute('aria-label','Manage your invoices')
  await upload.getByRole('link').click()
 }else await page.goto('/bills?period=2026-09')
 await expect(page.getByLabel('Upload bills',{exact:true})).toHaveCount(role==='viewer'?0:1)
 if(role==='viewer')expect((await page.request.post('/api/gst/bills/upload?period=2026-09',{multipart:{files:{name:'blocked.csv',mimeType:'text/csv',buffer:Buffer.from('blocked')}}})).status()).toBe(403)
 else {
  await expect(page.getByLabel('Upload bills',{exact:true})).toHaveAttribute('accept','.pdf,.jpg,.jpeg,.png,.xlsx,.csv')
  await page.setViewportSize({width:390,height:844})
  await expect(page.locator('.bill-drop')).toBeVisible()
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy()
 }
 await page.goto('/gst/filing?period=2026-09')
 await expect(page.getByLabel('Upload bills',{exact:true})).toHaveCount(0)
 if(role!=='viewer')await expect(page.getByLabel('Import GSTR-2B',{exact:true})).toBeEnabled()
})

test('shared upload processes purchases and sales, retains originals and prevents duplicates',async({page})=>{
 await page.goto('/gst/workspace?period=2026-09')
 await page.getByRole('region',{name:'Manage your invoices'}).getByRole('link').click()
 const header='Supplier GSTIN,Invoice Number,Invoice Date (DD-MM-YYYY),HSN/SAC,Description,Taxable Value,GST Rate %,CGST,SGST,IGST,Cess,Invoice Total,Place of Supply (State Code),Reverse Charge (Y/N)'
 for(const [number,direction] of [['UPLOAD-PURCHASE','purchase'],['UPLOAD-SALE','sale']]){
  const content=Buffer.from(`${header}\n33ABCDE1234F1Z1,${number},01-09-2026,8703,Vehicle,1000,18,90,90,0,0,1180,33,N`)
  const input=page.getByLabel('Upload bills',{exact:true})
  await expect(input).toBeEnabled()
  await input.setInputFiles({name:`${number}.csv`,mimeType:'text/csv',buffer:content})
  const row=page.locator('.bills-table tbody tr').filter({hasText:number})
  await expect(row).toBeVisible()
  await expect(input).toBeEnabled()
  await input.setInputFiles({name:`renamed-${number}.csv`,mimeType:'text/csv',buffer:content})
  await expect(input).toBeEnabled()
  await expect(row).toHaveCount(1)
  await row.getByRole('button',{name:'Review',exact:true}).click()
  await page.getByRole('combobox',{name:'Purchase or sale',exact:true}).selectOption(direction)
  await page.getByLabel('Supplier legal name',{exact:true}).fill('Synthetic upload supplier')
  await page.getByRole('button',{name:'Save changes',exact:true}).click()
  await expect(page.getByText('Bill updated. Checks have been refreshed.',{exact:true})).toBeVisible()
  await page.getByRole('button',{name:'Back to bills',exact:true}).click()
  const invoices=(await (await page.request.get('/api/gst/bills?period=2026-09')).json()).invoices
  const invoice=invoices.find((value:any)=>value.invoice_number===number)
  expect(invoice.direction).toBe(direction)
  expect((await page.request.get(`/api/gst/bills/${invoice.invoice_id}/original`)).status()).toBe(200)
 }
 await page.reload()
 await expect(page.locator('.bills-table tbody tr')).toHaveCount(2)
})


test('refresh resumes the saved upload job without posting the file again',async({page})=>{
 await page.goto('/bills?period=2026-09')
 await expect(page.getByLabel('Loading bills')).toHaveCount(0)
 await expect(page.getByLabel('Upload bills',{exact:true})).toBeEnabled()
 let finished:any;let resumed=false;let posts=0
 await page.route('**/api/gst/bills/upload?*',async route=>{
  posts++
  finished=await (await route.fetch()).json()
  await route.fulfill({json:{...finished,status:'reading',retryable:false,files:finished.files.map((file:any)=>({...file,status:'reading'}))}})
 })
 await page.route(/\/api\/gst\/bills\/upload\/[^/?]+$/,route=>route.fulfill({json:resumed?finished:{...finished,status:'reading',retryable:false}}))
 const csv='Supplier GSTIN,Invoice Number,Invoice Date (DD-MM-YYYY),HSN/SAC,Description,Taxable Value,GST Rate %,CGST,SGST,IGST,Cess,Invoice Total,Place of Supply (State Code),Reverse Charge (Y/N)\n33ABCDE1234F1Z1,UPLOAD-RESUME,01-09-2026,8703,Vehicle,1000,18,90,90,0,0,1180,33,N'
 await expect(page.getByLabel('Upload bills',{exact:true})).toBeEnabled()
 await page.getByLabel('Upload bills',{exact:true}).setInputFiles({name:'resume.csv',mimeType:'text/csv',buffer:Buffer.from(csv)})
 await expect.poll(()=>page.evaluate(()=>sessionStorage.getItem('gst-bill-job:browser-client:2026-09'))).toBeTruthy()
 resumed=true
 await page.reload()
 await expect(page.getByText('UPLOAD-RESUME',{exact:true})).toBeVisible()
 await expect(page.getByLabel('Upload bills',{exact:true})).toBeEnabled()
 expect(posts).toBe(1)
})
