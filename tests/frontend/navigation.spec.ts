import {test,expect} from '../../frontend/node_modules/@playwright/test'

test.beforeEach(async({context,request,baseURL})=>{
 test.skip(Boolean(process.env.BV_TEST_URL),'Local synthetic role fixtures only')
 await request.post('http://127.0.0.1:8103/__test__/reset')
 await context.addCookies([{name:'session',value:'local-browser-test',url:baseURL!}])
})

for(const role of ['client','viewer','tax_admin','admin']){
 test(`${role} menus, protected routes and mobile controls`,async({page,request})=>{
  await request.post(`http://127.0.0.1:8103/__test__/role/${role}`)
  await page.goto('/settings/profile')
  await expect(page.getByRole('img',{name:'Business logo',exact:true})).toHaveCount(0)
  const sidebar=page.getByRole('navigation',{name:'Main navigation'})
  await expect(sidebar.getByRole('link',{name:'Workspace Administration'})).toHaveCount(role==='admin'?1:0)
  await expect(page.getByRole('link',{name:'Manage your business team'})).toHaveCount(role==='client'?1:0)
  await expect(page.getByRole('button',{name:'Save business details'})).toHaveCount(role==='viewer'?0:1)
  await expect(page.getByRole('button',{name:'Save GSTIN'})).toHaveCount(role==='viewer'?0:1)
  await page.getByLabel('Account menu',{exact:true}).click()
  const menu=page.locator('.account-popover')
  await expect(menu.getByRole('link')).toHaveText(['My Profile','Business Profile','Account Settings','Change Password','Help & Support'])
  await expect(menu.getByRole('button',{name:'Logout'})).toBeVisible()
  await expect(menu).not.toContainText(/Administration|Workspace access|Notifications|Infrastructure/)
  await page.screenshot({path:`../artifacts/gst_easy/local-rbac-${role}-desktop.png`,fullPage:true})
  await page.keyboard.press('Escape');await expect(menu).not.toBeVisible()
  await expect(page.getByLabel('Account menu',{exact:true})).toBeFocused()
  await page.keyboard.press('Enter');await expect(menu).toBeVisible()
  await page.getByRole('heading',{name:'Business Profile',exact:true}).click();await expect(menu).not.toBeVisible()
  await page.reload();await expect(sidebar.getByRole('link',{name:'Workspace Administration'})).toHaveCount(role==='admin'?1:0)
  await page.setViewportSize({width:390,height:844})
  await page.getByLabel('Account menu',{exact:true}).click()
  await expect(menu).toBeVisible()
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy()
  await page.screenshot({path:`../artifacts/gst_easy/local-rbac-${role}-mobile.png`,fullPage:true})
  await menu.getByRole('link',{name:'My Profile',exact:true}).click()
  await expect(page).toHaveURL(/settings\/me/)
  await expect(page.locator('.account-popover')).not.toBeVisible()
  await expect(page.getByRole('textbox',{name:'Email Address Email verified',exact:true})).toHaveAttribute('readonly','')
  await expect(page.getByText('Email verified',{exact:true})).toBeVisible()
  await page.goto('/admin/workspace')
  await expect(page.getByRole('heading',{name:role==='admin'?'Selected workspace administration':'Access denied',exact:true})).toBeVisible()
  expect((await page.request.get('/api/admin/workspace')).status()).toBe(role==='admin'?200:403)
  if(role!=='client'){
   await page.goto('/settings/members');await expect(page.getByRole('heading',{name:'Access denied'})).toBeVisible()
  }
 })
}

test('revocation refreshes navigation and blocks existing privileged page',async({page,request})=>{
 await request.post('http://127.0.0.1:8103/__test__/role/admin')
 await page.goto('/admin/workspace')
 await expect(page.getByRole('heading',{name:'Selected workspace administration'})).toBeVisible()
 await request.post('http://127.0.0.1:8103/__test__/role/viewer')
 await page.evaluate(()=>window.dispatchEvent(new Event('focus')))
 await expect(page.getByRole('heading',{name:'Access denied'})).toBeVisible()
 expect((await page.request.get('/api/admin/workspace')).status()).toBe(403)
})

test('separate account and password pages keep password visibility accessible',async({page})=>{
 await page.goto('/settings/account')
 await expect(page.getByRole('heading',{name:'Account security'})).toBeVisible()
 await expect(page.getByRole('heading',{name:'Business details'})).toHaveCount(0)
 await page.getByRole('link',{name:'Change Password',exact:true}).click()
 const password=page.getByLabel('New password',{exact:true})
 await password.fill('LocalSyntheticPassword123')
 await page.getByRole('button',{name:'Show password',exact:true}).first().click()
 await expect(password).toHaveAttribute('type','text')
 await page.getByRole('button',{name:'Hide password',exact:true}).click()
 await expect(password).toHaveValue('LocalSyntheticPassword123')
 await page.goto('/help');await expect(page.getByRole('heading',{name:'Using GST Easy'})).toBeVisible()
})

test('business switching reloads membership permissions without retaining edit controls',async({page})=>{
 await page.goto('/settings/profile')
 await expect(page.getByRole('button',{name:'Save business details'})).toBeVisible()
 await page.getByLabel('Account menu',{exact:true}).click()
 await page.getByLabel('Switch business',{exact:true}).selectOption('browser-readonly')
 await expect(page.getByRole('button',{name:'Save business details'})).toHaveCount(0)
 await expect(page.getByRole('link',{name:'Manage your business team'})).toHaveCount(0)
 await page.reload()
 await expect(page.getByRole('button',{name:'Save GSTIN'})).toHaveCount(0)
})


test('selected business profile and dashboard survive refresh and mobile switching',async({page})=>{
 await page.goto('/settings/profile')
 const links=await page.locator('.bv-sidebar nav a').allTextContents()
 await page.getByLabel('Account menu',{exact:true}).click()
 await page.getByLabel('Switch business',{exact:true}).selectOption('browser-readonly')
 await expect(page.getByLabel('Selected business',{exact:true})).toHaveText('Synthetic Read Only')
 expect(await page.locator('.bv-sidebar nav a').allTextContents()).toEqual(links)
 await page.goto('/gst/workspace?period=2026-10')
 await expect(page.getByLabel('Selected business',{exact:true})).toHaveText('Synthetic Read Only')
 expect((await (await page.request.get('/api/gst/bills/dashboard?period=2026-10')).json()).client_id).toBe('browser-readonly')
 await page.reload()
 await expect(page.getByLabel('Selected business',{exact:true})).toHaveText('Synthetic Read Only')
 await page.setViewportSize({width:390,height:844})
 await page.getByLabel('Account menu',{exact:true}).click()
 await page.getByLabel('Switch business',{exact:true}).selectOption('browser-client')
 await expect(page.getByLabel('Selected business',{exact:true})).toHaveText('Red Taxi')
 expect((await page.request.post('/api/workspace/client',{data:{client_id:'unrelated'}})).status()).toBe(403)
 expect((await (await page.request.get('/api/settings/account')).json()).client_id).toBe('browser-client')
})

test('restricted business hides reports and redirects an unavailable module',async({page})=>{
 await page.goto('/reports?period=2026-10&invoice_id=previous-business')
 await page.getByLabel('Account menu',{exact:true}).click()
 await page.getByLabel('Switch business',{exact:true}).selectOption('browser-sample')
 await expect(page).toHaveURL(/gst\/workspace\?period=2026-10(?:&range=month)?$/)
 await expect(page.locator('.bv-sidebar nav').getByRole('link',{name:'Reports',exact:true})).toHaveCount(0)
 expect((await page.request.get('/api/gst/bills/reports?period=2026-10')).status()).toBe(403)
 await page.goto('/reports?period=2026-10')
 await expect(page).toHaveURL(/gst\/workspace/)
 await page.reload()
 await expect(page.locator('.bv-sidebar nav').getByRole('link',{name:'Reports',exact:true})).toHaveCount(0)
})


test('switching businesses isolates invoices and rejects foreign invoice URLs',async({page})=>{
 await page.goto('/bills?period=2026-09')
 const csv='Supplier GSTIN,Invoice Number,Invoice Date (DD-MM-YYYY),HSN/SAC,Description,Taxable Value,GST Rate %,CGST,SGST,IGST,Cess,Invoice Total,Place of Supply (State Code),Reverse Charge (Y/N)\n33ABCDE1234F1Z1,ISOLATION-A,01-09-2026,8703,Vehicle,1000,18,90,90,0,0,1180,33,N'
 await expect(page.getByLabel('Loading bills')).toHaveCount(0)
 await expect(page.getByText('No bills for this period yet.',{exact:true})).toBeVisible()
 await page.getByLabel('Upload bills',{exact:true}).setInputFiles({name:'isolation.csv',mimeType:'text/csv',buffer:Buffer.from(csv)})
 await expect(page.getByText('ISOLATION-A',{exact:true})).toBeVisible()
 const response=await (await page.request.get('/api/gst/bills?period=2026-09')).json()
 const invoice=response.invoices[0]
 await page.getByLabel('Account menu',{exact:true}).click()
 await page.getByLabel('Switch business',{exact:true}).selectOption('browser-readonly')
 await expect(page.getByLabel('Selected business',{exact:true})).toHaveText('Synthetic Read Only')
 await expect(page.getByText('ISOLATION-A',{exact:true})).toHaveCount(0)
 expect((await page.request.get(`/api/gst/bills/${invoice.invoice_id}`)).status()).toBe(404)
 await page.getByLabel('Account menu',{exact:true}).click()
 await page.getByLabel('Switch business',{exact:true}).selectOption('browser-client')
 await expect(page.getByText('ISOLATION-A',{exact:true})).toBeVisible()
})


test('GST Easy navigation and upload entry points remain scoped to their screens',async({page})=>{
 await page.goto('/gst/workspace?period=2026-09')
 const sidebar=page.getByRole('navigation',{name:'Main navigation'})
 await expect(sidebar.getByRole('link').first()).toHaveText('GST Easy')
 await expect(sidebar.getByRole('link')).toHaveText(['GST Easy','Bills & Vouchers','Returns & Credit','Reports','Search','AI Assistant'])
 await expect(page.getByRole('heading',{name:'GST Easy',exact:true})).toBeVisible()
 await page.getByRole('link',{name:'Upload Bills',exact:true}).click()
 await expect(page).toHaveURL(/bills\?period=2026-09/)
 await expect(page.getByLabel('Upload bills',{exact:true})).toBeEnabled()
 await page.goto('/gst/filing?period=2026-09')
 await expect(page.getByRole('link',{name:/Upload.*bills/i})).toHaveCount(0)
 await expect(page.getByLabel('Upload bills',{exact:true})).toHaveCount(0)
 await expect(page.getByLabel('Import GSTR-2B',{exact:true})).toBeEnabled()
 await page.setViewportSize({width:390,height:844})
 await expect(page.locator('.mobile-tabs').getByRole('link',{name:'GST Easy',exact:true})).toBeVisible()
 await expect(page.locator('.mobile-tabs .nav-item')).toHaveText(['GST Easy','Bills & Vouchers','Returns & Credit','Reports','Search','AI Assistant'])
})


test('dashboard grid is 3-2-1, summary-only, with uploads before KPIs and reports centralized',async({page})=>{
 await page.goto('/gst/workspace?period=2026-09')
 const grid=page.getByRole('region',{name:'GST summary'})
 await expect(grid.locator('.metric-card')).toHaveCount(9)
 await expect(grid.locator('a')).toHaveCount(0)
 const values=await grid.locator('.metric-card>strong').allTextContents()
 for(const [width,columns,label] of [[1440,3,'desktop'],[1000,2,'tablet'],[390,1,'mobile']] as const){
  await page.setViewportSize({width,height:1000})
  expect(await grid.evaluate(el=>getComputedStyle(el).gridTemplateColumns.split(' ').length)).toBe(columns)
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy()
  const boxes=await grid.locator('.metric-card').evaluateAll(cards=>cards.map(card=>({y:card.getBoundingClientRect().y,w:card.getBoundingClientRect().width})))
  expect(new Set(boxes.map(box=>Math.round(box.y))).size).toBe(Math.ceil(9/columns))
  expect(new Set(boxes.map(box=>Math.round(box.w))).size).toBe(1)
  await expect(page.locator('[aria-label="Dashboard filters"]+section')).toHaveAttribute('aria-label','Manage your invoices')
  await page.screenshot({path:`../artifacts/gst_easy/dashboard-redesign-${label}.png`,fullPage:true})
 }
 expect(await grid.locator('.metric-card>strong').allTextContents()).toEqual(values)
 await page.getByRole('link',{name:'Upload Bills'}).click()
 await expect(page.getByLabel('Upload bills',{exact:true})).toBeEnabled()
 await page.goto('/reports?period=2026-09')
 const catalog=page.getByLabel('Report categories')
 await expect(catalog.getByRole('link')).toHaveCount(9)
 for(const kind of ['credit','liability','cash','without_itc','sales','purchases','pending','mismatches','unmatched']){
  await page.getByLabel('Report',{exact:true}).selectOption(kind)
  await expect(page.getByText(/Loading report/)).toHaveCount(0)
  await expect(page.getByRole('button',{name:'Download Excel'})).toBeVisible()
  await expect(page.getByRole('region',{name:'Business reports'}).getByRole('alert')).toHaveCount(0)
 }
 await page.screenshot({path:'../artifacts/gst_easy/reports-redesign-mobile.png',fullPage:true})
})


test('profile and support remain available through the account dropdown only',async({page})=>{
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:900})
  await page.goto('/gst/workspace?period=2026-09')
  for(const navigation of [page.locator('.bv-sidebar nav'),page.locator('.mobile-tabs')]){
   await expect(navigation.getByRole('link',{name:'Business Profile',exact:true})).toHaveCount(0)
   await expect(navigation.getByRole('link',{name:'Help & Support',exact:true})).toHaveCount(0)
  }
  await page.getByLabel('Account menu',{exact:true}).click()
  await page.locator('.account-popover').getByRole('link',{name:'Business Profile',exact:true}).click()
  await expect(page).toHaveURL(/settings\/profile/)
  await expect(page.getByRole('heading',{name:'Business Profile',exact:true})).toBeVisible()
  await page.getByLabel('Account menu',{exact:true}).click()
  await page.locator('.account-popover').getByRole('link',{name:'Help & Support',exact:true}).click()
  await expect(page).toHaveURL(/\/help$/)
  await expect(page.getByRole('heading',{name:'Using GST Easy',exact:true})).toBeVisible()
 }
})
