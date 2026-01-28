from authlib.integrations.starlette_client import OAuth
import os
import firebase_admin
from firebase_admin import credentials, firestore, auth
from dotenv import load_dotenv

load_dotenv()


#================================Fire base
def init_firebase():
    """Initialize Firebase Admin SDK"""
    try:
        # Try to get credentials from JSON string (Best for Cloud/Docker)
        firebase_creds_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
        
        if firebase_creds_json:
            import json
            cred_dict = json.loads(firebase_creds_json)
            cred = credentials.Certificate(cred_dict)
            print("Firebase initialized from environment variable JSON")
        else:
            # Fallback to file path (Best for Local Dev)
            cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "./firebase-credentials.json")
            if not os.path.exists(cred_path):
                print(f"[WARNING] Firebase credentials file not found at: {cred_path}")
                return None
                
            cred = credentials.Certificate(cred_path)
            print(f"Firebase initialized from file: {cred_path}")

        firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception as e:
        print(f"Firebase initialization failed: {e}")
        return None

# Initialize Firebase
db = init_firebase()

def save_user_to_firebase(email: str, name: str, picture: str = None,auth_provider: str = 'email'):
    """Save or update user in Firestore"""
    try:
        user_ref = db.collection('users').document(email)
        user_ref.set({
            'email': email,
            'name': name,
            'picture': picture,
            'auth_provider': auth_provider,  # ← Add this
            'created_at': firestore.SERVER_TIMESTAMP,
            'last_login': firestore.SERVER_TIMESTAMP
        }, merge=True)
        print(f"User saved to Firebase: {email}")
        return True
    except Exception as e:
        print(f"Error saving user to Firebase: {e}")
        return False

def get_user_from_firebase(email: str):
    """Retrieve user from Firestore"""
    try:
        user_ref = db.collection('users').document(email)
        user = user_ref.get()
        if user.exists:
            return user.to_dict()
        return None
    except Exception as e:
        print(f"Error getting user from Firebase: {e}")
        return None


def save_file_to_firebase(user_email: str, file_name: str, table_name: str, row_count: int, column_count: int):
    """Save uploaded file metadata to Firestore"""
    try:
        files_ref = db.collection('user_files')
        files_ref.add({
            'user_email': user_email,
            'file_name': file_name,
            'table_name': table_name,
            'upload_date': firestore.SERVER_TIMESTAMP,
            'row_count': row_count,
            'column_count': column_count
        })
        print(f"File metadata saved to Firebase: {file_name}")
        return True
    except Exception as e:
        print(f"Error saving file to Firebase: {e}")
        return False

def get_user_files_from_firebase(email: str):
    """Get all files uploaded by a user from Firestore"""
    try:
        files_ref = db.collection('user_files').where('user_email', '==', email).order_by('upload_date', direction=firestore.Query.DESCENDING)
        files = files_ref.stream()
        
        result = []
        for file in files:
            file_data = file.to_dict()
            file_data['id'] = file.id
            result.append(file_data)
        
        return result
    except Exception as e:
        print(f"Error getting user files from Firebase: {e}")
        return []