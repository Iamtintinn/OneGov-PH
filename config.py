import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "onegov-ph-development-key")

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://root:@localhost/onegov_ph"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0") == "1"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_REFRESH_EACH_REQUEST = True

    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0") == "1"

    # Maya Checkout — sandbox only for this portfolio project.
    MAYA_ENVIRONMENT = os.getenv("MAYA_ENVIRONMENT", "sandbox").strip().lower()
    MAYA_PUBLIC_KEY = os.getenv("MAYA_PUBLIC_KEY", "").strip()
    MAYA_SECRET_KEY = os.getenv("MAYA_SECRET_KEY", "").strip()
    MAYA_API_URL = os.getenv("MAYA_API_URL", "https://pg-sandbox.paymaya.com").strip().rstrip("/")
    MAYA_WEBHOOK_BASE_URL = os.getenv("MAYA_WEBHOOK_BASE_URL", "").strip().rstrip("/")
    # Public origin used for Maya success/failure/cancel redirects (QRPh-friendly).
    # Prefer an HTTPS tunnel (ngrok) over localhost so wallet/QR returns keep working.
    MAYA_PUBLIC_BASE_URL = os.getenv("MAYA_PUBLIC_BASE_URL", "").strip().rstrip("/")

    OSRM_API = os.getenv("OSRM_API", "").strip().rstrip("/")
    NOMINATIM_API = os.getenv("NOMINATIM_API", "").strip().rstrip("/")

    # Brevo transactional email (OTP)
    BREVO_API_KEY = os.getenv("BREVO_API_KEY", "").strip()
    BREVO_API_URL = os.getenv("BREVO_API_URL", "https://api.brevo.com/v3/smtp/email").strip()
    BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL", "no-reply@onegovph.local").strip()
    BREVO_SENDER_NAME = os.getenv("BREVO_SENDER_NAME", "OneGov PH").strip()
    BREVO_SMTP_LOGIN = os.getenv("BREVO_SMTP_LOGIN", "").strip()
    BREVO_SMTP_SERVER = os.getenv("BREVO_SMTP_SERVER", "smtp-relay.brevo.com").strip()
    BREVO_SMTP_PORT = int(os.getenv("BREVO_SMTP_PORT", "587") or 587)
    OTP_EXPIRY_MINUTES = int(os.getenv("OTP_EXPIRY_MINUTES", "5") or 5)
    OTP_MAX_ATTEMPTS = int(os.getenv("OTP_MAX_ATTEMPTS", "5") or 5)
    OTP_RESEND_COOLDOWN_SECONDS = int(os.getenv("OTP_RESEND_COOLDOWN_SECONDS", "60") or 60)

    # Gemini AI Chatbot
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
