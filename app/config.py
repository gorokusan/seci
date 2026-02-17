# app/config.py
import os
from datetime import timedelta
from redis import Redis

class Config:
    SECRET_KEY = os.getenv("SECI", "dev-secret-change-me")

    database_url = os.getenv("DATABASE_URL")
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {}

    SITE_URL = os.getenv("SITE_URL", "")

    redis_url = os.getenv("REDIS_URL")

    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(days=int(os.getenv("SESSION_TIMEOUT", "180")))
    SESSION_PERMANENT = True
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = "seci_session:"

    if redis_url:
        SESSION_TYPE = "redis"
        SESSION_REDIS = Redis.from_url(redis_url)
    else:
        SESSION_TYPE = "filesystem"
        SESSION_REDIS = None
