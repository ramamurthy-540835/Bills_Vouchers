from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .config import get_settings
from .db import get_repository
from .repository import FinanceRepository
from .routes import router, v1_router
from .security import hash_password


def create_app():
    app = FastAPI(title="Bills & Voucher Finance — BigQuery")
    s = get_settings()
    app.add_middleware(
        SessionMiddleware,
        secret_key=s.app_secret_key,
        max_age=s.session_max_age,
        https_only=s.app_env == "production",
        same_site="lax",
    )

    @app.middleware("http")
    async def security_middleware(request: Request, call_next):
        request.state.request_id = request.headers.get("x-request-id", str(uuid4()))
        if (
            s.app_env == "production"
            and request.method in {"POST", "PUT", "PATCH", "DELETE"}
            and not request.url.path.startswith("/api/")
        ):
            origin = request.headers.get("origin") or request.headers.get("referer")
            if origin and origin.rstrip("/") != str(request.base_url).rstrip("/"):
                return JSONResponse(
                    {
                        "error": {
                            "code": "csrf_origin",
                            "message": "Request origin is not allowed.",
                            "request_id": request.state.request_id,
                        }
                    },
                    status_code=403,
                )
        response = await call_next(request)
        response.headers["x-request-id"] = request.state.request_id
        response.headers["x-content-type-options"] = "nosniff"
        response.headers["x-frame-options"] = "DENY"
        response.headers["referrer-policy"] = "strict-origin-when-cross-origin"
        response.headers["content-security-policy"] = (
            "default-src 'self'; img-src 'self' data:; frame-src 'self'; style-src 'self' https://cdn.jsdelivr.net; script-src 'self' 'unsafe-inline'; connect-src 'self'"
        )
        return response

    @app.exception_handler(HTTPException)
    async def authentication_redirect(request: Request, exc: HTTPException):
        if exc.status_code == 401 and not request.url.path.startswith("/api/"):
            return RedirectResponse("/login", status_code=303)
        from fastapi.exception_handlers import http_exception_handler

        return await http_exception_handler(request, exc)

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        return JSONResponse(
            {
                "error": {
                    "code": "internal_error",
                    "message": "An unexpected error occurred.",
                    "request_id": getattr(request.state, "request_id", "unknown"),
                }
            },
            status_code=500,
        )

    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    app.include_router(router)
    app.include_router(v1_router)

    @app.on_event("startup")
    def startup():
        if s.bootstrap_admin_password:
            FinanceRepository(get_repository()).ensure_admin(
                hash_password(s.bootstrap_admin_password), s.bootstrap_admin_email
            )

    return app


app = create_app()
