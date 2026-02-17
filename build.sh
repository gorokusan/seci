#!/usr/bin/env bash
# exit on error
set -euo pipefail

# パッケージのインストール
pip install -r requirements.txt

# データベースマイグレーション実行
python -m app.init_db
