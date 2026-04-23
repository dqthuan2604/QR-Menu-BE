from pydantic_settings import BaseSettings

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
    
    class Config:
        env_file = ".env"
        extra = "allow" # Cho phép các biến khác trong .env mà không báo lỗi

settings = Settings()
