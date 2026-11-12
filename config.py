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
