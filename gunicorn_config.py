# gunicorn_config.py
timeout = 120  # 2 minutes
workers = 2
worker_class = 'sync'
threads = 4
bind = "0.0.0.0:10000"
keepalive = 5
worker_connections = 1000
max_requests = 100
max_requests_jitter = 50
