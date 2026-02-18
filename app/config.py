# app/config.py
import os
from datetime import timedelta
from redis import Redis

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    FLASK_ENV = os.getenv("FLASK_ENV", "production")
    MAX_NODES_PER_USER = int(os.getenv("MAX_NODES_PER_USER", "200"))

    # ---- DB ----
    DATABASE_URL = os.getenv("DATABASE_URL")
    if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # これが無いと database.py 側で KeyError になり得る
    SQLALCHEMY_ENGINE_OPTIONS = {}

    # ---- Redis (任意) ----
    # Render 無料で Redis を使わないなら、REDIS_URL は未設定でOK（=無効化）
    REDIS_URL = os.getenv("REDIS_URL", "")
    if REDIS_URL:
        SESSION_TYPE = "redis"
        SESSION_REDIS = Redis.from_url(REDIS_URL)
    else:
        SESSION_TYPE = "filesystem"
        SESSION_REDIS = None

    SESSION_PERMANENT = True
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = "seci_session:"
    PERMANENT_SESSION_LIFETIME = timedelta(days=int(os.getenv("SESSION_TIMEOUT", "180")))

    SESSION_COOKIE_SECURE = (FLASK_ENV == "production")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    SITE_URL = os.getenv("SITE_URL", "https://seci-p6co.onrender.com")

