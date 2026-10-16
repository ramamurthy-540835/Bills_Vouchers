import {test,expect} from '../../frontend/node_modules/@playwright/test'
test.beforeEach(async({context,request,baseURL})=>{
 test.skip(Boolean(process.env.BV_TEST_URL),'Local UI verification only')
 await request.post('http://127.0.0.1:8103/__test__/reset')
 await context.addCookies([{name:'session',value:'local-browser-test',url:baseURL!}])
})
test('dashboard and bills controls fit desktop tablet and mobile',async({page})=>{
 for(const [width,label] of [[1440,'desktop'],[1000,'tablet'],[390,'mobile']] as const){
  await page.setViewportSize({width,height:1000})
  await page.goto('/gst/workspace?period=2026-09')
  await expect(page.locator('[aria-label="Dashboard filters"]+section')).toHaveAttribute('aria-label','Manage your invoices')
  await expect(page.locator('.gst-upload-section+section')).toHaveAttribute('aria-label','GST summary')
  if(width===1440){
   await expect.poll(()=>page.locator('.gst-dashboard-period-controls').evaluateAll(elements=>{
    if(!elements.length)return false
    const label=elements[0].querySelector('label')!.getBoundingClientRect(),select=elements[0].querySelector('select')!.getBoundingClientRect(),button=elements[0].querySelector('button')!.getBoundingClientRect()
    return select.x-label.right>=24&&button.x-select.right>=24&&Math.abs(select.y-button.y)<3
   })).toBe(true)
  }
  await page.getByRole('button',{name:'Refresh dashboard',exact:true}).click()
  await expect(page.getByRole('region',{name:'GST summary'})).toHaveAttribute('aria-busy','false')
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy()
  await page.evaluate(()=>window.scrollTo(0,0))
  await page.screenshot({path:`../artifacts/gst_easy/polish-dashboard-${label}.png`,fullPage:true})
  await page.getByRole('region',{name:'Manage your invoices'}).getByRole('link',{name:'Upload Bills',exact:true}).click()
  await expect(page.getByLabel('Upload bills',{exact:true})).toBeEnabled()
  await expect(page.getByRole('heading',{name:'Upload History & Deleted Bills'})).toBeVisible()
  await page.getByRole('button',{name:'View Upload History',exact:true}).click()
  await expect(page.getByText('No upload jobs for this period.')).toBeVisible()
  await page.getByRole('button',{name:'View Deleted Bills',exact:true}).click()
  await expect(page.getByText('No deleted bills for this period.')).toBeVisible()
  const filtered=page.waitForResponse(response=>response.url().includes('/api/gst/bills?')&&response.url().includes('status=confirmed'))
  await page.getByLabel('Bill status',{exact:true}).selectOption('confirmed')
  expect((await filtered).status()).toBe(200)
  const download=page.waitForEvent('download')
  await page.getByRole('link',{name:'Export purchase register',exact:true}).click()
  expect((await download).suggestedFilename()).toMatch(/\.xlsx$/)
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy()
  await page.evaluate(()=>window.scrollTo(0,0))
  await page.screenshot({path:`../artifacts/gst_easy/polish-bills-${label}.png`,fullPage:true})
 }
})
