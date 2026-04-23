import firebase_admin
from firebase_admin import credentials, firestore
import json
import os
from app.core.config import settings

_db = None

def initialize_firebase():
    global _db
    try:
        # Check if already initialized
        firebase_admin.get_app()
    except ValueError:
        service_account_info = None
        
        # 1. Ưu tiên lấy từ Path trong Settings (Config qua .env)
        if settings.firebase_service_account_path and os.path.exists(settings.firebase_service_account_path):
            service_account_info = settings.firebase_service_account_path
        
        # 2. Fallback: Lấy trực tiếp JSON từ biến môi trường (string)
        elif os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON"):
            try:
                service_account_info = json.loads(os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON"))
            except:
                pass
            
        if service_account_info:
            cred = credentials.Certificate(service_account_info)
            firebase_admin.initialize_app(cred)
            print(f"🔥 Firebase Admin SDK initialized successfully from: {service_account_info}")
        else:
            print("⚠️ Firebase Admin SDK NOT initialized: Missing credentials.")
            return None

    if _db is None:
        _db = firestore.client()
    return _db

def get_db():
    global _db
    if _db is None:
        _db = initialize_firebase()
    return _db
