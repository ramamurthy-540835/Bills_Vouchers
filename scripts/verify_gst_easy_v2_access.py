"""Read-only V2 auth/data smoke; never imports financial records."""
import json

import httpx
from prepare_gst_easy_v2 import cloud, ART


def main():
    deployment = json.loads((ART / 'deployment.json').read_text())
    base = deployment['frontend_url']
    assert base.startswith('https://gst-easy-v2-web-')
    password = cloud('secrets', 'versions', 'access', '1',
                     '--secret=gst-easy-v2-demo-password', '--project=aidirac-503309')
    checks = {}
    with httpx.Client(base_url=base, timeout=120, headers={'Origin': base}) as client:
        client.get('/login').raise_for_status()
        response = client.post('/api/auth/login', json={'email': 'naturelabs@demo.com', 'password': password})
        del password
        assert response.status_code == 200, response.status_code
        account = client.get('/api/settings/account').json()
        assert account['user']['role'] == 'client'
        assert len(account['clients']) == 3
        checks['client_identity_and_three_memberships'] = True
        response = client.get('/api/admin/workspace')
        assert response.status_code == 403, response.status_code
        checks['platform_admin_denied'] = True
        response = client.get('/api/gst/bills/dashboard?period=2026-10')
        assert response.status_code == 200, response.status_code
        dashboard = response.json()
        assert dashboard['confirmed_count'] == 0
        checks['no_confirmed_invoices'] = True
        response = client.get('/api/gst/bills/reports?kind=purchases&period=2026-10&format=csv')
        assert response.status_code == 403, response.status_code
        checks['synthetic_financial_export_denied'] = True
        csrf = client.cookies.get('csrf_token')
        response = client.post('/api/workspace/client', json={'client_id': 'unrelated-nonmember-business'},
                               headers={'X-CSRF-Token': csrf or ''})
        assert response.status_code in {403, 404}, response.status_code
        assert client.get('/api/settings/account').json()['client_id'] == account['client_id']
        checks['unauthorized_business_switch_denied_context_preserved'] = True
    (ART / 'live-access-results.json').write_text(json.dumps(checks, indent=2))
    print(json.dumps(checks, indent=2))


if __name__ == '__main__':
    main()
