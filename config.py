import os
from datetime import timedelta
from urllib.parse import quote

from dotenv import load_dotenv

load_dotenv()

DEFAULT_LOCAL_DATABASE_URL = "mysql+pymysql://root:@localhost/onegov_ph"


def _env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "required"}


def _using_tidb():
    mode = (os.getenv("DATABASE_MODE") or "auto").strip().lower()
    if mode == "tidb":
        return True
    if mode == "local":
        return False
    return bool((os.getenv("DB_HOST") or "").strip())


def _build_database_uri():
    """Build the SQLAlchemy URI from DATABASE_URL or the TiDB DB_* variables.

    DATABASE_MODE controls the active environment:
      - local: always use DATABASE_URL (XAMPP/MySQL).
      - tidb / cloud: build mysql+pymysql from DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME.
      - auto (default): use DB_* when DB_HOST is set, otherwise DATABASE_URL.
    Existing DATABASE_URL values without a mode still work for local development.
    """
    database_url = (os.getenv("DATABASE_URL") or "").strip()
    mode = (os.getenv("DATABASE_MODE") or "auto").strip().lower()

    if mode == "local":
        return database_url or DEFAULT_LOCAL_DATABASE_URL

    db_host = (os.getenv("DB_HOST") or "").strip()
    if mode in {"tidb", "cloud"} and not db_host:
        raise RuntimeError(
            "DB_HOST is required when DATABASE_MODE=tidb/cloud. "
            "Add the TiDB Cloud host to your .env file."
        )
    if db_host:
        user = quote(os.getenv("DB_USER") or "", safe="")
        password = quote(os.getenv("DB_PASSWORD") or "", safe="")
        port = (os.getenv("DB_PORT") or "4000").strip()
        database = quote((os.getenv("DB_NAME") or "onegov_ph").strip(), safe="")
        return f"mysql+pymysql://{user}:{password}@{db_host}:{port}/{database}?charset=utf8mb4"

    return database_url or DEFAULT_LOCAL_DATABASE_URL


def _build_engine_options():
    """Engine options that keep TiDB Cloud TLS connections healthy."""
    options = {
        "pool_pre_ping": True,
        "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "280") or 280),
    }
    if not _using_tidb():
        return options

    if not _env_bool("DB_SSL", False):
        return options

    ca_path = (os.getenv("DB_SSL_CA") or "").strip()
    verify_cert = _env_bool("DB_SSL_VERIFY_CERT", bool(ca_path))
    verify_identity = _env_bool("DB_SSL_VERIFY_IDENTITY", bool(ca_path))
    connect_args = {
        "ssl_verify_cert": verify_cert,
        "ssl_verify_identity": verify_identity,
    }
    if ca_path:
        connect_args["ssl_ca"] = ca_path
    options["connect_args"] = connect_args
    return options


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "onegov-ph-development-key")

    SQLALCHEMY_DATABASE_URI = _build_database_uri()
    SQLALCHEMY_ENGINE_OPTIONS = _build_engine_options()

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
