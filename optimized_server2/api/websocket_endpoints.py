"""
WebSocket endpoints для real-time уведомлений
"""
import json
import asyncio
from typing import Set, Dict, Any
from aiohttp import web, WSMsgType
from aiohttp.web import WebSocketResponse


class WebSocketManager:
    """Менеджер WebSocket соединений"""
    
    def __init__(self):
        self.connections: Set[WebSocketResponse] = set()
        self.station_subscribers: Dict[int, Set[WebSocketResponse]] = {}  # station_id -> connections
    
    def add_connection(self, ws: WebSocketResponse):
        """Добавляет новое WebSocket соединение"""
        self.connections.add(ws)
    
    def remove_connection(self, ws: WebSocketResponse):
        """Удаляет WebSocket соединение"""
        self.connections.discard(ws)
        # Удаляем из всех подписок на станции
        for station_connections in self.station_subscribers.values():
            station_connections.discard(ws)
    
    def subscribe_to_station(self, ws: WebSocketResponse, station_id: int):
        """Подписывает соединение на уведомления о станции"""
        if station_id not in self.station_subscribers:
            self.station_subscribers[station_id] = set()
        self.station_subscribers[station_id].add(ws)
    
    def unsubscribe_from_station(self, ws: WebSocketResponse, station_id: int):
        """Отписывает соединение от уведомлений о станции"""
        if station_id in self.station_subscribers:
            self.station_subscribers[station_id].discard(ws)
    
    async def broadcast_to_all(self, message: Dict[str, Any]):
        """Отправляет сообщение всем подключенным клиентам"""
        if not self.connections:
            return
        
        message_json = json.dumps(message, ensure_ascii=False)
        disconnected = set()
        
        for ws in self.connections:
            try:
                await ws.send_str(message_json)
            except ConnectionResetError:
                disconnected.add(ws)
            except Exception as e:
                print(f"Ошибка отправки WebSocket сообщения: {e}")
                disconnected.add(ws)
        
        # Удаляем отключенные соединения
        for ws in disconnected:
            self.remove_connection(ws)
    
    async def broadcast_to_station_subscribers(self, station_id: int, message: Dict[str, Any]):
        """Отправляет сообщение подписчикам конкретной станции"""
        if station_id not in self.station_subscribers:
            return
        
        message_json = json.dumps(message, ensure_ascii=False)
        disconnected = set()
        
        for ws in self.station_subscribers[station_id]:
            try:
                await ws.send_str(message_json)
            except ConnectionResetError:
                disconnected.add(ws)
            except Exception as e:
                print(f"Ошибка отправки WebSocket сообщения: {e}")
                disconnected.add(ws)
        
        # Удаляем отключенные соединения
        for ws in disconnected:
            self.remove_connection(ws)


# Глобальный экземпляр менеджера WebSocket
ws_manager = WebSocketManager()


class WebSocketEndpoints:
    """WebSocket endpoints для real-time уведомлений"""
    
    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
    
    def setup_routes(self, app):
        """Настраивает WebSocket маршруты"""
        app.router.add_get('/ws/notifications', self.websocket_handler)
        app.router.add_get('/ws/station/{station_id}', self.station_websocket_handler)
    
    async def websocket_handler(self, request):
        """Обработчик основного WebSocket соединения для общих уведомлений"""
        ws = WebSocketResponse()
        await ws.prepare(request)
        
        ws_manager.add_connection(ws)
        print(f"WebSocket подключен: {request.remote}")
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self.handle_websocket_message(ws, data)
                    except json.JSONDecodeError:
                        await ws.send_str(json.dumps({"error": "Неверный JSON"}))
                elif msg.type == WSMsgType.ERROR:
                    print(f"WebSocket ошибка: {ws.exception()}")
                    break
        except Exception as e:
            print(f"WebSocket ошибка: {e}")
        finally:
            ws_manager.remove_connection(ws)
            print(f"WebSocket отключен: {request.remote}")
        
        return ws
    
    async def station_websocket_handler(self, request):
        """Обработчик WebSocket соединения для конкретной станции"""
        station_id = int(request.match_info['station_id'])
        ws = WebSocketResponse()
        await ws.prepare(request)
        
        ws_manager.add_connection(ws)
        ws_manager.subscribe_to_station(ws, station_id)
        print(f"WebSocket подключен к станции {station_id}: {request.remote}")
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self.handle_websocket_message(ws, data)
                    except json.JSONDecodeError:
                        await ws.send_str(json.dumps({"error": "Неверный JSON"}))
                elif msg.type == WSMsgType.ERROR:
                    print(f"WebSocket ошибка: {ws.exception()}")
                    break
        except Exception as e:
            print(f"WebSocket ошибка: {e}")
        finally:
            ws_manager.remove_connection(ws)
            print(f"WebSocket отключен от станции {station_id}: {request.remote}")
        
        return ws
    
    async def handle_websocket_message(self, ws: WebSocketResponse, data: Dict[str, Any]):
        """Обрабатывает входящие WebSocket сообщения"""
        message_type = data.get('type')
        
        if message_type == 'ping':
            await ws.send_str(json.dumps({"type": "pong"}))
        elif message_type == 'subscribe_station':
            station_id = data.get('station_id')
            if station_id:
                ws_manager.subscribe_to_station(ws, station_id)
                await ws.send_str(json.dumps({
                    "type": "subscribed",
                    "station_id": station_id
                }))
        elif message_type == 'unsubscribe_station':
            station_id = data.get('station_id')
            if station_id:
                ws_manager.unsubscribe_from_station(ws, station_id)
                await ws.send_str(json.dumps({
                    "type": "unsubscribed",
                    "station_id": station_id
                }))
        else:
            await ws.send_str(json.dumps({"error": "Неизвестный тип сообщения"}))


async def notify_station_status_change(station_id: int, old_status: str, new_status: str, station_info: Dict[str, Any]):
    """Уведомляет о изменении статуса станции"""
    message = {
        "type": "station_status_change",
        "station_id": station_id,
        "old_status": old_status,
        "new_status": new_status,
        "station_info": station_info,
        "timestamp": asyncio.get_event_loop().time()
    }
    
    # Отправляем всем подписчикам станции
    await ws_manager.broadcast_to_station_subscribers(station_id, message)
    
    # Отправляем общее уведомление всем подключенным
    await ws_manager.broadcast_to_all(message)


async def notify_station_online(station_id: int, station_info: Dict[str, Any]):
    """Уведомляет о том, что станция стала онлайн"""
    message = {
        "type": "station_online",
        "station_id": station_id,
        "station_info": station_info,
        "timestamp": asyncio.get_event_loop().time()
    }
    
    await ws_manager.broadcast_to_station_subscribers(station_id, message)
    await ws_manager.broadcast_to_all(message)


async def notify_station_offline(station_id: int, station_info: Dict[str, Any]):
    """Уведомляет о том, что станция стала офлайн"""
    message = {
        "type": "station_offline",
        "station_id": station_id,
        "station_info": station_info,
        "timestamp": asyncio.get_event_loop().time()
    }
    
    await ws_manager.broadcast_to_station_subscribers(station_id, message)
    await ws_manager.broadcast_to_all(message)

async def notify_station_inactive(station_id: int, station_info: Dict[str, Any]):
    """Уведомляет о том, что станция стала неактивной (офлайн)"""
    message = {
        "type": "station_offline",  # Используем тот же тип для совместимости
        "station_id": station_id,
        "station_info": station_info,
        "timestamp": asyncio.get_event_loop().time()
    }
    
    await ws_manager.broadcast_to_station_subscribers(station_id, message)
    await ws_manager.broadcast_to_all(message)


async def notify_powerbank_status_change(station_id: int, powerbank_id: int, old_status: str, new_status: str):
    """Уведомляет об изменении статуса повербанка"""
    message = {
        "type": "powerbank_status_change",
        "station_id": station_id,
        "powerbank_id": powerbank_id,
        "old_status": old_status,
        "new_status": new_status,
        "timestamp": asyncio.get_event_loop().time()
    }
    
    await ws_manager.broadcast_to_station_subscribers(station_id, message)
    await ws_manager.broadcast_to_all(message)
