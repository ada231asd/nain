"""
Менеджер WebSocket соединений пользователей для отправки уведомлений
"""
from typing import Dict, Optional, Any, List
from aiohttp import web
import asyncio
import json
import logging
from collections import defaultdict, deque


class UserNotificationManager:
    """Менеджер для отправки уведомлений пользователям через WebSocket"""
    
    def __init__(self):
        self.user_connections: Dict[int, web.WebSocketResponse] = {}
        self.pending_notifications: Dict[int, deque] = defaultdict(lambda: deque(maxlen=10))  # Очередь уведомлений для отключенных пользователей
        self.logger = logging.getLogger('user_notifications')
    
    async def register_user(self, user_id: int, ws: web.WebSocketResponse):
        """Регистрирует WebSocket соединение пользователя"""
        if user_id in self.user_connections:
            old_ws = self.user_connections[user_id]
            if not old_ws.closed:
                await old_ws.close()
                self.logger.info(f"Закрыто старое WebSocket соединение для пользователя {user_id}")
        
        self.user_connections[user_id] = ws
        self.logger.info(f"✅ Пользователь {user_id} подключен к WebSocket. Всего подключений: {len(self.user_connections)}")
        
        # Отправляем накопленные уведомления
        await self.send_pending_notifications(user_id)
    
    def unregister_user(self, user_id: int):
        """Удаляет WebSocket соединение пользователя"""
        if user_id in self.user_connections:
            del self.user_connections[user_id]
            self.logger.info(f"❌ Пользователь {user_id} отключен от WebSocket. Осталось подключений: {len(self.user_connections)}")
    
    async def send_notification(self, user_id: int, notification_type: str, data: Dict[str, Any]) -> bool:
        """Отправляет уведомление пользователю"""
        message = {
            'type': notification_type,
            'data': data
        }
        
        if user_id not in self.user_connections:
            self.logger.info(f"Пользователь {user_id} не подключен к WebSocket, добавляем в очередь")
            self.pending_notifications[user_id].append(message)
            return False
        
        ws = self.user_connections[user_id]
        if ws.closed:
            self.logger.warning(f"WebSocket пользователя {user_id} закрыт, добавляем в очередь")
            self.unregister_user(user_id)
            self.pending_notifications[user_id].append(message)
            return False
        
        try:
            await ws.send_json(message)
            self.logger.info(f"Уведомление отправлено пользователю {user_id}: {notification_type}")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка отправки уведомления пользователю {user_id}: {e}, добавляем в очередь")
            self.unregister_user(user_id)
            self.pending_notifications[user_id].append(message)
            return False
    
    async def send_pending_notifications(self, user_id: int):
        """Отправляет накопленные уведомления пользователю"""
        if user_id not in self.pending_notifications or not self.pending_notifications[user_id]:
            return
        
        notifications = list(self.pending_notifications[user_id])
        self.pending_notifications[user_id].clear()
        
        self.logger.info(f"📬 Отправка {len(notifications)} накопленных уведомлений пользователю {user_id}")
        
        if user_id not in self.user_connections:
            # Возвращаем обратно в очередь
            self.pending_notifications[user_id].extend(notifications)
            return
        
        ws = self.user_connections[user_id]
        sent_count = 0
        
        for message in notifications:
            try:
                if not ws.closed:
                    await ws.send_json(message)
                    sent_count += 1
                else:
                    # Возвращаем неотправленные обратно в очередь
                    self.pending_notifications[user_id].append(message)
            except Exception as e:
                self.logger.error(f"Ошибка отправки накопленного уведомления пользователю {user_id}: {e}")
                # Возвращаем неотправленные обратно в очередь
                self.pending_notifications[user_id].append(message)
        
        if sent_count > 0:
            self.logger.info(f"✅ Отправлено {sent_count} накопленных уведомлений пользователю {user_id}")
    
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
    
    def get_pending_notifications_count(self, user_id: int) -> int:
        """Возвращает количество ожидающих уведомлений для пользователя"""
        return len(self.pending_notifications.get(user_id, []))


# Глобальный экземпляр менеджера уведомлений
user_notification_manager = UserNotificationManager()

