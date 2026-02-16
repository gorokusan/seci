"""
データベース接続管理
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from contextlib import contextmanager

db_session = None
engine = None

def init_db(app):
    """データベース初期化"""
    db_url = app.config.get("SQLALCHEMY_DATABASE_URI")
    if not db_url:
        raise RuntimeError("DATABASE_URL is not set. Please set DATABASE_URL in Render Environment.")

    global db_session, engine
    
    engine = create_engine(
    app.config["SQLALCHEMY_DATABASE_URI"],
    **(app.config.get("SQLALCHEMY_ENGINE_OPTIONS") or {})
    )
    
    db_session = scoped_session(
        sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine
        )
    )
    
    # アプリケーションコンテキストにDB sessionを追加
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        if db_session:
            db_session.remove()


@contextmanager
def get_db():
    """データベースセッションのコンテキストマネージャー"""
    try:
        yield db_session
        db_session.commit()
    except Exception:
        db_session.rollback()
        raise
    finally:
        db_session.close()


def get_session():
    """データベースセッション取得"""
    return db_session
