// Read-only deployed UI checks. Credentials are supplied through the environment.
const {chromium, request}=require('../frontend/node_modules/@playwright/test');
(async()=>{
 const base=process.env.BV_TEST_URL||'https://preview-v3---bills-voucher-web-foovqasysa-el.a.run.app';
 const api=await request.newContext({baseURL:base});
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
 try{
  const page=await browser.newPage();
  await page.goto(base+'/login');
  await page.getByRole('link',{name:'Create an account'}).click();
  await page.getByRole('heading',{name:'Create your account'}).waitFor();
  console.log('PASS live registration page');
  const login=await api.post('/api/auth/login',{data:{email:process.env.BV_TEST_EMAIL,password:process.env.BV_TEST_PASSWORD}});
  if(!login.ok())throw Error('Login failed: '+login.status());
  const alphabet='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ',prefix='33ABCDE1234F1Z';
  let total=0,factor=2;
  for(const char of [...prefix].reverse()){const value=alphabet.indexOf(char)*factor;total+=Math.floor(value/36)+value%36;factor=factor===2?1:2}
  const gstin=prefix+alphabet[(36-total%36)%36];
  const duplicate=await api.post('/api/auth/register',{headers:{Origin:base},data:{email:process.env.BV_TEST_EMAIL,full_name:'Registration check',business_name:'Registration check',gstin,password:'RegistrationCheck2026'}});
  if(duplicate.status()!==409)throw Error('Duplicate registration should return 409, received '+duplicate.status()+': '+await duplicate.text());
  console.log('PASS duplicate registration blocked');
  const {token}=await (await api.get('/api/auth/csrf')).json();
  const invalidLogo=await api.post('/api/settings/profile/logo',{headers:{Origin:base,'x-csrf-token':token},multipart:{file:{name:'invalid.png',mimeType:'image/png',buffer:Buffer.from('invalid')}}});
  if(invalidLogo.status()!==422)throw Error('Logo validation returned '+invalidLogo.status());
  const missing=await api.delete('/api/gst/bills/'+require('crypto').randomUUID(),{headers:{Origin:base,'x-csrf-token':token}});
  if(missing.status()!==404)throw Error('Unknown bill deletion returned '+missing.status());
  console.log('PASS logo validation and tenant-bound deletion endpoint');
  await page.context().addCookies((await api.storageState()).cookies);
  await page.goto(base+'/settings/profile');
  await page.getByLabel('Upload logo',{exact:true}).waitFor({state:'attached'});
  console.log('PASS profile logo upload control');
  await page.goto(base+'/bills?period=2026-09');
  await page.getByLabel('Loading bills').waitFor({state:'detached'});
  const rows=page.locator('.bills-table tbody tr');
  if(await rows.count()){
   await rows.first().getByRole('button',{name:'Review',exact:true}).click();
   await page.getByRole('dialog').waitFor();
   await page.getByRole('button',{name:'Save changes',exact:true}).waitFor();
   await page.getByRole('button',{name:'Delete bill',exact:true}).waitFor();
   await page.getByRole('button',{name:'Back to bills',exact:true}).click();
   await page.getByRole('dialog').waitFor({state:'detached'});
   console.log('PASS live bill drawer, save and delete controls');
  }else console.log('PASS live bill list (this workspace has no September bills)');
  const response=await api.get('/api/gst/bills?period=2026-09');
  if(!response.ok())throw Error('Bill list failed');
  const {invoices}=await response.json();
  if(invoices.some(invoice=>!invoice.filename))throw Error('Bill filenames missing');
  console.log('PASS canonical bill filenames');
 }finally{await browser.close();await api.dispose()}
})().catch(error=>{console.error(error.message);process.exitCode=1});
