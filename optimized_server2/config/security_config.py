"""
Конфигурация безопасности
"""
import os
from typing import Dict, Any

# Настройки безопасности
SECURITY_CONFIG = {
    # DDoS защита
    'ddos_protection': {
        'max_requests_per_minute': 60,
        'max_requests_per_hour': 1000,
        'block_duration': 300,  # 5 минут
        'cleanup_interval': 3600  # 1 час
    },
    
    # Rate limiting
    'rate_limiting': {
        'max_requests': 100,
        'time_window': 60,  # секунды
        'burst_limit': 20
    },
    
    # Размеры запросов
    'request_limits': {
        'max_request_size': 10 * 1024 * 1024,  # 10MB
        'max_json_depth': 10,
        'max_json_size': 1024 * 1024  # 1MB
    },
    
    # Валидация данных
    'validation': {
        'max_string_length': 1000,
        'max_phone_length': 20,
        'max_email_length': 255,
        'max_fio_length': 255,
        'max_box_id_length': 50,
        'max_iccid_length': 50
    },
    
    # Заголовки безопасности
    'security_headers': {
        'x_content_type_options': 'nosniff',
        'x_frame_options': 'DENY',
        'x_xss_protection': '1; mode=block',
        'referrer_policy': 'strict-origin-when-cross-origin',
        'content_security_policy': (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:"
        )
    },
    
    # Паттерны атак
    'attack_patterns': {
        'xss_patterns': [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'vbscript:',
            r'on\w+\s*=',
            r'<iframe[^>]*>',
            r'<object[^>]*>',
            r'<embed[^>]*>',
            r'<link[^>]*>',
            r'<meta[^>]*>',
            r'<style[^>]*>.*?</style>'
        ],
        'sql_patterns': [
            r'union\s+select',
            r'drop\s+table',
            r'delete\s+from',
            r'insert\s+into',
            r'update\s+.*\s+set',
            r'or\s+1\s*=\s*1',
            r'\'\s*or\s*\'\w*\'\s*=\s*\'\w*\'',
            r'\'\s*or\s*1\s*=\s*1',
            r'\'\s*;\s*--',
            r'\'\s*;\s*drop',
            r'\'\s*;\s*insert',
            r'\'\s*;\s*update',
            r'\'\s*;\s*delete',
            r'exec\s*\(',
            r'execute\s*\(',
            r'sp_',
            r'xp_',
            r'waitfor\s+delay',
            r'benchmark\s*\(',
            r'sleep\s*\(',
            r'load_file\s*\(',
            r'into\s+outfile',
            r'into\s+dumpfile'
        ]
    },
    
    # Логирование безопасности
    'security_logging': {
        'log_attacks': True,
        'log_blocked_ips': True,
        'log_suspicious_requests': True,
        'log_file': 'security.log'
    }
}

# Получение конфигурации
def get_security_config() -> Dict[str, Any]:
    """Возвращает конфигурацию безопасности"""
    return SECURITY_CONFIG

def get_ddos_config() -> Dict[str, Any]:
    """Возвращает конфигурацию DDoS защиты"""
    return SECURITY_CONFIG['ddos_protection']

def get_rate_limiting_config() -> Dict[str, Any]:
    """Возвращает конфигурацию rate limiting"""
    return SECURITY_CONFIG['rate_limiting']

def get_request_limits() -> Dict[str, Any]:
    """Возвращает лимиты запросов"""
    return SECURITY_CONFIG['request_limits']

def get_validation_config() -> Dict[str, Any]:
    """Возвращает конфигурацию валидации"""
    return SECURITY_CONFIG['validation']

def get_security_headers() -> Dict[str, str]:
    """Возвращает заголовки безопасности"""
    return SECURITY_CONFIG['security_headers']

def get_attack_patterns() -> Dict[str, list]:
    """Возвращает паттерны атак"""
    return SECURITY_CONFIG['attack_patterns']

