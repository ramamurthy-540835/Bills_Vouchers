import {defineConfig} from '@playwright/test'
import base from './playwright.config'

export default defineConfig(base, {
 use:{...base.use,baseURL:process.env.BV_TEST_URL||'http://localhost:3200',
  storageState:process.env.BV_TEST_URL?undefined:{cookies:[{
   name:'session',value:'local-browser-test',domain:'localhost',path:'/',expires:-1,
   httpOnly:true,secure:false,sameSite:'Lax'
  }],origins:[]}},
 reporter:[['list'],['json',{outputFile:'../artifacts/v4-audit/frontend-tests.json'}]],
})
