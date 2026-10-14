"""Exercise live mail readiness and validation without creating an account/email."""
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

from deploy_gst_easy import WEB


response = httpx.post(WEB + '/api/auth/register', json={},
                      headers={'Origin': WEB}, timeout=60)
result = {'utc': datetime.now(timezone.utc).isoformat(), 'status': response.status_code,
          'response': response.json(), 'account_created': False, 'email_sent': False}
assert response.status_code == 422, result
assert 'mobile' in str(result['response']).lower(), result
Path('artifacts/gst_easy/registration-readiness.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
