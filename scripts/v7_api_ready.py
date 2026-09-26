"""Read-only readiness check before pointing the web preview to v7 again."""
import os
import httpx

with httpx.Client(base_url='https://v7-api---bills-voucher-foovqasysa-el.a.run.app',timeout=120) as client:
    r=client.post('/api/auth/login',json={'email':os.environ['BV_TEST_EMAIL'],'password':os.environ['BV_TEST_PASSWORD']})
    assert r.status_code==200, f'Login: {r.status_code}'
    for path in ['/api/dashboard?period=2026-09','/api/gst/workspace?period=2026-09','/api/settings/account']:
        r=client.get(path)
        assert r.status_code==200, (path,r.status_code)
        if 'settings' not in path:
            assert r.json()['sample'] and r.json()['summary']
        print('PASS '+path,flush=True)
