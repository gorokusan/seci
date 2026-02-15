"""
アプリケーション設定
"""
import os
from datetime import timedelta
from dotenv import load_dotenv
import redis

load_dotenv()

class Config:
    """基本設定クラス"""
    
    # Flask基本設定
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_ENV = os.getenv('FLASK_ENV', 'production')
    DEBUG = FLASK_ENV == 'development'
    
    # データベース設定
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://seciuser:secipass@localhost:5432/secidb')
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_size': 10,
        'max_overflow': 20
    }
    
    # Redis設定
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    SESSION_REDIS = redis.from_url(REDIS_URL)
    
    # セッション設定
    SESSION_TYPE = 'redis'
    SESSION_PERMANENT = True
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'seci:'
    PERMANENT_SESSION_LIFETIME = timedelta(days=int(os.getenv('SESSION_TIMEOUT', 180)))
    SESSION_COOKIE_SECURE = True  # HTTPS必須
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # アプリケーション設定
    MAX_NODES_PER_USER = int(os.getenv('MAX_NODES_PER_USER', 1000))
    MAX_CONNECTIONS_PER_NODE = int(os.getenv('MAX_CONNECTIONS_PER_NODE', 50))
    DATA_RETENTION_DAYS = int(os.getenv('DATA_RETENTION_DAYS', 180))
    
    # SEO設定
    SITE_NAME = os.getenv('SITE_NAME', 'SECI Knowledge Mapper')
    SITE_DESCRIPTION = os.getenv('SITE_DESCRIPTION', 
        'SECIモデル（共同化・表出化・連結化・内面化）に基づく知識創造プロセスの可視化・管理ツール')
    SITE_URL = os.getenv('SITE_URL', 'https://localhost')
    SITE_KEYWORDS = 'SECI,知識創造,ナレッジマネジメント,共同化,表出化,連結化,内面化,野中郁次郎'
    
    # セキュリティ設定
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    
    # アップロード設定
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB
    
    # ログ設定
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')


class DevelopmentConfig(Config):
    """開発環境設定"""
    DEBUG = True
    TESTING = False
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    """本番環境設定"""
    DEBUG = False
    TESTING = False


class TestingConfig(Config):
    """テスト環境設定"""
    TESTING = True
    WTF_CSRF_ENABLED = False


# 環境別設定の取得
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': ProductionConfig
}
