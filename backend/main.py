#uvicorn main:app --reload

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from Auth.Signin import router as signin_router
from Auth.Signup import router as signup_router
import os
from dotenv import load_dotenv

# Try to import dataset routes with explicit error handling
try:
    from routes.datasets import router as datasets_router
    print("[OK] Dataset router imported successfully")
except Exception as e:
    print(f"[ERROR] Failed to import dataset router: {e}")
    import traceback
    traceback.print_exc()
    datasets_router = None

try:
    from routes.metadata import router as metadata_router
    print("[OK] Metadata router imported successfully")
except Exception as e:
    print(f"[ERROR] Failed to import metadata router: {e}")
    import traceback
    traceback.print_exc()
    metadata_router = None

try:
    from routes.ownership import router as ownership_router
    print("[OK] Ownership router imported successfully")
except Exception as e:
    print(f"[ERROR] Failed to import ownership router: {e}")
    import traceback
    traceback.print_exc()
    ownership_router = None

try:
    from database import init_database
    print("[OK] Database module imported successfully")
except Exception as e:
    print(f"[ERROR] Failed to import database module: {e}")
    import traceback
    traceback.print_exc()

load_dotenv()
print("=" * 50)
print("Environment Variables Check:")
print(f"SECRET_KEY: {'Loaded' if os.getenv('SECRET_KEY') else 'NOT FOUND'}")
print(f"GOOGLE_CLIENT_ID: {'Loaded' if os.getenv('GOOGLE_CLIENT_ID') else 'NOT FOUND'}")
print(f"GOOGLE_CLIENT_SECRET: {'Loaded' if os.getenv('GOOGLE_CLIENT_SECRET') else 'NOT FOUND'}")
print("=" * 50)

# Initialize database on startup (only if it doesn't exist)
from pathlib import Path
DB_PATH = Path(__file__).parent / "database" / "nlp_viz.duckdb"
if not DB_PATH.exists():
    print("\n[INFO] Database not found. Initializing for first time...")
    try:
        init_database()
        print("[OK] Database initialized successfully\n")
    except Exception as e:
        print(f"[ERROR] Database initialization failed: {e}\n")
else:
    print("\n[INFO] Database already exists. Skipping initialization.\n")

app = FastAPI(
    title="Natural Language Data Visualization API",
    description="API for uploading datasets and querying them with natural language",
    version="1.0.0"
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        FRONTEND_URL
    ],
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

# Include routers
app.include_router(signin_router)
app.include_router(signup_router)

if datasets_router is not None:
    app.include_router(datasets_router)
    print("[OK] Dataset router included")
else:
    print("[WARNING] Dataset router not included (import failed)")

if metadata_router is not None:
    app.include_router(metadata_router)
    print("[OK] Metadata router included")
else:
    print("[WARNING] Metadata router not included (import failed)")

if ownership_router is not None:
    app.include_router(ownership_router)
    print("[OK] Ownership router included")
else:
    print("[WARNING] Ownership router not included (import failed)")