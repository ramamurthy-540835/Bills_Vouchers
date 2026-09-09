from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
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
    @app.exception_handler(HTTPException)
    async def authentication_redirect(request:Request,exc:HTTPException):
        if exc.status_code==401 and not request.url.path.startswith('/api/'):
            return RedirectResponse('/login',status_code=303)
        from fastapi.exception_handlers import http_exception_handler
        return await http_exception_handler(request,exc)
    app.mount('/static',StaticFiles(directory='app/static'),name='static'); app.include_router(router)
    @app.on_event('startup')
    def startup(): FinanceRepository(get_repository()).ensure_admin(hash_password('ChangeMe123!'))
    return app
app=create_app()
