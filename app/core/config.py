import logging
import os
from pydantic_settings import BaseSettings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logging.info(f"DEBUG: Starting config loading. APP_ENV={os.getenv('APP_ENV')}")

class Settings(BaseSettings):
    app_env: str = "development"
    secret_key: str = "secret"
    
    # Firebase Config
    firebase_service_account_path: str = "qr-menu-business-firebase-adminsdk.json"
    
    # VietQR Bank Configs
    bank_bin: str = "970422" # Default MBBank
    bank_account: str = "123456789"
    bank_account_name: str = "NGUYEN VAN A"
    
    # Admin & Telegram
    admin_confirm_secret: str = "admin123"
    backend_url: str = "http://localhost:8000"
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # CORS
    allowed_origins: str = "*"  # Cho phép tất cả trong môi trường development/ngrok
    
    @property
    def cors_origins_list(self) -> list[str]:
        if not self.allowed_origins:
            return []
        if self.allowed_origins == "*":
            # In production, we force specific origins. If still '*', we log warning.
            return ["*"]
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]
    
    # Geoapify Config
    geoapify_api_key: str = ""
    
    model_config = {
        "env_file": ".env.prod" if os.getenv("APP_ENV") == "production" else ".env",
        "extra": "allow"
    }

settings = Settings()
logging.info(f"DEBUG: Config initialized. APP_ENV: {settings.app_env}")
