"""
Конфигурация сервера
"""
import os
from typing import Dict, Any

# Настройки сервера
SERVER_IP = "0.0.0.0"


TCP_PORTS_ENV = os.getenv("TCP_PORTS", "9066,10001")
TCP_PORTS = [int(port.strip()) for port in TCP_PORTS_ENV.split(",") if port.strip()]

HTTP_PORT = 8000

# Настройки базы данных
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "",
    "db": "zaryd",
    "autocommit": True
}



# Настройки логирования
LOG_LEVEL = "INFO"
TCP_PACKETS_LOG = "logs/tcp_packets.log"  

# Настройки JWT
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Настройки соединений
CONNECTION_TIMEOUT = 30   # 30 секунд - таймаут для heartbeat
HEARTBEAT_INTERVAL = 30   # 30 секунд

# Настройки безопасности паролей
PASSWORD_MIN_LENGTH = 6
PASSWORD_MAX_LENGTH = 36  # Защита от атак по стороннему каналу
PASSWORD_HASH_ROUNDS = 12  # Для bcrypt

# Настройки уведомлений
NOTIFICATION_CONFIG = {
    "smtp": {
        "enabled": os.getenv("SMTP_ENABLED", "true").lower() == "true",  
        "host": "smtp.mail.ru",
        "port": 587,
        "use_tls": True,
        "username": "v.bazarov142@mail.ru",
        "password": "aj3wqoCmWQbJFtRQdp8V",
        "from_email": "v.bazarov142@mail.ru",
        "app_name": "ЗАРЯД",
        "max_retries": int(os.getenv("SMTP_MAX_RETRIES", "2"))  # Количество повторных попыток
    },
    "sms": {
        "enabled": False,  
        "provider": "none"
    },
    "admin_email": "admin@powerbank.app"
}

MAX_PACKET_SIZE = 1024  # Максимальный размер пакета в байтах
