from pydantic_settings import BaseSettings
from typing import List
from pathlib import Path


class Settings(BaseSettings):
    # MongoDB
    mongodb_url: str = "mongodb://localhost:27017"
    database_name: str = "Fleety_db"

    # JWT
    secret_key: str = "your-super-secret-key-change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # CORS
    cors_origins: List[str] = ["*"]

    # Server
    debug: bool = True

    # Feature Flags
    enable_gemini_3_pro_preview: bool = True

    # Email Configuration (Optional)
    smtp_server: str = ""
    smtp_port: int = 587
    sender_email: str = ""
    sender_password: str = ""
    admin_email: str = ""

    class Config:
        env_file = str(Path(__file__).parent.parent / ".env")
        env_file_encoding = 'utf-8'
        extra = 'ignore'  # Ignore extra fields from .env


settings = Settings()
