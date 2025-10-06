"""
WebSocket сервер для real-time уведомлений
"""
import asyncio
import json
import logging
from typing import Set, Dict, Any
from aiohttp import web
from aiohttp.web import WebSocketResponse
from aiohttp_cors import setup as cors_setup, ResourceOptions

from utils.centralized_logger import get_logger


class WebSocketManager:
    """Менеджер WebSocket соединений"""
    
    def __init__(self):
        self.connections: Set[WebSocketResponse] = set()
        self.logger = get_logger('websocket_manager')
    
    def add_connection(self, ws: WebSocketResponse):
        """Добавляет WebSocket соединение"""
        self.connections.add(ws)
        self.logger.info(f"WebSocket соединение добавлено. Всего соединений: {len(self.connections)}")
    
    def remove_connection(self, ws: WebSocketResponse):
        """Удаляет WebSocket соединение"""
        self.connections.discard(ws)
        self.logger.info(f"WebSocket соединение удалено. Всего соединений: {len(self.connections)}")
    
    async def broadcast(self, message: Dict[str, Any]):
        """Отправляет сообщение всем подключенным клиентам"""
        if not self.connections:
            return
        
        message_str = json.dumps(message, ensure_ascii=False)
        disconnected = set()
        
        for ws in self.connections:
            try:
                await ws.send_str(message_str)
            except ConnectionResetError:
                disconnected.add(ws)
            except Exception as e:
                self.logger.error(f"Ошибка отправки WebSocket сообщения: {e}")
                disconnected.add(ws)
        
        # Удаляем отключенные соединения
        for ws in disconnected:
            self.remove_connection(ws)
    
    async def send_to_connections(self, connections: Set[WebSocketResponse], message: Dict[str, Any]):
        """Отправляет сообщение конкретным соединениям"""
        if not connections:
            return
        
        message_str = json.dumps(message, ensure_ascii=False)
        disconnected = set()
        
        for ws in connections:
            try:
                await ws.send_str(message_str)
            except ConnectionResetError:
                disconnected.add(ws)
            except Exception as e:
                self.logger.error(f"Ошибка отправки WebSocket сообщения: {e}")
                disconnected.add(ws)
        
        # Удаляем отключенные соединения
        for ws in disconnected:
            self.remove_connection(ws)


# Глобальный менеджер WebSocket соединений
websocket_manager = WebSocketManager()


class WebSocketServer:
    """WebSocket сервер"""
    
    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
        self.logger = get_logger('websocket_server')
    
    def create_app(self) -> web.Application:
        """Создает WebSocket приложение"""
        app = web.Application()
        
        # Добавляем CORS middleware
        @web.middleware
        async def cors_middleware(request, handler):
            response = await handler(request)
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            return response
        
        app.middlewares.append(cors_middleware)
        
        # Добавляем маршруты
        app.router.add_get('/ws', self.websocket_handler)
        app.router.add_get('/ws/slot-abnormal-reports', self.slot_abnormal_reports_websocket)
        
        return app
    
    async def websocket_handler(self, request: web.Request) -> WebSocketResponse:
        """Основной WebSocket обработчик"""
        ws = WebSocketResponse()
        await ws.prepare(request)
        
        self.logger.info("Новое WebSocket соединение")
        websocket_manager.add_connection(ws)
        
        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self.handle_websocket_message(ws, data)
                    except json.JSONDecodeError:
                        await ws.send_str(json.dumps({
                            "type": "error",
                            "message": "Неверный JSON формат"
                        }))
                elif msg.type == web.WSMsgType.ERROR:
                    self.logger.error(f"WebSocket ошибка: {ws.exception()}")
        except Exception as e:
            self.logger.error(f"Ошибка в WebSocket соединении: {e}")
        finally:
            websocket_manager.remove_connection(ws)
            self.logger.info("WebSocket соединение закрыто")
        
        return ws
    
    async def slot_abnormal_reports_websocket(self, request: web.Request) -> WebSocketResponse:
        """WebSocket для отчетов об аномалиях слотов"""
        ws = WebSocketResponse()
        await ws.prepare(request)
        
        # Проверяем, не слишком ли много соединений
        if len(websocket_manager.connections) >= 10:  # Максимум 10 соединений
            self.logger.warning("Превышено максимальное количество WebSocket соединений")
            await ws.close()
            return ws
        
        self.logger.info("Новое WebSocket соединение для аномалий слотов")
        websocket_manager.add_connection(ws)
        
        try:
            # Отправляем приветственное сообщение
            await ws.send_str(json.dumps({
                "type": "connected",
                "message": "Подключение к аномалиям слотов установлено"
            }))
            
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self.handle_slot_abnormal_reports_message(ws, data)
                    except json.JSONDecodeError:
                        await ws.send_str(json.dumps({
                            "type": "error",
                            "message": "Неверный JSON формат"
                        }))
                elif msg.type == web.WSMsgType.ERROR:
                    self.logger.error(f"WebSocket ошибка: {ws.exception()}")
        except Exception as e:
            self.logger.error(f"Ошибка в WebSocket соединении для аномалий: {e}")
        finally:
            websocket_manager.remove_connection(ws)
            self.logger.info("WebSocket соединение для аномалий закрыто")
        
        return ws
    
    async def handle_websocket_message(self, ws: WebSocketResponse, data: Dict[str, Any]):
        """Обрабатывает WebSocket сообщения"""
        message_type = data.get("type")
        
        if message_type == "ping":
            await ws.send_str(json.dumps({"type": "pong"}))
        elif message_type == "subscribe":
            # Подписка на определенные события
            subscription = data.get("subscription")
            if subscription == "slot_abnormal_reports":
                await ws.send_str(json.dumps({
                    "type": "subscribed",
                    "subscription": "slot_abnormal_reports"
                }))
        else:
            await ws.send_str(json.dumps({
                "type": "error",
                "message": f"Неизвестный тип сообщения: {message_type}"
            }))
    
    async def handle_slot_abnormal_reports_message(self, ws: WebSocketResponse, data: Dict[str, Any]):
        """Обрабатывает сообщения для аномалий слотов"""
        message_type = data.get("type")
        
        if message_type == "ping":
            await ws.send_str(json.dumps({"type": "pong"}))
        elif message_type == "get_recent":
            # Получить последние аномалии
            limit = data.get("limit", 10)
            await self.send_recent_abnormal_reports(ws, limit)
        else:
            await ws.send_str(json.dumps({
                "type": "error",
                "message": f"Неизвестный тип сообщения: {message_type}"
            }))
    
    async def send_recent_abnormal_reports(self, ws: WebSocketResponse, limit: int = 10):
        """Отправляет последние аномалии слотов"""
        try:
            from api.slot_abnormal_report_api import SlotAbnormalReportAPI
            
            api = SlotAbnormalReportAPI(self.db_pool, self.connection_manager)
            result = await api.get_all_abnormal_reports(limit)
            
            await ws.send_str(json.dumps({
                "type": "recent_abnormal_reports",
                "data": result
            }))
        except Exception as e:
            self.logger.error(f"Ошибка получения последних аномалий: {e}")
            await ws.send_str(json.dumps({
                "type": "error",
                "message": f"Ошибка получения данных: {str(e)}"
            }))
    
    async def broadcast_slot_abnormal_report(self, report_data: Dict[str, Any]):
        """Отправляет новую аномалию слота всем подключенным клиентам"""
        message = {
            "type": "new_slot_abnormal_report",
            "data": report_data,
            "timestamp": report_data.get("created_at")
        }
        
        await websocket_manager.broadcast(message)
        self.logger.info(f"Отправлено уведомление о новой аномалии слота: {report_data.get('report_id')}")


# Функция для отправки уведомлений о новых аномалиях
async def notify_slot_abnormal_report(report_data: Dict[str, Any]):
    """Уведомляет о новой аномалии слота через WebSocket"""
    message = {
        "type": "new_slot_abnormal_report",
        "data": report_data,
        "timestamp": report_data.get("created_at")
    }
    
    await websocket_manager.broadcast(message)
