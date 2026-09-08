from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from .config import get_settings
from .db import Base, SessionLocal, engine
from .routes import bootstrap_admin, router
from .services.accounting import seed_accounts

def create_app() -> FastAPI:
    app=FastAPI(title="Bills & Voucher Finance", docs_url=None if get_settings().app_env=="production" else "/docs")
    app.add_middleware(SessionMiddleware,secret_key=get_settings().app_secret_key,https_only=get_settings().app_env=="production",same_site="lax")
    app.mount("/static",StaticFiles(directory="app/static"),name="static")
    app.include_router(router)
    @app.on_event("startup")
    def startup():
        Base.metadata.create_all(engine)
        with SessionLocal() as db: bootstrap_admin(db); seed_accounts(db)
    return app
app=create_app()
