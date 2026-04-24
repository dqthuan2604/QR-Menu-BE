import logging
import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
from app.core.config import settings

db = None

def initialize_firebase():
    global db
    try:
        # 1. Thử đọc từ biến môi trường FIREBASE_SERVICE_ACCOUNT (Dùng cho Railway/Cloud)
        service_account_info = os.getenv("FIREBASE_SERVICE_ACCOUNT")
        logging.info(f"DEBUG: FIREBASE_SERVICE_ACCOUNT env present: {bool(service_account_info)}")
        
        if service_account_info:
            # Nếu biến môi trường chứa chuỗi JSON, ta parse nó
            logging.info("DEBUG: Using FIREBASE_SERVICE_ACCOUNT from env")
            info = json.loads(service_account_info)
            cred = credentials.Certificate(info)
        else:
            # 2. Nếu không có biến môi trường, thử đọc từ file (Dùng cho Local)
            path = settings.firebase_service_account_path
            logging.info(f"DEBUG: Using FIREBASE_SERVICE_ACCOUNT_PATH: {path}")
            if os.path.exists(path):
                logging.info(f"DEBUG: Found credentials file at {path}")
                cred = credentials.Certificate(path)
            else:
                logging.warning("⚠️ DEBUG: Firebase credentials not found. Database will be disabled.")
                return None

        firebase_admin.initialize_app(cred)
        db = firestore.client()
        logging.info("✅ DEBUG: Firebase initialized successfully.")
        return db
    except Exception as e:
        logging.error(f"❌ DEBUG: Error initializing Firebase: {e}")
        return None

def get_db():
    if db is None:
        return initialize_firebase()
    return db
