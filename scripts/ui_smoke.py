"""Browser checks against an in-memory API fixture; never contacts GCP."""
import json
import os
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        cookie = self.headers.get("cookie", "")
        # Model signed session values containing base64 padding. Re-encoding
        # the cookie changes its signature and must fail authentication.
        if "=.signature" not in cookie:
            self.send_response(401)
            self.end_headers()
            return
        role = "viewer" if "viewer" in cookie else "client"
        other = "client-b" in cookie
        payload = {"client_id": "b" if other else "a", "period": "2026-09", "mode": "empty",
                   "user": {"full_name": "Client B" if other else "Red Taxi", "email": "user@example.test", "role": role},
                   "profile": {"legal_name": "Client B" if other else "Red Taxi", "gstin": "", "state_code": None},
                   "clients": [{"id": "b" if other else "a", "name": "Client B" if other else "Red Taxi"}],
                   "counts": {"documents": 0, "review": 0, "posted": 0, "failed": 0},
                   "pipeline": {"bronze": 0, "silver": 0, "gold": 0, "updated_at": None},
                   "documents": [], "ledger": [], "matches": [], "summary": None, "filing": {"state": "draft"},
                   "has_silver": False, "outward_count": 0, "demo_fallback": "sample" in cookie}
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 8088), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    node = Path(r"C:\Users\BIS\Stephen\ITR\income-tax\.tools\node-v22.22.0-win-x64\node.exe")
    log = (ROOT / "artifacts").mkdir(exist_ok=True)
    with (ROOT / "artifacts/ui-server.log").open('w') as log:
        process = subprocess.Popen([str(node), "node_modules/next/dist/bin/next", "start", "-p", "3100"], cwd=ROOT / "frontend",
                                   env={**os.environ, "BACKEND_URL": "http://127.0.0.1:8088"}, stdout=log, stderr=log,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            time.sleep(3)
            with sync_playwright() as p:
                browser = p.chromium.launch(executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe", headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                response = page.goto('http://localhost:3100/', wait_until='networkidle')
                assert page.url.endswith('/login')
                for identity in ('client-a', 'viewer-a', 'client-b', 'sample-a'):
                    context = browser.new_context(viewport={"width": 1440, "height": 1000})
                    context.add_cookies([{"name": "session", "value": identity+"=.signature", "domain": "localhost", "path": "/"}])
                    page = context.new_page()
                    for route in ('/', '/documents', '/gst/filing', '/search'):
                        response = page.goto('http://localhost:3100'+route, wait_until='networkidle')
                        assert response.status == 200
                        assert not page.url.endswith('/login'), 'signed cookie did not survive SSR forwarding'
                        text = page.locator('body').inner_text()
                        assert 'Loading finance workspace' not in text
                        assert 'Your workspace could not be loaded' not in text
                        assert '27AAPFU0939F1ZV' not in text
                        assert page.locator('nav a:not(.nav-item)').count() == 0
                        if 'sample' in identity:
                            assert page.get_by_text("Sample data — not your client's figures").count() == 1
                        else:
                            assert 'Umesh' not in text
                        if 'viewer' in identity:
                            assert page.locator('input[type=file]').count() == 0
                            assert page.get_by_role('button', name='Validate', exact=True).count() == 0
                        elif identity=='client-a' and route in ('/', '/documents'):
                            assert page.get_by_text('＋ Upload bill', exact=True).count() == 1
                        if identity=='client-a' and route in ('/', '/gst/filing'):
                            page.screenshot(path=str(ROOT / 'artifacts' / ('overview.png' if route=='/' else 'filing.png')), full_page=True)
                    page.set_viewport_size({"width": 390, "height": 844})
                    page.goto('http://localhost:3100/', wait_until='networkidle')
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'mobile horizontal overflow'
                    context.close()
                    print('PASS rendered pages, role controls and responsive layout: '+identity, flush=True)
                browser.close()
        finally:
            process.terminate()
            process.wait(timeout=15)
            server.shutdown()


if __name__ == '__main__':
    main()
