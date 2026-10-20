import {test,expect} from '../../frontend/node_modules/@playwright/test'
test.beforeEach(async({context,request,baseURL})=>{
 test.skip(Boolean(process.env.BV_TEST_URL),'Local synthetic website fixture only')
 await request.post('http://127.0.0.1:8103/__test__/reset')
 await context.addCookies([{name:'session',value:'local-browser-test',url:baseURL!}])
})
test('Website validates, saves, edits, cancels and isolates business context',async({page})=>{
 let website='',version='website-version-0',writes=0
 await page.route('**/api/settings/account',async route=>{
  const response=await route.fetch();const data=await response.json()
  if(data.client_id==='browser-client'){data.profile.website_url=website;data.profile.profile_id=version}
  await route.fulfill({response,json:data})
 })
 await page.route('**/api/settings/profile',async route=>{
  const body=route.request().postDataJSON();expect(body.client_id).toBe('browser-client')
  if(writes)expect(body.profile_id).toBe(version)
  expect(Object.keys(body).sort()).toEqual(writes?['client_id','profile_id','website_url']:['client_id','website_url'])
  website=body.website_url;version=`website-version-${++writes}`
  await route.fulfill({json:{saved:true}})
 })
 await page.goto('/settings/profile')
 const input=page.getByLabel('Website URL',{exact:true})
 await expect(input).toBeVisible()
 for(const invalid of ['red taxi','abc','@@@','javascript:alert(1)','https://name:password@example.com']){
  await input.fill(invalid);await page.getByRole('button',{name:'Save Website',exact:true}).click()
  await expect(page.locator('.website-editor [role=alert]')).toBeVisible()
 }
 expect(writes).toBe(0)
 await input.fill('  example.com/company  ');await page.getByRole('button',{name:'Save Website',exact:true}).click()
 await expect(page.getByRole('link',{name:'Open Website'})).toHaveAttribute('href','https://example.com/company')
 await expect(page.locator('.website-editor [role=status]')).toHaveText('Company website saved successfully.')
 await page.getByRole('button',{name:'Edit Website'}).click();await input.fill('https://changed.example.com')
 await page.locator('.website-editor').getByRole('button',{name:'Cancel',exact:true}).click()
 await page.getByRole('button',{name:'Edit Website'}).click();await expect(input).toHaveValue('https://example.com/company')
 await input.fill('http://example.org');await page.getByRole('button',{name:'Save Website',exact:true}).click()
 await expect(page.getByRole('link',{name:'Open Website'})).toHaveAttribute('href','http://example.org/')
 await page.locator('.website-editor').screenshot({path:'../artifacts/gst_easy/website-desktop.png'})
 await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'Edit Website'}).click()
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy()
 await page.locator('.website-editor').screenshot({path:'../artifacts/gst_easy/website-mobile.png'})
 await page.getByRole('button',{name:'Switch to Business Synthetic Read Only',exact:true}).click()
 await expect(page.getByLabel('Legal name',{exact:true})).toHaveValue('Synthetic Read Only')
 await expect(input).toHaveCount(0)
 await expect(page.getByRole('button',{name:'Save Website'})).toHaveCount(0)
 await expect(page.locator('.website-editor')).not.toContainText('http://example.org/')
 await page.unrouteAll({behavior:'wait'})
})
