"""
Titan — High-performance multi-service API platform
Creator: Antmind Ventures Private Limited

How to add a new service:
  1. Create  app/services/<name>/
  2. Add     app/services/<name>/router.py  (FastAPI APIRouter)
  3. Import and include below with prefix "/api/v1/<name>"
  4. Register its models in alembic/env.py
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import logging
import sys

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from loguru import logger

from app.core.cache import close_redis, init_redis
from app.core.config import settings
from app.core.middleware.logging import RequestLoggingMiddleware

# ── Service routers ───────────────────────────────────────────────────────────
from app.services.object_replace.router import router as object_replace_router
from app.services.platform.router import router as platform_router
from app.workers.client import close_arq_pool, init_arq_pool

# from app.services.game_one.router import router as game_one_router
# from app.services.game_two.router import router as game_two_router


# ── Loguru setup ──────────────────────────────────────────────────────────────
def setup_logging():
    # Remove default handler
    logger.remove()

    # Add a clean colored one
    logger.add(
        sys.stdout,
        level=settings.log_level.upper(),
        colorize=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        backtrace=True,
        diagnose=False,
        # We disable enqueue for now to rule out async logging issues during boot
        enqueue=False,
    )

    # Intercept stdlib logging
    class InterceptHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            # Get corresponding Loguru level if it exists
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno

            # Find caller from where originated the logged message
            frame, depth = logging.currentframe(), 2
            while frame and frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1

            logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

    # Set up the intercept handler
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Also intercept uvicorn/gunicorn specifically
    for _name in ("uvicorn", "uvicorn.error", "uvicorn.access", "gunicorn", "gunicorn.error"):
        _logger = logging.getLogger(_name)
        _logger.handlers = [InterceptHandler()]
        _logger.propagate = False


setup_logging()


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    logger.info("Titan starting — v{}", settings.app_version)
    await init_redis()
    logger.info("Redis connected")
    await init_arq_pool()
    logger.info("ARQ producer pool connected")
    yield
    await close_arq_pool()
    await close_redis()
    logger.info("Titan shutdown complete")


# ── App factory ───────────────────────────────────────────────────────────────
def create_app() -> FastAPI:
    app = FastAPI(
        title="Titan API",
        description=(
            "Multi-service API platform by **Antmind Ventures Private Limited**.\n\n"
            "Built on FastAPI · PostgreSQL + pgvector · Redis."
        ),
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── Middleware (outermost first) ──────────────────────────────────────────
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost",
            "http://localhost:3000",
            "http://localhost:8000",
            "https://titan.antmind.ai",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Response-Time", "Server-Timing"],
    )

    # ── Service routers ───────────────────────────────────────────────────────
    app.include_router(platform_router, prefix=settings.api_v1_prefix)
    app.include_router(object_replace_router, prefix=settings.api_v1_prefix)
    # app.include_router(game_one_router, prefix=f"{settings.api_v1_prefix}/game-one")
    # app.include_router(game_two_router, prefix=f"{settings.api_v1_prefix}/game-two")

    # ── Convenience routes ────────────────────────────────────────────────────
    @app.get("/", include_in_schema=False)
    async def root() -> dict:
        return {
            "service": "titan",
            "creator": "Antmind Ventures Private Limited",
            "version": settings.app_version,
            "docs": "/docs",
            "health": "/api/v1/health",
        }

    @app.get("/health", include_in_schema=False)
    async def health_alias() -> RedirectResponse:
        return RedirectResponse(url="/api/v1/health", status_code=307)

    @app.exception_handler(Exception)
    async def _global_exc(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception | {} {}", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    return app


app = create_app()
