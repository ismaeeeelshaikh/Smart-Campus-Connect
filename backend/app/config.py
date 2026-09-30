from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/.env, resolved from this file so it works no matter where you start the app
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    database_url: str
    groq_api_key: str
    groq_model: str = "openai/gpt-oss-120b"
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    admin_email: str = ""
    # Comma-separated email domains allowed to sign up; empty = anyone. ADMIN_EMAIL can always sign up.
    allowed_signup_domains: str = "apsit.edu.in"
    # Comma-separated list of frontend URLs allowed to call the API
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_TLS: bool = True
    MAIL_SSL: bool = False

    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    def email_can_sign_up(self, email: str) -> bool:
        email = email.strip().lower()
        if self.admin_email and email == self.admin_email.strip().lower():
            return True
        domains = [d.strip().lower().lstrip("@") for d in self.allowed_signup_domains.split(",") if d.strip()]
        return not domains or email.rsplit("@", 1)[-1] in domains


settings = Settings()
