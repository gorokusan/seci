#!/bin/bash

# SSL証明書生成スクリプト
# 開発環境用の自己署名証明書を生成します

set -e

echo "SSL証明書を生成しています..."

# SSLディレクトリの作成
mkdir -p nginx/ssl

# 自己署名証明書の生成
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout nginx/ssl/key.pem \
    -out nginx/ssl/cert.pem \
    -subj "/C=JP/ST=Tokyo/L=Tokyo/O=SECI Mapper/CN=localhost"

# パーミッションの設定
chmod 600 nginx/ssl/key.pem
chmod 644 nginx/ssl/cert.pem

echo "✅ SSL証明書の生成が完了しました"
echo "証明書の場所: nginx/ssl/cert.pem"
echo "秘密鍵の場所: nginx/ssl/key.pem"
echo ""
echo "⚠️  注意: これは開発用の自己署名証明書です"
echo "本番環境では Let's Encrypt などの正式な証明書を使用してください"
