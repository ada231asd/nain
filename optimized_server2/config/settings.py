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
    "user": "root",
    "password": "",
    "db": "DB",
    "autocommit": True
}

# Настройки логирования
LOG_LEVEL = "INFO"
TCP_PACKETS_LOG = "logs/tcp_packets.log"  

# Настройки JWT
JWT_SECRET_KEY = "your-secret-key-here"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Настройки соединений
CONNECTION_TIMEOUT = 300  # 5 минут
HEARTBEAT_INTERVAL = 30   # 30 секунд

# Настройки безопасности паролей
PASSWORD_MIN_LENGTH = 6
PASSWORD_MAX_LENGTH = 36  # Защита от атак по стороннему каналу
PASSWORD_HASH_ROUNDS = 12  # Для bcrypt


MAX_PACKET_SIZE = 1024  # Максимальный размер пакета в байтах
PROTOCOL_COMMAND_RANGE = (0x60, 0x8F)  # Диапазон команд протокола
MAX_SUSPICIOUS_PACKETS = 1  # Максимум подозрительных пакетов перед отключением
