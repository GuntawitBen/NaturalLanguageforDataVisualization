from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from firebase_admin import firestore
import re
from Auth.firebase import db, get_user_from_firebase
from Auth.Auth_utils import hash_password

router = APIRouter(prefix="/auth", tags=["Sign Up"])

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str
    first_name: str
    last_name: str

@router.post('/register')
async def register(req: RegisterRequest):
    """Register a new user with email/password"""
    try:
        # Validate password strength
        if len(req.password) < 8:
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
        if not re.search(r'[A-Z]', req.password):
            raise HTTPException(status_code=400, detail="Password must contain uppercase letter")
        if not re.search(r'[a-z]', req.password):
            raise HTTPException(status_code=400, detail="Password must contain lowercase letter")
        if not re.search(r'[0-9]', req.password):
            raise HTTPException(status_code=400, detail="Password must contain number")
        
        # Check if user exists
        existing_user = get_user_from_firebase(req.email)
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Hash password
        hashed_password = hash_password(req.password)
        
        # Save to Firestore
        user_ref = db.collection('users').document(req.email)
        user_ref.set({
            'email': req.email,
            'password': hashed_password,
            'name': req.name,
            'first_name': req.first_name,
            'last_name': req.last_name,
            'picture': None,
            'auth_provider': 'email',
            'created_at': firestore.SERVER_TIMESTAMP,
            'last_login': firestore.SERVER_TIMESTAMP
        })
        
        print(f"User registered: {req.name} ({req.email})")
        
        return {
            "message": "User registered successfully",
            "email": req.email,
            "name": req.name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")