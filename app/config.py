# app/config.py
import os
from datetime import timedelta
from redis import Redis

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    FLASK_ENV = os.getenv("FLASK_ENV", "production")

    database_url = os.getenv("DATABASE_URL")
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 3600,
    }

    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        SESSION_TYPE = "redis"
        SESSION_REDIS = Redis.from_url(redis_url)
    else:
        SESSION_TYPE = "filesystem"
        SESSION_REDIS = None

    SESSION_PERMANENT = True
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = "seci_session:"
    PERMANENT_SESSION_LIFETIME = timedelta(days=int(os.getenv("SESSION_TIMEOUT", 180)))

    SESSION_COOKIE_SECURE = (FLASK_ENV == "production")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    SITE_URL = os.getenv("SITE_URL")
    if not SITE_URL:
        host = os.getenv("RENDER_EXTERNAL_HOSTNAME")
        SITE_URL = f"https://{host}" if host else "https://seci-p6co.onrender.com"
