"""
Middleware для безопасности HTTP сервера
"""
import asyncio
import time
import hashlib
import hmac
from typing import Dict, Set, Optional
from collections import defaultdict, deque
from aiohttp import web
import json
import re
import html


class SecurityMiddleware:
    """Middleware для защиты от различных атак"""
    
    def __init__(self):
        # Rate limiting
        self.rate_limits: Dict[str, deque] = defaultdict(lambda: deque())
        self.ip_requests: Dict[str, int] = defaultdict(int)
        self.blocked_ips: Set[str] = set()
        
        # DDoS protection
        self.request_times: Dict[str, deque] = defaultdict(lambda: deque())
        self.max_requests_per_minute = 60
        self.block_duration = 300  # 5 минут
        
        # XSS protection
        self.xss_patterns = [
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
        ]
        
        # SQL injection patterns
        self.sql_patterns = [
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
            r'\'\s*;\s*delete'
        ]
        
        # Combined patterns
        self.combined_patterns = self.xss_patterns + self.sql_patterns
    
    async def __call__(self, request, handler):
        """Основной метод middleware"""
        
        # Получаем IP адрес клиента
        client_ip = self._get_client_ip(request)
        
        # Проверяем, не заблокирован ли IP
        if client_ip in self.blocked_ips:
            return web.json_response({
                'error': 'IP заблокирован за подозрительную активность'
            }, status=403)
        
        try:
            # 1. DDoS защита - Rate Limiting
            if not await self._check_rate_limit(client_ip):
                return web.json_response({
                    'error': 'Слишком много запросов. Попробуйте позже.'
                }, status=429)
            
            # 2. Проверка размера запроса
            if not await self._check_request_size(request):
                return web.json_response({
                    'error': 'Слишком большой размер запроса'
                }, status=413)
            
            # 3. Проверка заголовков
            if not await self._check_headers(request):
                return web.json_response({
                    'error': 'Недопустимые заголовки'
                }, status=400)
            
            # 4. Проверка тела запроса на XSS и SQL инъекции
            if request.method in ['POST', 'PUT', 'PATCH']:
                if not await self._check_request_body(request):
                    return web.json_response({
                        'error': 'Обнаружена попытка атаки в данных запроса'
                    }, status=400)
            
            # 5. Проверка URL параметров
            if not await self._check_url_params(request):
                return web.json_response({
                    'error': 'Обнаружена попытка атаки в параметрах URL'
                }, status=400)
            
            # Выполняем запрос
            response = await handler(request)
            
            # Добавляем заголовки безопасности
            if isinstance(response, web.Response):
                self._add_security_headers(response)
            
            return response
            
        except Exception as e:
            # Логируем подозрительную активность
            print(f"Security exception for {client_ip}: {e}")
            
            # Блокируем IP при повторных нарушениях
            self.ip_requests[client_ip] += 1
            if self.ip_requests[client_ip] > 10:
                self.blocked_ips.add(client_ip)
                print(f"IP {client_ip} заблокирован за подозрительную активность")
            
            return web.json_response({
                'error': 'Обнаружена подозрительная активность'
            }, status=403)
    
    def _get_client_ip(self, request: web.Request) -> str:
        """Получает реальный IP клиента"""
        # Проверяем заголовки proxy
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        return request.remote
    
    async def _check_rate_limit(self, client_ip: str) -> bool:
        """Проверяет rate limiting"""
        current_time = time.time()
        
        # Очищаем старые записи
        while (self.rate_limits[client_ip] and 
               current_time - self.rate_limits[client_ip][0] > 60):
            self.rate_limits[client_ip].popleft()
        
        # Проверяем лимит
        if len(self.rate_limits[client_ip]) >= self.max_requests_per_minute:
            return False
        
        # Добавляем текущий запрос
        self.rate_limits[client_ip].append(current_time)
        return True
    
    async def _check_request_size(self, request: web.Request) -> bool:
        """Проверяет размер запроса"""
        content_length = request.headers.get('Content-Length')
        if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB
            return False
        return True
    
    async def _check_headers(self, request: web.Request) -> bool:
        """Проверяет заголовки на подозрительные значения"""
        suspicious_headers = ['X-Forwarded-For', 'X-Real-IP', 'User-Agent']
        
        for header in suspicious_headers:
            value = request.headers.get(header)
            if value and self._contains_attack_patterns(value):
                return False
        
        return True
    
    async def _check_request_body(self, request: web.Request) -> bool:
        """Проверяет тело запроса на атаки"""
        try:
            # Читаем тело запроса
            body = await request.text()
            
            # Проверяем на XSS и SQL инъекции
            if self._contains_attack_patterns(body):
                return False
            
            return True
            
        except Exception:
            return False
    
    async def _check_url_params(self, request: web.Request) -> bool:
        """Проверяет параметры URL на атаки"""
        # Проверяем query параметры
        for key, value in request.query.items():
            if self._contains_attack_patterns(f"{key}={value}"):
                return False
        
        return True
    
    def _contains_attack_patterns(self, text: str) -> bool:
        """Проверяет текст на наличие паттернов атак"""
        if not text:
            return False
        
        text_lower = text.lower()
        
        for pattern in self.combined_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE | re.DOTALL):
                return True
        
        return False
    
    def _add_security_headers(self, response: web.Response):
        """Добавляет заголовки безопасности"""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:"
        )
    
    def cleanup_expired_data(self):
        """Очищает устаревшие данные"""
        current_time = time.time()
        
        # Очищаем rate limiting данные
        for ip in list(self.rate_limits.keys()):
            while (self.rate_limits[ip] and 
                   current_time - self.rate_limits[ip][0] > 3600):  # 1 час
                self.rate_limits[ip].popleft()
            
            if not self.rate_limits[ip]:
                del self.rate_limits[ip]
        
        # Очищаем заблокированные IP (после 24 часов)
        # В реальном приложении это должно быть в базе данных
        pass


def create_security_middleware():
    """Создает экземпляр middleware безопасности"""
    return SecurityMiddleware()
