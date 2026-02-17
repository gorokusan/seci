# app/init_db.py
import os
from pathlib import Path

from sqlalchemy import create_engine, text

# ★ ここはあなたの models.py が Base = declarative_base() を持っている前提
from app.models import Base
import app.models  # モデル定義を確実に読み込ませる（副作用でテーブル定義が揃う）

def main():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is not set")

    # まれに postgres:// が来るケースの保険
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    engine = create_engine(db_url, pool_pre_ping=True)

    # 1) まず ORM 定義からテーブル作成（sessions を確実に作る）
    Base.metadata.create_all(bind=engine)

    # 2) migrations/init.sql があるなら流す（既存ならエラー無視）
    sql_path = Path(__file__).resolve().parent.parent / "migrations" / "init.sql"
    if sql_path.exists():
        sql = sql_path.read_text(encoding="utf-8")
        with engine.begin() as conn:
            for stmt in sql.split(";"):
                stmt = stmt.strip()
                if not stmt:
                    continue
                try:
                    conn.execute(text(stmt))
                except Exception as e:
                    print(f"[WARN] {e}")

    # 3) デバッグ：sessions の存在確認（ログで見える）
    with engine.begin() as conn:
        r = conn.execute(text("SELECT to_regclass('public.sessions')")).scalar()
        print("sessions table:", r)

if __name__ == "__main__":
    main()

