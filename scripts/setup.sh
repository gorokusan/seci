#!/bin/bash

# SECIモデル知識マッピングツール - セットアップスクリプト

set -e

echo "======================================"
echo "SECI Knowledge Mapper - セットアップ"
echo "======================================"

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. 必要なツールの確認
echo -e "\n${YELLOW}[1/6]${NC} 必要なツールの確認..."

command -v docker >/dev/null 2>&1 || { 
    echo -e "${RED}✗ Dockerがインストールされていません${NC}"
    exit 1
}
echo -e "${GREEN}✓ Docker${NC}"

command -v docker-compose >/dev/null 2>&1 || { 
    echo -e "${RED}✗ Docker Composeがインストールされていません${NC}"
    exit 1
}
echo -e "${GREEN}✓ Docker Compose${NC}"

# 2. 環境変数ファイルの作成
echo -e "\n${YELLOW}[2/6]${NC} 環境変数ファイルの設定..."

if [ ! -f .env ]; then
    echo -e "${YELLOW}→ .envファイルが見つかりません。作成します...${NC}"
    cp .env.example .env
    
    # シークレットキーの生成
    SECRET_KEY=$(openssl rand -hex 32)
    sed -i "s/your_very_secret_key_change_this_in_production/$SECRET_KEY/" .env
    
    # パスワードの生成
    DB_PASSWORD=$(openssl rand -base64 16)
    sed -i "s/your_secure_password_here/$DB_PASSWORD/" .env
    
    echo -e "${GREEN}✓ .envファイルを作成しました${NC}"
else
    echo -e "${GREEN}✓ .envファイルは既に存在します${NC}"
fi

# 3. SSL証明書の生成
echo -e "\n${YELLOW}[3/6]${NC} SSL証明書の生成..."

if [ ! -f nginx/ssl/cert.pem ]; then
    echo -e "${YELLOW}→ SSL証明書を生成します...${NC}"
    ./scripts/generate_ssl.sh
else
    echo -e "${GREEN}✓ SSL証明書は既に存在します${NC}"
fi

# 4. ディレクトリの作成
echo -e "\n${YELLOW}[4/6]${NC} 必要なディレクトリの作成..."

mkdir -p app/static/images
mkdir -p app/static/css
mkdir -p app/static/js

echo -e "${GREEN}✓ ディレクトリを作成しました${NC}"

# 5. Dockerイメージのビルド
echo -e "\n${YELLOW}[5/6]${NC} Dockerイメージのビルド..."

docker-compose build

echo -e "${GREEN}✓ ビルド完了${NC}"

# 6. コンテナの起動
echo -e "\n${YELLOW}[6/6]${NC} コンテナの起動..."

docker-compose up -d

echo -e "${GREEN}✓ コンテナを起動しました${NC}"

# 起動確認
echo -e "\n${YELLOW}起動確認中...${NC}"
sleep 5

if docker-compose ps | grep -q "Up"; then
    echo -e "\n${GREEN}======================================"
    echo -e "セットアップが完了しました！"
    echo -e "======================================${NC}"
    echo ""
    echo "アクセスURL:"
    echo "  HTTPS: https://localhost"
    echo "  HTTP:  http://localhost (自動的にHTTPSにリダイレクト)"
    echo ""
    echo "コンテナ管理:"
    echo "  ログ確認:   docker-compose logs -f"
    echo "  停止:       docker-compose down"
    echo "  再起動:     docker-compose restart"
    echo ""
    echo -e "${YELLOW}注意:${NC} 自己署名証明書を使用しているため、ブラウザで"
    echo "セキュリティ警告が表示されます。本番環境では正式な証明書を"
    echo "使用してください。"
else
    echo -e "\n${RED}======================================"
    echo -e "エラー: コンテナの起動に失敗しました"
    echo -e "======================================${NC}"
    echo "詳細を確認してください:"
    echo "  docker-compose logs"
    exit 1
fi
