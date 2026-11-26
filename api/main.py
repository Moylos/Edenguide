import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.sessions import SessionMiddleware

from api.config import get_settings
from api.deps import AdminRequired, LoginRequired
from api.routers import admin as admin_api
from api.routers import auth, public, tierlist

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Edenguide", docs_url="/docs", redoc_url=None)

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        https_only=settings.is_production,
        same_site="lax",
    )

    static_dir = BASE_DIR / "ui" / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.exception_handler(LoginRequired)
    async def _login_required(request: Request, exc: LoginRequired):
        return RedirectResponse(url="/login", status_code=303)

    @app.exception_handler(AdminRequired)
    async def _admin_required(request: Request, exc: AdminRequired):
        if request.url.path.startswith("/api/") or "application/json" in request.headers.get("accept", ""):
            return JSONResponse({"error": "Forbidden"}, status_code=403)
        return PlainTextResponse("Forbidden", status_code=403)

    def _db_unavailable_response(request: Request):
        path = request.url.path
        if path.startswith("/api/") or "application/json" in request.headers.get("accept", ""):
            return JSONResponse(
                {"error": "Service temporarily unavailable: database connection failed."},
                status_code=503,
            )
        return PlainTextResponse(
            "Service temporarily unavailable: database connection failed. Try again later.",
            status_code=503,
        )

    @app.exception_handler(SQLAlchemyError)
    async def _db_error(request: Request, exc: SQLAlchemyError):
        logger.warning("Database error on %s %s: %s", request.method, request.url.path, exc)
        return _db_unavailable_response(request)

    @app.exception_handler(TimeoutError)
    async def _timeout_error(request: Request, exc: TimeoutError):
        logger.warning("Timeout on %s %s: %s", request.method, request.url.path, exc)
        return _db_unavailable_response(request)

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    app.include_router(public.router)
    app.include_router(auth.router)
    app.include_router(tierlist.router)
    app.include_router(admin_api.router)

    # Flask-Admin (WSGI) mounted into FastAPI (ASGI)
    try:
        from a2wsgi import WSGIMiddleware

        from api.admin_panel import create_admin_app

        flask_admin_app = create_admin_app()
        app.mount("/admin", WSGIMiddleware(flask_admin_app))
    except Exception as exc:  # pragma: no cover - keeps app booting if admin deps missing
        import logging

        logging.getLogger(__name__).warning("Admin panel not mounted: %s", exc)

    return app


app = create_app()
