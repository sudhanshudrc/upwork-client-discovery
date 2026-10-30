from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.core.logging import setup_logging, get_logger, RequestLoggingMiddleware
from app.api.v1.router import api_v1_router

# Initialize centralized logging immediately
setup_logging()
logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context for initialization and shutdown."""
    logger.info("Initializing application directories and database...")
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    settings.SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    settings.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Automatically create relational database tables if needed
    try:
        from app.models.session import init_db
        await init_db()
        logger.info("Relational database schema verified and synchronized.")
    except Exception as e:
        logger.error(f"Database table initialization failure: {e}", exc_info=True)

    logger.info(f"{settings.PROJECT_NAME} v{settings.VERSION} online and ready.")
    yield
    logger.info("Application shutting down.")



app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Automated Upwork Lead Discovery, Deep History Scraping, and LinkedIn Decision-Maker Scoring Platform.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Captures HTTP exceptions, records failure reason for logging, and returns JSON error."""
    detail = exc.detail
    request.state.error_detail = detail
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": detail},
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Captures 422 request validation failures and formats structured field error details."""
    formatted_errors = []
    for err in exc.errors():
        field_loc = " -> ".join(str(item) for item in err.get("loc", []))
        msg = err.get("msg", "Validation error")
        formatted_errors.append(f"{field_loc}: {msg}")

    error_summary = "; ".join(formatted_errors) if formatted_errors else "Validation error"
    request.state.error_detail = error_summary
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catches unhandled internal exceptions, records failure reason, and logs full traceback."""
    reason = f"{type(exc).__name__}: {str(exc)}"
    request.state.error_detail = reason
    logger.error(
        f"[UNHANDLED EXCEPTION] {request.method} {request.url.path} - REASON: {reason}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error occurred."},
    )


app.include_router(api_v1_router, prefix=settings.API_V1_STR)

@app.get("/", include_in_schema=False)
async def serve_root_api_status():
    """Returns the platform API status and documentation entry points."""
    return {
        "message": f"{settings.PROJECT_NAME} API Online.",
        "version": settings.VERSION,
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "frontend_dev_url": "http://localhost:3000",
    }


@app.get("/health", tags=["Health"])
async def root_health_check():
    """Application root liveness check."""
    return {
        "status": "ONLINE",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }

