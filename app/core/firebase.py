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
                msg = f"⚠️ DEBUG: Firebase credentials not found at {path} and FIREBASE_SERVICE_ACCOUNT env is missing."
                logging.error(msg)
                # Nếu đang trong môi trường CI/Test, trả về Mock thay vì lỗi
                if os.getenv("CI") == "true" or os.getenv("TESTING") == "true" or settings.app_env == "testing":
                    from unittest.mock import MagicMock
                    logging.warning("⚠️ DEBUG: CI/Testing environment detected. Returning Mock Firestore DB.")
                    db = MagicMock()
                    return db
                raise FileNotFoundError(msg)

        firebase_admin.initialize_app(cred)
        db = firestore.client()
        logging.info("✅ DEBUG: Firebase initialized successfully.")
        return db
    except Exception as e:
        # Nếu đã trả về mock ở trên thì e sẽ không bắt được, 
        # nhưng nếu initialize_app fail vì lý do khác trong CI, ta cũng trả về mock.
        if os.getenv("CI") == "true" or os.getenv("TESTING") == "true" or settings.app_env == "testing":
            from unittest.mock import MagicMock
            logging.warning(f"⚠️ DEBUG: Firebase init failed in CI/Test: {e}. Returning Mock Firestore DB.")
            db = MagicMock()
            return db
        error_msg = f"❌ DEBUG: Error initializing Firebase: {e}"
        logging.error(error_msg)
        raise RuntimeError(error_msg)

def get_db():
    if db is None:
        return initialize_firebase()
    return db
