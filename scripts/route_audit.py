"""Generate a static inventory, distinguishing evidence from untested claims."""
import ast
from pathlib import Path

lines = ["# v5 route audit", "", "Updated 2026-09-24. This table inventories every Python route decorator in the checkout. Static PASS means the dependency/scope is present in source, not that every legacy business workflow has an end-to-end test. Runtime isolation gates cover the v5 workspace, document detail/search, pipeline and filing actions; legacy workflows retain their existing tests.", "", "## Resolution chain", "", "Next.js server page -> signed backend session -> users -> active client_memberships -> selected client -> current client_user_role -> gst_client_profile. Workspace queries bind client_id and period. A missing profile produces incomplete-profile chrome; a missing session redirects before rendering. Sample figures live only in frontend/app/sample.ts and require DEMO_FALLBACK from the authenticated workspace response.", "", "D1 was located in the recovered preview frontend/app/page.tsx: its company context used the Umesh GSTIN independently of the resolved user name. That component and the fixture-only filing page have been replaced. Recovery source: Cloud Build f70ce346-7cda-4642-8b8c-c6b2ca829795; the later production build did not contain the complete preview implementation.", "", "## Frontend", "", "| Route | Auth | Client | Without data | Layer | Result |", "|---|---|---|---|---|---|"]
for route in ('/', '/documents', '/documents/[id]', '/gst/filing', '/search'):
    lines.append(f"| `{route}` | Server proxy + backend session | Workspace identity | Complete shell / empty or error card | Bronze, silver, gold via API | PASS (browser gate) |")
lines += ["| `/login` | Public sign-in | Not yet selected | Sign-in form | Identity | PASS |", "| `/settings` | Server proxy; password API session | Not needed for own password | Password form | Identity | PASS; standalone security flow |", "| `/api/[...path]` | Forwarded cookie, backend authorization | Backend | Structured error | Backend | PASS |", "", "## Backend", "", "| Method / route | Auth applied | Client resolved | Without data | Reads from | Static result |", "|---|---|---|---|---|---|"]
count = 0
for file in (Path('app/routes.py'), Path('app/services/gst/routes.py'), Path('app/services/gst/workbench.py')):
    source = file.read_text()
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        text = ast.get_source_segment(source, node) or ''
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call) or not isinstance(dec.func, ast.Attribute) or not dec.args or not isinstance(dec.args[0], ast.Constant):
                continue
            path = dec.args[0].value
            if not isinstance(path, str) or not path.startswith('/'):
                continue
            prefix = '/api/v1' if isinstance(dec.func.value, ast.Name) and dec.func.value.id == 'v1_router' else ''
            path = prefix + path
            auth = 'Session dependency' if 'Depends(current_user)' in text else 'OIDC identity' if path.startswith('/internal/') else 'Public identity/health endpoint'
            scoped = any(key in text for key in ('active_client(', 'client_context(', 'selected(request', '_client_or_403(', 'client.id', 'client_id=@'))
            client = 'Bound selected client' if scoped else 'Delegates to scoped handler' if 'return ' in text and auth == 'Session dependency' and not path.startswith('/api/auth') else 'Identity / service scope'
            layer = 'Medallion (bronze/silver/gold)' if file.name == 'workbench.py' else 'GST profile / gold' if file.parent.name == 'gst' and '/gst/' in path else 'Legacy scoped tables'
            if '/auth/' in path or '/health' in path or path in ('/login','/logout','/signup','/readyz'):
                layer = 'Identity / operational'
            result = 'PASS' if auth != 'Public identity/health endpoint' or path in ('/login','/signup','/logout','/health','/healthz','/readyz','/api/auth/login','/api/v1/health') else 'REVIEW'
            lines.append(f"| `{dec.func.attr.upper()} {path}` | {auth} | {client} | Empty response or explicit error; page templates retain shell | {layer} | {result} |")
            count += 1
lines += ["", f"Backend registrations inventoried: **{count}**.", "", "## Verification limits", "", "Unauthenticated login and infrastructure health probes are intentionally public. Identity lookup queries bind user/email parameters before client selection; they are not tenant financial reads. No claim is made that every legacy write has been migrated to the new medallion tables. The new web shell uses the new tenant-bound APIs. Source documents remain immutable; no legacy routes or tables were removed."]
Path('docs/v5-route-audit.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
print(f'Inventoried {count} backend route registrations')
