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

    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    SESSION_TYPE = "redis"
    SESSION_REDIS = Redis.from_url(redis_url)
    SESSION_PERMANENT = True
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = "seci_session:"
    PERMANENT_SESSION_LIFETIME = timedelta(days=int(os.getenv("SESSION_TIMEOUT", 180)))

    SESSION_COOKIE_SECURE = (FLASK_ENV == "production")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    SITE_URL = os.getenv("SITE_URL", "https://seci-p6co.onrender.com")
