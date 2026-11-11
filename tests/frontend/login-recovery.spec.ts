import {test,expect} from '../../frontend/node_modules/@playwright/test'

test.beforeEach(async()=>{
 test.skip(Boolean(process.env.BV_TEST_URL),'Mocked identity responses are local-only')
})

test('unverified login offers resend without granting a session or losing input',async({page})=>{
 let resend:any=null
 await page.route('**/api/auth/login',route=>route.fulfill({status:403,json:{error:{code:'email_verification_required',message:'Verify your email address before signing in. If your link expired, request a new verification email.'}}}))
 await page.route('**/api/auth/request-link',route=>{resend=route.request().postDataJSON();return route.fulfill({json:{message:'If this account can receive a link, an email will arrive shortly.'}})})
 await page.goto('/login')
 await page.getByLabel('Email',{exact:true}).fill('synthetic@example.test')
 await page.locator('input[type=password]').fill('SyntheticPassword123')
 await page.getByRole('button',{name:'Sign in',exact:true}).click()
 await expect(page.locator('.auth-card').getByRole('alert')).toContainText('link expired')
 await page.getByRole('button',{name:'Resend verification email'}).click()
 await expect(page.locator('.auth-card').getByRole('status')).toContainText('If this account')
 expect(resend).toEqual({email:'synthetic@example.test',purpose:'verify'})
 await expect(page.getByLabel('Email',{exact:true})).toHaveValue('synthetic@example.test')
 await expect(page.locator('input[type=password]')).toHaveValue('SyntheticPassword123')
 expect(new URL(page.url()).pathname).toBe('/login')
 await page.getByLabel('Email',{exact:true}).fill('other@example.test')
 await expect(page.getByRole('button',{name:'Resend verification email'})).toHaveCount(0)
})

test('sign-in transport failures preserve inputs and allow a safe retry',async({page})=>{
 let attempt=0
 await page.route('**/api/auth/login',route=>{attempt++;return attempt===1?route.abort('connectionreset'):route.fulfill({status:429,headers:{'Retry-After':'900'},json:{error:{message:'Too many attempts. Wait 15 minutes before trying again.'}}})})
 await page.goto('/login')
 await page.getByLabel('Email',{exact:true}).fill('synthetic@example.test')
 await page.locator('input[type=password]').fill('SyntheticPassword123')
 await page.getByRole('button',{name:'Sign in',exact:true}).click()
 await expect(page.locator('.auth-card').getByRole('alert')).toContainText('entered details have been kept')
 await expect(page.locator('input[type=password]')).toHaveValue('SyntheticPassword123')
 await page.getByRole('button',{name:'Sign in',exact:true}).click()
 await expect(page.locator('.auth-card').getByRole('alert')).toContainText('Wait 15 minutes')
 await expect(page.getByRole('button',{name:'Resend verification email'})).toHaveCount(0)
 expect(attempt).toBe(2)
})
