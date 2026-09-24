"""Local browser coverage for all demo scenarios; model responses are stubbed here."""
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import uvicorn
from fastapi import FastAPI, Response
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.routes import current_user
from app.services.gst import demo_routes
from app.services.gst.mock_data import SCENARIOS, generate_mock_data

ROOT = Path(__file__).resolve().parents[1]


def main():
    app = FastAPI()
    user = SimpleNamespace(id='demo-viewer', role='viewer', full_name='Demo Viewer', email='demo@example.test')
    app.dependency_overrides[current_user] = lambda: user
    app.include_router(demo_routes.router)
    demo_routes.generate_answer = lambda payload, context: {'answer':'Synthetic demo answer based on the selected Gold summary.',
        'sample':True, 'sources':[{'id':'gold-summary','label':'Validated financial summary','layer':'Gold','href':'/demo?scenario=mixed&tab=filing'}],
        'followups':['Which credits are deferred?']}

    @app.get('/api/auth/csrf')
    def csrf(response: Response):
        response.set_cookie('csrf_token', 'test-token')
        return {'token':'test-token'}

    @app.get('/api/dashboard')
    def dashboard():
        return {**generate_mock_data()['dashboard'], 'user':vars(user), 'clients':[]}

    server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=8089, log_level='error'))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    node = r'C:\Users\BIS\Stephen\ITR\income-tax\.tools\node-v22.22.0-win-x64\node.exe'
    with (ROOT/'artifacts/demo-ui-server.log').open('w') as log:
        process = subprocess.Popen([node,'node_modules/next/dist/bin/next','start','-p','3101'], cwd=ROOT/'frontend',
            env={**os.environ,'BACKEND_URL':'http://127.0.0.1:8089'}, stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            time.sleep(3)
            with sync_playwright() as p:
                browser = p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
                context = browser.new_context(viewport={'width':1440,'height':1000})
                context.add_cookies([{'name':'session','value':'demo=.signature','domain':'localhost','path':'/'}])
                page = context.new_page()
                page.goto('http://localhost:3101/demo?period=2026-09')
                page.get_by_text('Demo workspace · Synthetic data',exact=True).wait_for()
                assert page.get_by_role('navigation', name='Main navigation').get_by_role('link', name='GST Workspace').count() == 1
                assert page.get_by_role('navigation', name='Main navigation').get_by_role('link', name='Assistant').count() == 1
                for scenario in SCENARIOS:
                    page.get_by_label('Demo scenario').select_option(scenario)
                    page.get_by_text(SCENARIOS[scenario],exact=True).last.wait_for()
                    page.wait_for_function("!document.querySelector('select[aria-label=\"Demo scenario\"]').disabled")
                    assert page.locator('input[type=file]').count()==0
                    assert 'Your workspace could not be loaded' not in page.locator('body').inner_text()
                print('PASS all 15 demo scenarios and read-only controls',flush=True)
                page.get_by_role('tab',name='Documents',exact=True).click()
                page.get_by_role('button',name='Next',exact=True).click()
                page.get_by_text('Page 2',exact=True).wait_for()
                page.get_by_role('button',name='View',exact=True).first.click()
                page.get_by_role('region',name='Synthetic invoice details').wait_for()
                print('PASS pagination and synthetic invoice details',flush=True)
                page.get_by_role('tab',name='Search',exact=True).click()
                page.get_by_label('Search documents',exact=True).fill('metro')
                page.get_by_role('button',name='Search',exact=True).click()
                page.get_by_text('24 results',exact=False).wait_for()
                page.get_by_label('Search documents',exact=True).fill('no-match')
                page.get_by_role('button',name='Search',exact=True).click()
                page.get_by_text('No matching documents.',exact=False).wait_for()
                print('PASS search results and empty search',flush=True)
                page.get_by_role('tab',name='Assistant',exact=True).click()
                page.get_by_label('Your question',exact=True).fill('What is my cash requirement?')
                page.get_by_role('button',name='Ask assistant',exact=True).click()
                page.get_by_text('Synthetic demo answer based on the selected Gold summary.',exact=True).wait_for()
                page.get_by_role('link',name='Validated financial summary',exact=False).wait_for()
                page.get_by_role('button',name='Which credits are deferred?',exact=True).click()
                assert page.get_by_text('Which credits are deferred?',exact=True).count()>0
                print('PASS conversational UI, citations and follow-up (stubbed model)',flush=True)
                page.screenshot(path=str(ROOT/'artifacts/demo-assistant.png'),full_page=True)
                page.set_viewport_size({'width':390,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.get_by_role('tab',name='Dashboard',exact=True).click()
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.screenshot(path=str(ROOT/'artifacts/demo-mobile.png'),full_page=True)
                print('PASS mobile dashboard and assistant',flush=True)
                browser.close()
        finally:
            process.terminate()
            process.wait(timeout=15)
            server.should_exit = True
            thread.join(timeout=10)


if __name__=='__main__':
    main()
