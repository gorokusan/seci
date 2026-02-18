FROM python:3.11-slim

# 作業ディレクトリの設定
WORKDIR /app

# システムパッケージの更新とインストール
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python依存関係のインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションファイルのコピー
COPY app ./app
COPY migrations ./migrations

# 非rootユーザーの作成
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# ヘルスチェック用のポート公開
EXPOSE 5000

# Flaskアプリケーションの起動
#CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--threads", "2", "--timeout", "120", "app:create_app()"]
CMD ["sh", "-c", "python -m app.init_db && exec gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 4 --threads 2 --timeout 120 \"app:create_app()\" --access-logfile - --error-logfile - --log-level debug"]
