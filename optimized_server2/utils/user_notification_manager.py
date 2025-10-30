"""
Менеджер WebSocket соединений пользователей для отправки уведомлений
"""
from typing import Dict, Optional, Any
from aiohttp import web
import asyncio
import json
import logging


class UserNotificationManager:
    """Менеджер для отправки уведомлений пользователям через WebSocket"""
    
    def __init__(self):
        self.user_connections: Dict[int, web.WebSocketResponse] = {}
        self.logger = logging.getLogger('user_notifications')
    
    async def register_user(self, user_id: int, ws: web.WebSocketResponse):
        """Регистрирует WebSocket соединение пользователя"""
        if user_id in self.user_connections:
            old_ws = self.user_connections[user_id]
            if not old_ws.closed:
                await old_ws.close()
        
        self.user_connections[user_id] = ws
        self.logger.info(f"Пользователь {user_id} подключен к WebSocket")
    
    def unregister_user(self, user_id: int):
        """Удаляет WebSocket соединение пользователя"""
        if user_id in self.user_connections:
            del self.user_connections[user_id]
            self.logger.info(f"Пользователь {user_id} отключен от WebSocket")
    
    async def send_notification(self, user_id: int, notification_type: str, data: Dict[str, Any]) -> bool:
        """Отправляет уведомление пользователю"""
        if user_id not in self.user_connections:
            self.logger.debug(f"Пользователь {user_id} не подключен к WebSocket")
            return False
        
        ws = self.user_connections[user_id]
        if ws.closed:
            self.logger.warning(f"WebSocket пользователя {user_id} закрыт")
            self.unregister_user(user_id)
            return False
        
        try:
            message = {
                'type': notification_type,
                'data': data
            }
            await ws.send_json(message)
            self.logger.info(f"Уведомление отправлено пользователю {user_id}: {notification_type}")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка отправки уведомления пользователю {user_id}: {e}")
            self.unregister_user(user_id)
            return False
    
    async def send_powerbank_return_notification(self, user_id: int, order_id: int, 
                                                 powerbank_serial: str, message: str) -> bool:
        """Отправляет уведомление о возврате powerbank"""
        return await self.send_notification(
            user_id=user_id,
            notification_type='powerbank_returned',
            data={
                'order_id': order_id,
                'powerbank_serial': powerbank_serial,
                'message': message,
                'title': 'Спасибо за возврат!',
                'alert': 'Спасибо за возврат! Заказ успешно закрыт.'
            }
        )
    
    def get_active_users_count(self) -> int:
        """Возвращает количество активных подключений"""
        return len(self.user_connections)


# Глобальный экземпляр менеджера уведомлений
user_notification_manager = UserNotificationManager()

