import {test,expect} from '../../frontend/node_modules/@playwright/test'
const png=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aJ1cAAAAASUVORK5CYII=','base64')
test.beforeEach(async({context,request,baseURL})=>{
 test.skip(Boolean(process.env.BV_TEST_URL),'Synthetic local tests only')
 await request.post('http://127.0.0.1:8103/__test__/reset')
 await context.addCookies([{name:'session',value:'local-browser-test',url:baseURL!}])
})
test('Shared uploader empty, upload, replace, failure and remove states',async({page})=>{
 const png=Buffer.from(await page.evaluate(()=>{const canvas=document.createElement('canvas');canvas.width=160;canvas.height=80;const ctx=canvas.getContext('2d')!;ctx.fillStyle='#187653';ctx.fillRect(0,0,160,80);ctx.fillStyle='#ffffff';ctx.font='bold 28px sans-serif';ctx.textAlign='center';ctx.fillText('TEST',80,50);return canvas.toDataURL('image/png').split(',')[1]}),'base64')
 let exists=false,fail=false,posts=0
 await page.route('**/api/settings/profile/logo*',async route=>{
  if(route.request().method()==='POST'){posts++;if(fail)return route.fulfill({status:422,json:{detail:'Invalid image content.'}});exists=true;return route.fulfill({json:{ok:true}})}
  if(route.request().method()==='DELETE'){exists=false;return route.fulfill({json:{ok:true}})}
  return exists?route.fulfill({contentType:'image/png',body:png}):route.fulfill({status:404,json:{detail:'Not found'}})
 })
 await page.goto('/settings/profile')
 const card=page.getByRole('region',{name:'Business Branding',exact:true})
 await expect(card.getByText('No logo uploaded',{exact:true})).toBeVisible()
 await expect(card.getByRole('button',{name:'Upload Logo',exact:true})).toHaveCSS('background-color','rgb(24, 118, 83)')
 await card.screenshot({path:'../artifacts/gst_easy/logo-empty.png'})
 const chooser=page.waitForEvent('filechooser');await card.getByRole('button',{name:'Upload Logo',exact:true}).click()
 await (await chooser).setFiles({name:'logo.png',mimeType:'image/png',buffer:png})
 await expect(card.getByRole('status')).toHaveText('Logo saved.')
 await expect(card.getByRole('button',{name:'Replace Logo'})).toBeVisible()
 await expect(card.getByRole('img')).toBeVisible()
 await expect.poll(()=>card.getByRole('img').evaluate((img:HTMLImageElement)=>img.naturalWidth)).toBe(160)
 await expect(card.getByRole('img')).toHaveCSS('object-fit','contain')
 await card.screenshot({path:'../artifacts/gst_easy/logo-uploaded.png'})
 fail=true
 await card.getByLabel('Choose business logo').setInputFiles({name:'logo.png',mimeType:'image/png',buffer:png})
 await expect(card.getByRole('alert')).toHaveText('Invalid image content.')
 await expect(card.getByRole('img')).toBeVisible()
 await card.getByLabel('Choose business logo').setInputFiles({name:'bad.png',mimeType:'image/png',buffer:Buffer.from('<svg/>')})
 await expect(card.getByRole('alert')).toContainText('Choose a PNG, JPEG or WebP image')
 await card.getByLabel('Choose business logo').setInputFiles({name:'large.png',mimeType:'image/png',buffer:Buffer.alloc(2*1024*1024+1)})
 await expect(card.getByRole('alert')).toHaveText('Choose a logo up to 2 MB.')
 expect(posts).toBe(2)
 fail=false
 await card.getByLabel('Choose business logo').setInputFiles({name:'replacement.png',mimeType:'image/png',buffer:png})
 await expect(card.getByRole('status')).toHaveText('Logo saved.')
 await page.setViewportSize({width:390,height:844})
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy()
 await card.screenshot({path:'../artifacts/gst_easy/logo-mobile.png'})
 page.once('dialog',dialog=>dialog.accept());await card.getByRole('button',{name:'Remove Logo'}).click()
 await expect(card.getByText('No logo uploaded',{exact:true})).toBeVisible()
 await page.goto('/settings/onboarding')
 await expect(card.getByRole('button',{name:'Upload Logo',exact:true})).toBeVisible()
 await expect(card.getByRole('button',{name:'Upload Logo',exact:true})).toHaveCSS('color','rgb(255, 255, 255)')
})
test('Switching clears the preview and viewer cannot edit',async({page})=>{
 let current=true
 await page.route('**/api/settings/profile/logo*',route=>current?route.fulfill({contentType:'image/png',body:png}):route.fulfill({status:404,json:{detail:'Not found'}}))
 await page.goto('/settings/profile')
 const card=page.getByRole('region',{name:'Business Branding',exact:true})
 await expect(card.getByRole('img')).toBeVisible()
 current=false
 await page.getByRole('button',{name:'Switch to Business Synthetic Read Only',exact:true}).click()
 await expect(page.getByLabel('Legal name',{exact:true})).toHaveValue('Synthetic Read Only')
 await expect(card.getByText('No logo uploaded',{exact:true})).toBeVisible()
 await expect(card.getByRole('img')).toHaveCount(0)
 await expect(card.getByRole('button')).toHaveCount(0)
 await expect(card.getByText('Read-only access')).toBeVisible()
})
