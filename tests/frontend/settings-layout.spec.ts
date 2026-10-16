import {test,expect} from '../../frontend/node_modules/@playwright/test'
test.beforeEach(async({context,request,baseURL})=>{
 test.skip(Boolean(process.env.BV_TEST_URL),'Local synthetic settings only')
 await request.post('http://127.0.0.1:8103/__test__/reset')
 await context.addCookies([{name:'session',value:'local-browser-test',url:baseURL!}])
})
test('Settings status rows, actions and responsive layouts',async({page})=>{
 for(const [path,name] of [['/settings/profile','profile'],['/settings/account','account'],['/help','help']]){
  await page.setViewportSize({width:1440,height:1000});await page.goto(path)
  if(name==='profile'){
   await expect(page.getByRole('heading',{name:'Business Preferences'})).toBeVisible()
   await expect(page.getByText('Monthly',{exact:true})).toBeVisible()
   const save=page.getByRole('button',{name:'Save business details'})
   expect(await save.evaluate((button:HTMLButtonElement)=>button.form?.id)).toBe('business-details-form')
   await expect(page.getByRole('link',{name:'Manage your business team'})).toHaveAttribute('href','/settings/members')
  }
  if(name==='account'){
   await expect(page.getByText('Unverified',{exact:true})).toBeVisible()
   await expect(page.getByRole('link',{name:'Update personal contact details'})).toHaveAttribute('href','/settings/me')
   await expect(page.getByRole('link',{name:'Contact Support'})).toHaveAttribute('href','/help')
  }
  if(name==='help'){
   for(const title of ['Getting Started','Team Access','Account Help','Important Notes'])await expect(page.getByRole('heading',{name:title,exact:true})).toBeVisible()
   await expect(page.getByRole('navigation',{name:'Help quick links'}).getByRole('link')).toHaveCount(3)
  }
  await page.screenshot({path:`../artifacts/gst_easy/settings-${name}-desktop.png`,fullPage:true})
  await page.setViewportSize({width:390,height:844})
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy()
  await page.screenshot({path:`../artifacts/gst_easy/settings-${name}-mobile.png`,fullPage:true})
 }
 await page.getByRole('navigation',{name:'Help quick links'}).getByRole('link',{name:'Business Profile'}).click()
 await expect(page).toHaveURL(/settings\/profile/)
})
