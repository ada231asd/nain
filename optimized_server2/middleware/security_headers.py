"""
Middleware для добавления заголовков безопасности
"""
from aiohttp import web

@web.middleware
async def security_headers_middleware(request, handler):
    """Добавляет заголовки безопасности к ответам"""
    response = await handler(request)
    
    # Заголовки безопасности
    security_headers = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
        'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
    }
    
    for header, value in security_headers.items():
        response.headers[header] = value
    
    return response
