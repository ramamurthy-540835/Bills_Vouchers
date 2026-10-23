import {test,expect} from '../../frontend/node_modules/@playwright/test'

test.beforeEach(async({request,context,baseURL})=>{
 test.skip(Boolean(process.env.BV_TEST_URL),'Synthetic local backend only')
 await request.post('http://127.0.0.1:8103/__test__/reset')
 await context.addCookies([{name:'session',value:'local-browser-test',url:baseURL!}])
})

test('empty attention card is absent and default business policy is OFF',async({page})=>{
 await page.goto('/bills?period=2026-09')
 await expect(page.getByRole('switch',{name:'Business Auto Review'})).toHaveAttribute('aria-checked','false')
 await expect(page.getByRole('region',{name:'Requires Attention',exact:true})).toHaveCount(0)
})

test('business scope persists and existing durable batch confirms synthetic eligible bill',async({page,request})=>{
 await request.post('http://127.0.0.1:8103/__test__/auto-review')
 await page.goto('/bills?period=2026-09')
 const intelligence=page.getByRole('region',{name:'Invoice Intelligence',exact:true})
 await expect(page.getByRole('region',{name:'Requires Attention',exact:true})).toBeVisible()
 await page.getByRole('switch',{name:'Business Auto Review'}).click()
 await expect(page.getByLabel('Processing scope')).toHaveValue('both')
 await page.reload()
 await expect(page.getByRole('switch',{name:'Business Auto Review'})).toHaveAttribute('aria-checked','true')
 await intelligence.getByRole('button',{name:'Run Auto Review',exact:true}).click()
 await expect(page.getByRole('region',{name:'Requires Attention',exact:true})).toHaveCount(0)
 await expect(intelligence.locator('dd').first()).toHaveText('1')
 await page.getByRole('switch',{name:'Business Auto Review'}).click()
 await expect(intelligence.locator('dd').first()).toHaveText('1')
})

test('exception labels, details, filters and responsive layout',async({page,request})=>{
 await request.post('http://127.0.0.1:8103/__test__/auto-review?approved=false')
 await page.goto('/bills?period=2026-09')
 await page.getByRole('switch',{name:'Business Auto Review'}).click()
 await page.getByRole('region',{name:'Invoice Intelligence',exact:true}).getByRole('button',{name:'Run Auto Review'}).click()
 const card=page.getByRole('region',{name:'Requires Attention',exact:true})
 await expect(card.getByText('GST rate and applicability require verified policy evidence',{exact:true}).first()).toBeVisible()
 await card.getByText('Validation Details',{exact:true}).click()
 await expect(card.locator('code').first()).toBeVisible()
 for(const width of [1440,768,390]){
  await page.setViewportSize({width,height:1000})
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy()
  await page.evaluate(()=>window.scrollTo(0,0))
  await page.screenshot({path:`../artifacts/auto-review-v3/intelligence-${width}.png`,fullPage:true})
 }
 await page.getByLabel('Exception category').selectOption('gstin')
 await expect(card.getByText('No exceptions match this filter.')).toBeVisible()
})

test('viewer sees read-only intelligence',async({page,request})=>{
 await request.post('http://127.0.0.1:8103/__test__/viewer')
 await page.goto('/bills?period=2026-09')
 await expect(page.getByRole('switch',{name:'Business Auto Review'})).toBeDisabled()
})

test('future scope inherits backend policy and allows a file exclusion',async({page})=>{
 await page.goto('/bills?period=2026-09')
 await page.getByRole('switch',{name:'Business Auto Review'}).click()
 await page.getByLabel('Processing scope').selectOption('future')
 await expect(page.getByRole('region',{name:'Invoice Intelligence',exact:true}).getByRole('button',{name:'Run Auto Review'})).toHaveCount(0)
 await page.getByLabel('Upload bills',{exact:true}).setInputFiles([{name:'inherit.csv',mimeType:'text/csv',buffer:Buffer.from('synthetic')},{name:'exclude.csv',mimeType:'text/csv',buffer:Buffer.from('synthetic')}])
 await page.getByRole('checkbox',{name:'Auto Review exclude.csv',exact:true}).uncheck()
 const choices:(string|null)[]=[]
 await page.route('**/api/gst/bills/upload?*',route=>{choices.push(new URL(route.request().url()).searchParams.get('auto_review'));return route.fulfill({json:{job_id:'synthetic',status:'completed',files:[]}})})
 await page.getByRole('button',{name:'Upload selected bills'}).click()
 await expect.poll(()=>choices).toEqual([null,'false'])
})
