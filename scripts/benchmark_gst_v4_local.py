"""Compare actual old/new login handlers with identical synthetic blocking I/O.

This is an event-loop concurrency benchmark, NOT a Cloud Run or BigQuery SLO.
No credentials, real accounts, network providers or cloud writes are used.
"""
import asyncio
import json
from pathlib import Path
import secrets
import statistics
import subprocess
import sys
from time import perf_counter, sleep
from types import ModuleType, SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from app import routes
from app.db import get_db

BASE='5656ed8caaf76abc1b859effe5368893ee4fb637'


async def exercise(module, count=40):
    user=SimpleNamespace(id='synthetic-benchmark',email='benchmark@example.test',full_name='Synthetic',
        role='client',email_verified=True,is_active=True,session_version=0,password_hash='not-a-real-hash')
    def blocking(value=None):
        sleep(.025)
        return value
    module.fr=lambda _:SimpleNamespace(user_by_email=lambda _:blocking(user),audit=lambda *_:blocking())
    module.verify_password=lambda *_:blocking(True)
    module.auth_identity.throttle=lambda *_:blocking()
    module.auth_identity.complete_login=lambda *_:blocking()
    app=FastAPI();app.add_middleware(SessionMiddleware,secret_key=secrets.token_urlsafe(32))
    app.include_router(module.router);app.dependency_overrides[get_db]=lambda:object()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://benchmark') as client:
        started=perf_counter()
        async def request():
            response=await client.post('/api/auth/login',json={'email':user.email,'password':secrets.token_urlsafe(20)})
            assert response.status_code==200
            return (perf_counter()-started)*1000
        times=sorted(await asyncio.gather(*(request() for _ in range(count))))
    return {'requests':count,'completion_p50_ms':round(statistics.median(times),2),
        'completion_p95_ms':round(times[int(count*.95)-1],2),'batch_wall_ms':round(times[-1],2)}


def main():
    original=ModuleType('app.v4_baseline_benchmark');original.__package__='app'
    source=subprocess.check_output(['git','show',BASE+':app/routes.py'],text=True,encoding='utf-8')
    exec(compile(source,'baseline_routes.py','exec'),original.__dict__)
    before=asyncio.run(exercise(original));after=asyncio.run(exercise(routes))
    result={'baseline_commit':BASE,'environment':'local ASGI; synthetic storage/password operations',
        'workload':'40 concurrent sign-ins, five 25ms blocking operations per request',
        'cloud_requests':0,'before':before,'after':after,
        'batch_wall_improvement_percent':round((1-after['batch_wall_ms']/before['batch_wall_ms'])*100,2)}
    path=Path('artifacts/v4-audit/local-concurrency.json');path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2));print(json.dumps(result))


if __name__=='__main__':main()
