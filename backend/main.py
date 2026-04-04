#uvicorn main:app --reload
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from Auth.Signin import router as signin_router
from Auth.Signup import router as signup_router
import os
import asyncio
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Try to import dataset routes with explicit error handling
try:
    from routes.datasets import router as datasets_router
    logger.info("Dataset router imported successfully")
except Exception as e:
    logger.error(f"Failed to import dataset router: {e}", exc_info=True)
    datasets_router = None

try:
    from routes.metadata import router as metadata_router
    logger.info("Metadata router imported successfully")
except Exception as e:
    logger.error(f"Failed to import metadata router: {e}", exc_info=True)
    metadata_router = None

try:
    from routes.ownership import router as ownership_router
    logger.info("Ownership router imported successfully")
except Exception as e:
    logger.error(f"Failed to import ownership router: {e}", exc_info=True)
    ownership_router = None

try:
    from routes.cleaning import router as cleaning_router
    logger.info("Cleaning router imported successfully")
except Exception as e:
    logger.error(f"Failed to import Cleaning router: {e}", exc_info=True)
    cleaning_router = None

try:
    from routes.text_to_sql import router as text_to_sql_router
    logger.info("Text-to-SQL router imported successfully")
except Exception as e:
    logger.error(f"Failed to import Text-to-SQL router: {e}", exc_info=True)
    text_to_sql_router = None

try:
    from database import init_database
    from database.db_init import test_db_connection, get_db_status, get_db_engine, DatabaseConnectionError
    logger.info("Database module imported successfully")
except Exception as e:
    logger.error(f"Failed to import database module: {e}", exc_info=True)
    init_database = None
    test_db_connection = None
    get_db_status = lambda: (False, "Database module failed to import")

load_dotenv(override=False)
logger.info("Environment Variables Check:")
logger.info(f"SECRET_KEY: {'Loaded' if os.getenv('SECRET_KEY') else 'NOT FOUND'}")
logger.info(f"GOOGLE_CLIENT_ID: {'Loaded' if os.getenv('GOOGLE_CLIENT_ID') else 'NOT FOUND'}")
logger.info(f"GOOGLE_CLIENT_SECRET: {'Loaded' if os.getenv('GOOGLE_CLIENT_SECRET') else 'NOT FOUND'}")

# Initialize database on startup (check MySQL connection and tables)
def check_mysql_connection() -> bool:
    """
    Check MySQL connection and initialize tables if needed.
    Returns True if connection successful, False otherwise.
    Does NOT raise exceptions - allows app to start without database.
    """
    from sqlalchemy import text

    if test_db_connection is None:
        logger.error("Database module not available")
        return False

    # Test connection with retry logic
    if not test_db_connection(retry_count=3, retry_delay=2.0):
        connected, error_msg = get_db_status()
        logger.warning("=" * 60)
        logger.warning("Application starting WITHOUT database connection")
        logger.warning(f"Error: {error_msg}")
        logger.info("Database-dependent features will be unavailable")
        logger.info("Make sure MySQL is running: docker-compose up -d")
        logger.warning("=" * 60)
        return False

    # Connection successful, check if tables need initialization
    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = DATABASE() AND table_name = 'users'"
            ))
            if result.scalar() == 0:
                logger.info("Database tables not found. Initializing for first time...")
                init_database()
                logger.info("Database initialized successfully")
            else:
                logger.info("Database tables already exist. Skipping initialization.")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}")
        logger.info("Database connection works but schema initialization failed")
        return False

# Run connection check (non-blocking - app will start even if DB is down)
_db_available = check_mysql_connection()

# Background cleanup task for cleaning agent
async def cleanup_task():
    """Periodically cleanup old sessions and orphaned backup files"""
    while True:
        try:
            await asyncio.sleep(3600)  # Run every hour

            # Import session_manager (only if cleaning agent is available)
            try:
                from Agents.cleaning_agent.state_manager import session_manager

                # Cleanup old sessions (older than 30 minutes)
                session_manager.cleanup_old_sessions()

                # Cleanup orphaned backup files (older than 24 hours)
                session_manager.cleanup_orphaned_backups(max_age_hours=24)

            except Exception as e:
                logger.warning(f"Cleanup task failed: {e}")

        except asyncio.CancelledError:
            logger.info("Cleanup task cancelled")
            break
        except Exception as e:
            logger.error(f"Unexpected error in cleanup task: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown"""
    # Startup
    logger.info("Starting background cleanup task...")
    cleanup_task_handle = asyncio.create_task(cleanup_task())

    yield

    # Shutdown
    logger.info("Stopping background cleanup task...")
    cleanup_task_handle.cancel()
    try:
        await cleanup_task_handle
    except asyncio.CancelledError:
        pass

app = FastAPI(
    title="Natural Language Data Visualization API",
    description="API for uploading datasets and querying them with natural language",
    version="1.0.0",
    lifespan=lifespan
)

# SessionMiddleware FIRST
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY"),
    session_cookie="session",
    max_age=3600,
    same_site="lax",
    https_only=False
)

# CORS SECOND
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:5173')
PRODUCTION_FRONTEND_URL = os.getenv('PRODUCTION_FRONTEND_URL', '')
cors_origins = [origin for origin in [FRONTEND_URL, PRODUCTION_FRONTEND_URL, PRODUCTION_FRONTEND_URL.rstrip('/')] if origin]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600
)

@app.get("/api/hello")
async def hello():
    return {"message": "Hello from FastAPI (Vite frontend)!"}

@app.get("/")
async def root():
    return {
        "message": "Natural Language Data Visualization API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint that reports database connection status.
    Returns 200 even if database is down (for load balancer health checks),
    but includes detailed status information.
    """
    db_connected, db_error = get_db_status()

    # Try to verify current connection if we think we're connected
    if db_connected:
        try:
            from sqlalchemy import text
            engine = get_db_engine()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as e:
            from database.db_init import set_db_status
            set_db_status(False, f"Connection lost: {str(e)}")
            db_connected = False
            db_error = f"Connection lost: {str(e)}"

    return {
        "status": "healthy" if db_connected else "degraded",
        "database": {
            "connected": db_connected,
            "error": db_error
        },
        "version": "1.0.0"
    }


@app.get("/health/db")
async def database_health():
    """
    Database-specific health check.
    Returns 503 if database is not connected.
    """
    from fastapi import HTTPException

    db_connected, db_error = get_db_status()

    if not db_connected:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unavailable",
                "error": db_error or "Database not connected",
                "hint": "Make sure MySQL is running: docker-compose up -d"
            }
        )

    # Verify connection is still alive
    try:
        from sqlalchemy import text
        engine = get_db_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
        return {
            "status": "connected",
            "message": "Database connection is healthy"
        }
    except Exception as e:
        from database.db_init import set_db_status
        set_db_status(False, f"Connection lost: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unavailable",
                "error": f"Connection lost: {str(e)}"
            }
        )

# Include routers
app.include_router(signin_router)
app.include_router(signup_router)

if datasets_router is not None:
    app.include_router(datasets_router)
    logger.info("Dataset router included")
else:
    logger.warning("Dataset router not included (import failed)")

if metadata_router is not None:
    app.include_router(metadata_router)
    logger.info("Metadata router included")
else:
    logger.warning("Metadata router not included (import failed)")

if ownership_router is not None:
    app.include_router(ownership_router)
    logger.info("Ownership router included")
else:
    logger.warning("Ownership router not included (import failed)")

if cleaning_router is not None:
    app.include_router(cleaning_router)
    logger.info("Cleaning router included")
else:
    logger.warning("Cleaning router not included (import failed)")

if text_to_sql_router is not None:
    app.include_router(text_to_sql_router)
    logger.info("Text-to-SQL router included")
else:
    logger.warning("Text-to-SQL router not included (import failed)")