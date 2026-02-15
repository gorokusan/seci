FROM nginx:1.25-alpine

# Nginxの設定ファイルを削除
RUN rm /etc/nginx/conf.d/default.conf

# カスタムNginx設定をコピー
COPY nginx.conf /etc/nginx/nginx.conf

# SSL証明書用のディレクトリを作成
RUN mkdir -p /etc/nginx/ssl

# ヘルスチェック用のcurlをインストール
RUN apk add --no-cache curl

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
