from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from Auth.Signin import router as signin_router
from Auth.Signup import router as signup_router
import os
from dotenv import load_dotenv

load_dotenv()
print("=" * 50)
print("Environment Variables Check:")
print(f"SECRET_KEY: {'Loaded' if os.getenv('SECRET_KEY') else 'NOT FOUND'}")
print(f"GOOGLE_CLIENT_ID: {'Loaded' if os.getenv('GOOGLE_CLIENT_ID') else 'NOT FOUND'}")
print(f"GOOGLE_CLIENT_SECRET: {'Loaded' if os.getenv('GOOGLE_CLIENT_SECRET') else 'NOT FOUND'}")
print("=" * 50)

app = FastAPI()

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

app.include_router(signin_router)
app.include_router(signup_router)