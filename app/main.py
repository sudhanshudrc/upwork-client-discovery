from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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

app.include_router(api_v1_router, prefix=settings.API_V1_STR)

# Mount static directory for frontend assets
static_path = Path("static")
static_path.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", include_in_schema=False)
async def serve_frontend_index():
    """Serves the interactive single-page web application."""
    index_file = static_path / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": f"{settings.PROJECT_NAME} API Online. Visit /docs for OpenAPI documentation."}


@app.get("/health", tags=["Health"])
async def root_health_check():
    """Application root liveness check."""
    return {
        "status": "ONLINE",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }

