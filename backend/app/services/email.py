from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from ..config import settings

# SMTP settings come from backend/.env (MAIL_* keys). Never hardcode them here.
conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=settings.MAIL_TLS,
    MAIL_SSL_TLS=settings.MAIL_SSL,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)


async def _send(email: str, subject: str, body: str):
    message = MessageSchema(subject=subject, recipients=[email], body=body, subtype="plain")
    await FastMail(conf).send_message(message)


async def send_otp_email(email: str, otp: str):
    await _send(email, "Your OTP Code",
                f"Your OTP for verification is: {otp}. It expires in 10 minutes.")


async def send_reset_email(email: str, otp: str):
    await _send(email, "College AI Chatbot Password Reset OTP",
                f"Your OTP to reset your password is: {otp}")


async def send_admin_alert(subject: str, body: str):
    """Email every admin (ADMIN_EMAIL), e.g. when a website sync fails."""
    for admin in settings.admin_emails():
        await _send(admin, f"[Smart Campus Connect] {subject}", body)
