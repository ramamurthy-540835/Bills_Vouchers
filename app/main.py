from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from .config import get_settings
from .db import get_repository
from .routes import router
from .security import hash_password
from .repository import FinanceRepository

def create_app():
    app=FastAPI(title='Bills & Voucher Finance — BigQuery')
    s=get_settings(); app.add_middleware(SessionMiddleware,secret_key=s.app_secret_key,https_only=s.app_env=='production',same_site='lax')
    app.mount('/static',StaticFiles(directory='app/static'),name='static'); app.include_router(router)
    @app.on_event('startup')
    def startup(): FinanceRepository(get_repository()).ensure_admin(hash_password('ChangeMe123!'))
    return app
app=create_app()
