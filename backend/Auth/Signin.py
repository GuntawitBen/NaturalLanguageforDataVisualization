from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
import os
from dotenv import load_dotenv
from Auth.firebase import db, save_user_to_firebase, get_user_from_firebase, get_user_files_from_firebase
from Auth.Auth_utils import verify_password, generate_session_token, save_session_token, get_current_user, get_current_user_and_token, delete_session_token
from pydantic import BaseModel
from fastapi import Depends

load_dotenv()

router = APIRouter(prefix="/auth", tags=["Sign In"])

# Environment variables
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:8000')
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:5173')

# Google OAuth setup with code_challenge_method
oauth = OAuth()
oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile',
        'prompt': 'select_account',
        'code_challenge_method': 'S256'  # ← Use PKCE instead of state
    }
)

@router.get("/google/login")
async def google_login(request: Request):
    """Redirect user to Google login page"""
    redirect_uri = f"{BACKEND_URL}/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)

# Handle Google OAuth callback
@router.get("/google/callback")
async def google_callback(request: Request):
    """Handle callback from Google after user logs in"""
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        
        if user_info:
            email = user_info.get('email')
            name = user_info.get('name')
            picture = user_info.get('picture')
            
            # Save user to Firebase
            save_user_to_firebase(email, name, picture)
            
            print(f"User logged in: {name} ({email})")

            # Redirect to main dashboard
            return RedirectResponse(
                url=f"{FRONTEND_URL}/?email={email}&name={name}"
            )
        else:
            raise HTTPException(status_code=400, detail="Failed to get user info from Google")
    except Exception as e:
        print(f"Error during Google OAuth: {e}")
        return RedirectResponse(
            url=f"{FRONTEND_URL}/login/?error=auth_failed"
        )
    
@router.get("/user/{email}")
async def get_user(email: str):
    """Retrieve user information by email"""
    user = get_user_from_firebase(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("/users")
async def get_all_users():
    """Get all users (for testing)"""
    try:
        users_ref = db.collection('users').stream()
        users = [doc.to_dict() for doc in users_ref]
        return {"users": users, "count": len(users)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {e}")

@router.get("/me")
async def get_current_user_profile(current_user: str = Depends(get_current_user)):
    """Get current user's profile (Protected route)"""
    user = get_user_from_firebase(current_user)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("/logout")
async def logout(user_data: dict = Depends(get_current_user_and_token)):
    """Logout user (Protected route)"""
    email = user_data["email"]
    token = user_data["token"]

    # Delete session token from Firebase
    delete_session_token(db, token)

    return {"message": "Logged out successfully", "email": email}

@router.get("/user/{email}/files")
async def get_user_files(email: str, current_user: str = Depends(get_current_user)):
    """Get user's uploaded files (Protected route)"""
    # Verify the user is requesting their own files
    if current_user != email:
        raise HTTPException(status_code=403, detail="Access denied")

    files = get_user_files_from_firebase(email)
    return {"files": files, "count": len(files)}

@router.get("/health")
def health_check():
    """Health check"""
    try:
        users_count = len(list(db.collection('users').stream()))
        files_count = len(list(db.collection('user_files').stream()))
        return {
            "status": "healthy",
            "database": "Firebase Firestore",
            "users_count": users_count,
            "files_count": files_count
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
    

    #============================================================== 

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/login")
async def login(req: LoginRequest):
    user = get_user_from_firebase(req.email)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if user.get("auth_provider") != "email":
        raise HTTPException(status_code=400, detail="Use Google login")

    if not verify_password(req.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    session_token = generate_session_token()
    save_session_token(db, req.email, session_token)

    return {
        "message": "Login successful",
        "email": req.email,
        "name": user["name"],
        "session_token": session_token
    }