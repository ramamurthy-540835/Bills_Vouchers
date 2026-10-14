const {chromium}=require('../frontend/node_modules/playwright')
const fs=require('fs')
const path=require('path')
const url='https://gst-easy---bills-voucher-web-foovqasysa-el.a.run.app'
;(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH||'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'})
 const checks=[]
 try{
  for(const [name,width,height] of [['desktop',1280,900],['mobile',390,844]]){
   const page=await browser.newPage({viewport:{width,height}})
   await page.goto(url+'/login',{waitUntil:'domcontentloaded'})
   await page.getByRole('link',{name:'Create an account',exact:true}).click()
   await page.getByLabel('Full name',{exact:true}).waitFor()
   for(const label of ['Email','Business name','Mobile number','Password','Confirm password'])await page.getByLabel(label,{exact:true}).waitFor()
   const input=page.getByLabel('Password',{exact:true})
   await input.fill('SyntheticPreviewCheck123')
   await page.getByRole('button',{name:'Show password',exact:true}).first().click()
   if(await input.getAttribute('type')!=='text')throw Error('Password visibility failed')
   await page.getByRole('button',{name:'Hide password',exact:true}).click()
   if(await input.inputValue()!=='SyntheticPreviewCheck123')throw Error('Password value changed')
   if(!await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth))throw Error('Horizontal overflow at '+width)
   fs.mkdirSync(path.join(__dirname,'../artifacts/gst_easy'),{recursive:true})
   await input.fill('')
   await page.screenshot({path:path.join(__dirname,`../artifacts/gst_easy/preview-register-${name}.png`),fullPage:true})
   checks.push({viewport:name,width,registration_fields:true,password_visibility:true,no_horizontal_overflow:true})
   await page.close()
  }
 }finally{await browser.close()}
 const result={url,utc:new Date().toISOString(),result:'passed',checks,account_created:false,authenticated_uat:false}
 fs.writeFileSync(path.join(__dirname,'../artifacts/gst_easy/preview-browser.json'),JSON.stringify(result,null,2))
 console.log(JSON.stringify(result,null,2))
})().catch(error=>{console.error(error);process.exitCode=1})
