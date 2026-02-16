"""Gunicorn設定ファイル"""
import os
import multiprocessing

# サーバーソケット
bind = f"0.0.0.0:{os.getenv('PORT', '10000')}"

# ワーカー設定
workers = int(os.getenv('WEB_CONCURRENCY', multiprocessing.cpu_count() * 2 + 1))
worker_class = 'sync'
worker_connections = 1000
timeout = 120
keepalive = 5

# ログ設定
accesslog = '-'
errorlog = '-'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# プロセス名
proc_name = 'seci-knowledge-mapper'

# セキュリティヘッダー
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190