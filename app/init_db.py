# app/init_db.py
from pathlib import Path
from flask import current_app
from sqlalchemy import text
from app.data:contentReference[oaicite:10]{index=10}_init():
    sql_path = Path(__file__).resolve().parent.parent / "migrations" / "init.sql"
    sql = sql_path.read_text(encoding="utf-8")
    with engine.begin() as conn:
        conn.execute(text(sql))

def main():
    # create_app() を使うならここで import して app_context を作る
    from app import create_app
    app = create_app()
    with app.app_context():
        run_sql_init()

if __name__ == "__main__":
    main()

