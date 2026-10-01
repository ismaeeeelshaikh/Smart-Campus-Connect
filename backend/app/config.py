from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ folder, resolved from this file so paths work no matter where you start the app
BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    database_url: str
    groq_api_key: str
    groq_model: str = "openai/gpt-oss-120b"
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    # Admin(s): can start a website sync. Comma-separated for several admins.
    admin_email: str = ""
    # Comma-separated email domains allowed to sign up; empty = anyone. Admins can always sign up.
    allowed_signup_domains: str = "apsit.edu.in"
    # Comma-separated list of frontend URLs allowed to call the API
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    # Interactive API docs at /docs. Turn off in production.
    enable_docs: bool = True
    # Behind a reverse proxy (nginx etc.) the client's IP comes from X-Forwarded-For. Only enable
    # this when such a proxy is in front, otherwise anyone could fake their IP to dodge rate limits.
    trust_proxy_headers: bool = False

    # Knowledge base (relative paths are inside backend/)
    college_data_dir: str = "college_data"
    chroma_dir: str = "chroma_db"
    embedding_model: str = "BAAI/bge-base-en-v1.5"

    # Website sync (https://www.apsit.edu.in). 0 hours = no automatic sync (admins can still start one).
    crawl_interval_hours: float = 6
    crawl_max_pages: int = 2000
    crawl_delay_seconds: float = 0.5
    crawl_include_pdfs: bool = True
    crawl_max_pdfs: int = 60

    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_TLS: bool = True
    MAIL_SSL: bool = False

    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    def is_admin(self, email: str) -> bool:
        admins = {e.strip().lower() for e in self.admin_email.split(",") if e.strip()}
        return email.strip().lower() in admins

    def email_can_sign_up(self, email: str) -> bool:
        email = email.strip().lower()
        if self.is_admin(email):
            return True
        domains = [d.strip().lower().lstrip("@") for d in self.allowed_signup_domains.split(",") if d.strip()]
        return not domains or email.rsplit("@", 1)[-1] in domains

    def backend_path(self, path: str) -> Path:
        p = Path(path)
        return p if p.is_absolute() else BACKEND_DIR / p


settings = Settings()
