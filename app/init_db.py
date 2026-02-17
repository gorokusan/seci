import os
from sqlalchemy import create_engine, text

def main():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is not set")

    # RenderのURLが postgres:// になることがあるので補正
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    engine = create_engine(db_url, pool_pre_ping=True)

    # 1) まず migrations/init.sql があれば流す（あなたの方式）
    sql_path = os.path.join(os.path.dirname(__file__), "migrations", "init.sql")
    if os.path.exists(sql_path):
        with open(sql_path, "r", encoding="utf-8") as f:
            sql = f.read()
        with engine.begin() as conn:
            conn.execute(text(sql))
        print("Applied migrations/init.sql")
    else:
        print("migrations/init.sql not found, skipping SQL init")

    # 2) 念のため sessions テーブルの存在チェック（デバッグ用）
    with engine.begin() as conn:
        r = conn.execute(text("SELECT to_regclass('public.sessions')")).scalar()
        print("sessions table:", r)

if __name__ == "__main__":
    main()

