"""
Firebase Authentication Middleware
Verifies Firebase ID tokens for API authentication
"""
from fastapi import HTTPException, Header
from typing import Optional
from firebase_admin import auth as firebase_auth
from Auth.firebase import db, save_user_to_firebase
from database import sync_user_from_firebase

async def verify_firebase_token(authorization: Optional[str] = Header(None)) -> dict:
    """
    Verify Firebase ID token and return user information

    This dependency should be used for endpoints that require Firebase authentication

    Usage:
        @router.get("/protected")
        async def protected_route(user: dict = Depends(verify_firebase_token)):
            return {"user": user}

    Returns:
        dict: User information containing uid, email, name, picture
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization header missing"
        )

    # Extract token from "Bearer <token>" format
    try:
        scheme, token = authorization.split()
        if scheme.lower() != 'bearer':
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication scheme. Use 'Bearer <token>'"
            )
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format. Expected 'Bearer <token>'"
        )

    # Verify Firebase ID token
    try:
        decoded_token = firebase_auth.verify_id_token(token)

        # Extract user information
        uid = decoded_token['uid']
        email = decoded_token.get('email')
        name = decoded_token.get('name', email)
        picture = decoded_token.get('picture')

        # Determine auth provider
        firebase_user = decoded_token.get('firebase', {})
        auth_provider = 'google' if firebase_user.get('sign_in_provider') == 'google.com' else 'email'

        # Sync user to Firebase Firestore (for backward compatibility)
        save_user_to_firebase(
            email=email,
            name=name,
            picture=picture,
            auth_provider=auth_provider
        )

        # Sync user to DuckDB (for dataset ownership)
        sync_user_from_firebase(
            user_id=uid,
            email=email,
            name=name,
            picture=picture,
            auth_provider=auth_provider
        )

        return {
            'uid': uid,
            'email': email,
            'name': name,
            'picture': picture,
            'auth_provider': auth_provider
        }

    except firebase_auth.InvalidIdTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid Firebase ID token"
        )
    except firebase_auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=401,
            detail="Firebase ID token has expired"
        )
    except firebase_auth.RevokedIdTokenError:
        raise HTTPException(
            status_code=401,
            detail="Firebase ID token has been revoked"
        )
    except firebase_auth.CertificateFetchError:
        raise HTTPException(
            status_code=500,
            detail="Error fetching Firebase public keys"
        )
    except Exception as e:
        print(f"[ERROR] Firebase token verification failed: {e}")
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {str(e)}"
        )

async def get_firebase_user_email(authorization: Optional[str] = Header(None)) -> str:
    """
    Simplified dependency that returns only the user's email

    Usage:
        @router.get("/my-data")
        async def get_my_data(user_email: str = Depends(get_firebase_user_email)):
            return {"email": user_email}
    """
    user = await verify_firebase_token(authorization)
    return user['email']

async def get_firebase_user_id(authorization: Optional[str] = Header(None)) -> str:
    """
    Simplified dependency that returns only the user's UID

    Usage:
        @router.get("/my-profile")
        async def get_profile(user_id: str = Depends(get_firebase_user_id)):
            return {"uid": user_id}
    """
    user = await verify_firebase_token(authorization)
    return user['uid']
