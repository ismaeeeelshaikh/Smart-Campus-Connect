from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/.env, resolved from this file so it works no matter where you start the app
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    database_url: str
    groq_api_key: str
    groq_model: str = "llama-3.3-70b-versatile"
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    admin_email: str = ""

    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_TLS: bool = True
    MAIL_SSL: bool = False

    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")


settings = Settings()
