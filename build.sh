#!/usr/bin/env bash
# exit on error
set -o errexit

# パッケージのインストール
pip install --upgrade pip
pip install -r requirements.txt

# データベースマイグレーション実行
