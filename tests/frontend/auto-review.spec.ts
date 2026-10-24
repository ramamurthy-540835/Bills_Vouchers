import {test,expect} from '../../frontend/node_modules/@playwright/test'

const fixtureURL=process.env.BV_LOCAL_FIXTURE_API||'http://127.0.0.1:8103'

test.beforeEach(async({request,context,baseURL})=>{
 test.skip(Boolean(process.env.BV_TEST_URL)&&!process.env.BV_LOCAL_FIXTURE_API,'Local synthetic fixture only')
 await request.post(`${fixtureURL}/__test__/reset`)
 await request.post(`${fixtureURL}/__test__/auto-review`)
 await context.addCookies([{name:'session',value:'local-browser-test',url:baseURL!}])
})

test('opt-in persists, runs authorized confirmation and OFF preserves confirmation',async({page})=>{
 await page.goto('/bills?period=2026-09&invoice=auto-synthetic')
 const toggle=page.getByRole('switch',{name:'Auto Review',exact:true})
 await expect(toggle).toHaveAttribute('aria-checked','false')
 await toggle.focus();await page.keyboard.press('Space')
 await expect(toggle).toHaveAttribute('aria-checked','true')
 await page.reload()
 await expect(toggle).toHaveAttribute('aria-checked','true')
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000})
  expect(await page.locator('.bill-review-drawer').evaluate(el=>el.scrollWidth<=el.clientWidth)).toBeTruthy()
  await page.screenshot({path:`../artifacts/auto-review/review-${width}.png`,fullPage:true})
 }
 await page.getByRole('button',{name:'Run Auto Review',exact:true}).click()
 await expect(page.getByText('Auto Confirmed',{exact:true})).toBeVisible()
 await toggle.click()
 await expect(toggle).toHaveAttribute('aria-checked','false')
 await expect(page.getByText('This bill is confirmed. Turning OFF does not undo confirmation.')).toBeVisible()
 await expect(page.getByRole('link',{name:'View Original Bill',exact:true})).toBeVisible()
})

test('unavailable approved GST policy produces manual exception, not false success',async({page,request})=>{
 await request.post('http://127.0.0.1:8103/__test__/auto-review?approved=false')
 await page.goto('/bills?period=2026-09&invoice=auto-synthetic')
 await page.getByRole('switch',{name:'Auto Review',exact:true}).click()
 await page.getByRole('button',{name:'Run Auto Review',exact:true}).click()
 await expect(page.getByText('Manual Review Required',{exact:true})).toBeVisible()
 await expect(page.getByRole('region',{name:'Auto Review controls'}).getByText(/no unique current approved rate/)).toBeVisible()
})

test('viewer cannot enable Auto Review',async({page,request})=>{
 await request.post('http://127.0.0.1:8103/__test__/viewer')
 await page.goto('/bills?period=2026-09&invoice=auto-synthetic')
 await expect(page.getByRole('switch',{name:'Auto Review',exact:true})).toBeDisabled()
 await expect(page.getByRole('button',{name:'Run Auto Review',exact:true})).toHaveCount(0)
})

test('batch opt-in permits per-file exclusions before upload',async({page})=>{
 await page.goto('/bills?period=2026-09')
 await page.getByRole('switch',{name:'Auto Review All Eligible Bills',exact:true}).check()
 await page.getByLabel('Upload bills',{exact:true}).setInputFiles([
  {name:'first.csv',mimeType:'text/csv',buffer:Buffer.from('synthetic')},
  {name:'second.csv',mimeType:'text/csv',buffer:Buffer.from('synthetic')},
 ])
 await page.getByRole('checkbox',{name:'Auto Review second.csv',exact:true}).uncheck()
 const choices:string[]=[]
 await page.route('**/api/gst/bills/upload?*',route=>{
  choices.push(new URL(route.request().url()).searchParams.get('auto_review')!)
  return route.fulfill({json:{job_id:'test',status:'completed',files:[{filename:'synthetic.csv',status:'ready',invoice_ids:[]}]}})
 })
 await page.getByRole('button',{name:'Upload selected bills',exact:true}).click()
 await expect.poll(()=>choices).toEqual(['true','false'])
 await expect(page.getByRole('switch',{name:'Auto Review All Eligible Bills',exact:true})).not.toBeChecked()
})

test('reviewer can retain source unit price and tax-inclusive basis',async({page})=>{
 await page.goto('/bills?period=2026-09&invoice=auto-synthetic')
 await page.getByLabel('Unit price',{exact:true}).fill('1180')
 await page.getByLabel('Price basis',{exact:true}).selectOption('tax_inclusive')
 await page.getByRole('button',{name:'Save changes',exact:true}).click()
 await expect(page.getByText('Bill updated. Checks have been refreshed.')).toBeVisible()
 await page.reload()
 await expect(page.getByLabel('Unit price',{exact:true})).toHaveValue('1180')
 await expect(page.getByLabel('Price basis',{exact:true})).toHaveValue('tax_inclusive')
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000})
  expect(await page.locator('.bill-review-drawer').evaluate(el=>el.scrollWidth<=el.clientWidth)).toBeTruthy()
  await page.screenshot({path:`../artifacts/auto-review/source-price-${width}.png`,fullPage:true})
 }
})
