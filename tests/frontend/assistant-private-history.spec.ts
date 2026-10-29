import {test,expect} from '../../frontend/node_modules/@playwright/test'

test.beforeEach(async({context,request,baseURL})=>{
 test.skip(Boolean(process.env.BV_TEST_URL),'Isolated local fixtures; never run against customer deployments')
 await request.post('http://127.0.0.1:8103/__test__/reset')
 await context.addCookies([{name:'session',value:'local-browser-test',url:baseURL!}])
})

test('25 questions, saved-answer reload, new conversation and clear history (mocked chat API)',async({page})=>{
 const turns:any[]=[];let failure=false;const calls:any[]=[]
 await page.route('**/api/assistant/history?*',route=>route.fulfill({json:{items:[...turns].reverse().slice(0,20),next_offset:null}}))
 await page.route('**/api/assistant/history/clear?*',route=>{turns.length=0;return route.fulfill({json:{cleared:true}})})
 await page.route('**/api/assistant/chat?*',route=>{
  const payload=route.request().postDataJSON();calls.push(payload)
  if(failure){failure=false;return route.fulfill({status:503,json:{detail:'Synthetic provider unavailable'}})}
  const response={answer:`Saved answer for ${payload.question}`,sources:[{id:'guide',label:'Official guide',href:'https://www.gst.gov.in/',layer:'Reference'}],followups:[],history_saved:true}
  turns.push({question:payload.question,response,conversation_id:payload.conversation_id,created_at:new Date().toISOString()})
  return route.fulfill({json:response})
 })
 await page.goto('/assistant?period=2026-10')
 const input=page.getByLabel('Your question')
 for(let i=1;i<=25;i++){
  await input.fill(`GST test question ${i}`);await page.getByRole('button',{name:'Ask assistant',exact:true}).click()
  await expect(page.getByRole('log').getByText(`Saved answer for GST test question ${i}`,{exact:true})).toBeVisible()
 }
 expect(calls).toHaveLength(25)
 expect(calls.every(p=>p.history.length===0)).toBeTruthy()
 expect(new Set(calls.map(p=>p.conversation_id)).size).toBe(1)
 await page.reload();await page.getByText('Recently asked (20)',{exact:true}).click()
 await page.getByRole('button',{name:'GST test question 25',exact:true}).click()
 await expect(page.getByRole('log')).toContainText('Saved answer for GST test question 25')
 await page.getByRole('button',{name:'New conversation',exact:true}).click()
 await expect(page.getByRole('log')).not.toContainText('Saved answer')
 failure=true
 await input.fill('Keep this question after failure');await page.getByRole('button',{name:'Ask assistant',exact:true}).click()
 await expect(input).toHaveValue('Keep this question after failure')
 await expect(page.locator('.assistant-panel').getByRole('alert')).toContainText('Synthetic provider unavailable')
 await page.getByRole('button',{name:'Retry question',exact:true}).click()
 await expect(page.getByRole('log')).toContainText('Saved answer for Keep this question after failure')
 expect(calls.at(-1).conversation_id).not.toBe(calls[0].conversation_id)
 page.once('dialog',dialog=>dialog.accept())
 await page.getByRole('button',{name:'Clear my history',exact:true}).click()
 await expect(page.getByText('No saved questions for this period.')).toBeVisible()
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:900})
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy()
  await page.screenshot({path:`../artifacts/assistant-2026-10-29/assistant-${width}.png`,fullPage:true})
 }
})

test('history errors are recoverable and unsafe source links are suppressed',async({page})=>{
 let historyFail=true
 await page.route('**/api/assistant/history?*',route=>route.fulfill(historyFail?{status:503,json:{detail:'history unavailable'}}:{json:{items:[],next_offset:null}}))
 await page.route('**/api/assistant/chat?*',route=>route.fulfill({json:{answer:'Safe rendered answer',history_saved:true,sources:[{id:'bad',href:'javascript:alert(1)',label:'Unsafe',layer:'Bad'},{id:'other',href:'https://attacker.example/',label:'Other',layer:'Bad'}],followups:[]}}))
 await page.goto('/assistant?period=2026-10')
 await expect(page.locator('.assistant-panel').getByRole('alert')).toContainText('Recently asked could not be loaded')
 historyFail=false;await page.getByRole('button',{name:'Retry history',exact:true}).click()
 await expect(page.locator('.assistant-panel').getByRole('alert')).toHaveCount(0)
 await page.getByLabel('Your question').fill('What is GST?');await page.getByRole('button',{name:'Ask assistant',exact:true}).click()
 await expect(page.getByRole('log')).toContainText('Safe rendered answer')
 await expect(page.getByRole('link',{name:'Unsafe'})).toHaveCount(0)
 await expect(page.getByRole('link',{name:'Other',exact:false})).toHaveCount(0)
})

test('long saved questions wrap on mobile without horizontal overflow',async({page})=>{
 const question='Long private question '+ 'reference'.repeat(35)
 await page.route('**/api/assistant/history?*',route=>route.fulfill({json:{items:[{question,response:{answer:'Historical answer',sources:[],followups:[]},conversation_id:'00000000-0000-4000-8000-000000000001',created_at:'2026-10-29T12:00:00+00:00'}],next_offset:null}}))
 await page.setViewportSize({width:390,height:900})
 await page.goto('/assistant?period=2026-10')
 await page.getByText('Recently asked (1)',{exact:true}).click()
 await expect(page.getByRole('button',{name:question,exact:true})).toBeVisible()
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy()
})
