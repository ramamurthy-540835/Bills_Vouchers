import {defineConfig} from '@playwright/test'
export default defineConfig({
 testDir:'../tests/frontend',workers:1,timeout:60000,
 use:{baseURL:process.env.BV_TEST_URL||'http://localhost:3100',
  launchOptions:{executablePath:process.env.CHROME_PATH||'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'},
  headless:true},
 reporter:[['list'],['json',{outputFile:'../artifacts/v3/frontend-tests.json'}]],
})
