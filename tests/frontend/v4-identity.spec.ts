import {test,expect} from '../../frontend/node_modules/@playwright/test'

test.beforeEach(()=>test.skip(Boolean(process.env.BV_TEST_URL),'Local isolated identity response tests'))

test('forgot-password navigation requests recovery rather than verification',async({page})=>{
 let purpose=''
 await page.route('**/api/auth/request-link',route=>{purpose=route.request().postDataJSON().purpose;return route.fulfill({json:{message:'Password reset requested. Check your inbox and spam folder.'}})})
 await page.goto('/login')
 await page.getByRole('link',{name:'Forgot password?'}).click()
 await expect(page.getByRole('heading',{name:'Forgot password',exact:true})).toBeVisible()
 await page.getByLabel('Email',{exact:true}).fill('synthetic@example.test')
 await page.getByRole('button',{name:'Send password reset email'}).click()
 expect(purpose).toBe('reset')
 await expect(page.getByRole('status')).toContainText('Password reset requested')
 await expect(page.getByRole('heading',{name:'Verify your email'})).toHaveCount(0)
})

test('expired recovery link retains entries and offers a new reset link',async({page})=>{
 const token=crypto.randomUUID()+crypto.randomUUID()
 await page.route('**/api/auth/reset-password',route=>route.fulfill({status:422,json:{error:{message:'This link is invalid, expired or already used. Request a new link.'}}}))
 await page.goto('/reset-password#token='+token)
 await expect(page.getByRole('button',{name:'Reset password',exact:true})).toBeVisible()
 expect(page.url()).not.toContain(token)
 const password='A1'+crypto.randomUUID()
 await page.getByLabel('New password',{exact:true}).fill(password)
 await page.getByLabel('Confirm password',{exact:true}).fill(password)
 await page.getByRole('button',{name:'Reset password',exact:true}).click()
 await expect(page.locator('.auth-card').getByRole('alert')).toContainText('expired')
 await expect(page.getByLabel('New password',{exact:true})).toHaveValue(password)
 await page.getByRole('link',{name:'Request a new password reset link'}).click()
 await expect(page.getByRole('heading',{name:'Forgot password',exact:true})).toBeVisible()
})

test('verification resend has its own purpose and does not claim inbox delivery',async({page})=>{
 let purpose=''
 await page.route('**/api/auth/request-link',route=>{purpose=route.request().postDataJSON().purpose;return route.fulfill({json:{message:'Verification email requested. Check your inbox and spam folder.'}})})
 await page.goto('/verify-email')
 await page.getByLabel('Email',{exact:true}).fill('synthetic@example.test')
 await page.getByRole('button',{name:'Send verification email'}).click()
 expect(purpose).toBe('verify')
 await expect(page.getByRole('status')).toContainText('Verification email requested')
})
