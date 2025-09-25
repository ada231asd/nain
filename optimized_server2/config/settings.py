"""
Конфигурация сервера
"""
import os
from typing import Dict, Any

# Настройки сервера
SERVER_IP = "0.0.0.0"
TCP_PORT = 9066
HTTP_PORT = 8000

# Настройки базы данных
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "appuser",
    "password": "MyPassw0rd!",
    "db": "zaryd",
    "autocommit": True
}

# Настройки логирования
LOG_LEVEL = "INFO"
LOG_FILE = "tcp_server.log"
EXCEPTION_LOG_FILE = "exceptions.log"
API_REQUESTS_LOG = "api_requests.log"

# Настройки JWT
JWT_SECRET_KEY = "your-secret-key-here"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Настройки соединений
CONNECTION_TIMEOUT = 300  # 5 минут
HEARTBEAT_INTERVAL = 30   # 30 секунд
