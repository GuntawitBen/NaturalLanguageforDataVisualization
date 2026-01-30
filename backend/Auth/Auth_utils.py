import bcrypt
import secrets
from datetime import datetime, timedelta
from fastapi import HTTPException, Header
from typing import Optional

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)

def generate_session_token() -> str:
    """Generate a random session token"""
    return secrets.token_urlsafe(32)

def save_session_token(db, email: str, token: str):
    """Save session token to Firestore"""
    try:
        from firebase_admin import firestore
        session_ref = db.collection('sessions').document(token)
        session_ref.set({
            'email': email,
            'created_at': firestore.SERVER_TIMESTAMP,
            'expires_at': datetime.utcnow() + timedelta(days=7)
        })
        return True
    except Exception as e:
        print(f"Error saving session token: {e}")
        return False

def verify_session_token(db, token: str) -> Optional[str]:
    """Verify session token and return user email"""
    try:
        print(f"[AUTH] Looking up session document for token: {token[:20]}...")
        session_ref = db.collection('sessions').document(token)
        session = session_ref.get()

        if not session.exists:
            print(f"[AUTH] Session document does not exist")
            return None

        session_data = session.to_dict()
        print(f"[AUTH] Found session data: email={session_data.get('email')}")

        # Check if token is expired
        expires_at = session_data.get('expires_at')
        if expires_at:
            # Handle both timezone-aware and naive datetimes
            current_time = datetime.utcnow()

            # If expires_at is timezone-aware, make current_time aware too
            if hasattr(expires_at, 'tzinfo') and expires_at.tzinfo is not None:
                from datetime import timezone
                current_time = datetime.now(timezone.utc)

            # Convert expires_at to naive if it's aware
            if hasattr(expires_at, 'replace') and hasattr(expires_at, 'tzinfo') and expires_at.tzinfo is not None:
                expires_at = expires_at.replace(tzinfo=None)
                current_time = datetime.utcnow()

            if expires_at < current_time:
                print(f"[AUTH] Token expired: {expires_at} < {current_time}")
                session_ref.delete()
                return None

        return session_data.get('email')
    except Exception as e:
        print(f"[AUTH] Error verifying session token: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None

def delete_session_token(db, token: str):
    """Delete session token from Firestore"""
    try:
        session_ref = db.collection('sessions').document(token)
        session_ref.delete()
        return True
    except Exception as e:
        print(f"Error deleting session token: {e}")
        return False

async def get_current_user(authorization: Optional[str] = Header(None)):
    """Dependency to get current user from session token"""
    from Auth.firebase import db

    if not authorization:
        print("[AUTH] Missing authorization header")
        raise HTTPException(status_code=401, detail="Authorization header missing")

    # Extract token from "Bearer <token>" format
    try:
        scheme, token = authorization.split()
        if scheme.lower() != 'bearer':
            print(f"[AUTH] Invalid scheme: {scheme}")
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
    except ValueError:
        print(f"[AUTH] Invalid format: {authorization[:50]}...")
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

    print(f"[AUTH] Verifying token: {token[:20]}...")
    email = verify_session_token(db, token)

    if not email:
        print(f"[AUTH] Token verification failed for: {token[:20]}...")
        raise HTTPException(status_code=401, detail="Invalid or expired session token")

    print(f"[AUTH] Success for user: {email}")
    return email

async def get_current_user_and_token(authorization: Optional[str] = Header(None)):
    """Dependency to get current user email and token"""
    from Auth.firebase import db

    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    # Extract token from "Bearer <token>" format
    try:
        scheme, token = authorization.split()
        if scheme.lower() != 'bearer':
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

    email = verify_session_token(db, token)

    if not email:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")

    return {"email": email, "token": token}