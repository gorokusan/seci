"""
SECIモデル知識マッピングツール - Flaskアプリケーション
"""
from flask import Flask
from flask_cors import CORS
from flask_session import Session
import os
from .config import Config
from .database import init_db
from .cache_manager import init_cache

def create_app(config_class=Config):
    """Flaskアプリケーションファクトリ"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # CORS設定
    CORS(app, supports_credentials=True)
    
    # セッション設定
    Session(app)
    
    # データベース初期化
    init_db(app)
    
    # キャッシュ初期化
    init_cache(app)
    
    # ブループリント登録
    from .routes import main_bp, api_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # エラーハンドラー
    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Not found'}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return {'error': 'Internal server error'}, 500
    
    # ヘルスチェックエンドポイント
    @app.route('/health')
    def health():
        return {'status': 'healthy'}, 200
    
    return app
