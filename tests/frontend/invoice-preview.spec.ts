import {test,expect} from '../../frontend/node_modules/@playwright/test'
import {readFileSync} from 'node:fs'
import path from 'node:path'

test.beforeEach(async({request,context,baseURL})=>{
 test.skip(Boolean(process.env.BV_TEST_URL),'Local synthetic review only')
 await request.post('http://127.0.0.1:8103/__test__/reset')
 await context.addCookies([{name:'session',value:'local-browser-test',url:baseURL!}])
})
for(const format of ['pdf','multi','png','jpg','csv','xlsx','failed'])test(`fitted ${format} original and authorized full-view link`,async({page,context})=>{
 const loaded=page.waitForResponse(r=>r.url().includes('/api/gst/bills?')); await page.goto('/bills?period=2026-09'); await loaded
 const csv='Supplier GSTIN,Invoice Number,Invoice Date (DD-MM-YYYY),HSN/SAC,Description,Taxable Value,GST Rate %,CGST,SGST,IGST,Cess,Invoice Total,Place of Supply (State Code),Reverse Charge (Y/N)\n33ABCDE1234F1Z1,PREVIEW-TEST,01-09-2026,8703,Synthetic item,1000,18,90,90,0,0,1180,33,N'
 await page.getByLabel('Upload bills',{exact:true}).setInputFiles({name:'preview.csv',mimeType:'text/csv',buffer:Buffer.from(csv.replace('PREVIEW-TEST','PREVIEW-'+format))})
 const row=page.locator('.bills-table tr').filter({hasText:'PREVIEW-'+format})
 await expect(row).toBeVisible()
 const invoice=(await (await page.request.get('/api/gst/bills?period=2026-09')).json()).invoices[0]
 const ext=['multi','failed'].includes(format)?'pdf':format
 await page.route(`**/api/gst/bills/${invoice.invoice_id}`,async route=>{
  const data=await (await route.fetch()).json();data.extraction.raw_ref=`private/synthetic.${ext}`
  await route.fulfill({json:data})
 })
 const original=`/api/gst/bills/${invoice.invoice_id}/original`
 await context.route(`**${original}`,route=>{
  if(format==='failed')return route.fulfill({status:503,body:'Unavailable'})
  if(['csv','xlsx'].includes(format))return route.fulfill({body:csv,contentType:'text/csv'})
  const file=format==='multi'?'edge_cases/multi_page.pdf':`manufacturing/29ZXZCZ0100Q1ZI_NL-MAN-001.${format}`
  return route.fulfill({body:readFileSync(path.resolve('..','demo bills',file)),contentType:ext==='pdf'?'application/pdf':ext==='jpg'?'image/jpeg':'image/png'})
 })
 await row.getByRole('button',{name:'Review',exact:true}).click()
 const preview=page.getByRole('link',{name:'Open full original invoice',exact:true})
 await expect(preview).toHaveAttribute('href',original)
 await expect(page.getByRole('link',{name:'View Original Bill',exact:true})).toHaveAttribute('href',original)
 if(['pdf','multi','png','jpg'].includes(format)){
  await expect(preview.locator('img')).toBeVisible()
  await expect(preview.locator('img')).toHaveCSS('object-fit','contain')
  if(format==='pdf')await expect(page.getByRole('status').filter({hasText:'Page 1 of 1'})).toBeVisible()
  if(format==='multi')await expect(page.getByRole('status').filter({hasText:'Page 1 of 2'})).toBeVisible()
 }else await expect(preview).toContainText(format==='failed'?'Preview unavailable':'Spreadsheet original')
 await preview.focus()
 const navigation=context.waitForEvent('request',r=>r.url().endsWith(original)&&r.isNavigationRequest());await page.keyboard.press('Enter');await navigation
 for(const tab of context.pages())if(tab!==page)await tab.close()
 for(const width of [1440,900,390]){
  await page.setViewportSize({width,height:1000})
  expect(await page.locator('.bill-review-drawer').evaluate(el=>el.scrollWidth<=el.clientWidth)).toBeTruthy()
  expect(await preview.evaluate(el=>el.scrollWidth<=el.clientWidth)).toBeTruthy()
  if(format==='pdf')await page.screenshot({path:`../artifacts/gst_easy_v2/review-${width}.png`,fullPage:true})
 }
 await page.getByLabel('Supplier legal name',{exact:true}).fill('Synthetic corrected supplier')
 await page.getByRole('button',{name:'Save changes',exact:true}).click()
 await expect(page.getByText('Bill updated. Checks have been refreshed.',{exact:true})).toBeVisible()
})
