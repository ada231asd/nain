"""
HTTP сервер с API endpoints
"""
import asyncio
import aiomysql
import os
from aiohttp import web
from aiohttp.web import Application
from aiohttp.web_exceptions import HTTPRequestEntityTooLarge, HTTPException
from aiohttp_cors import setup as cors_setup, ResourceOptions

from config.settings import DB_CONFIG, HTTP_PORT
from utils.centralized_logger import get_logger
from handlers.auth_handler import AuthHandler
from api.admin_endpoints import AdminEndpoints
from api.borrow_endpoints import BorrowEndpoints
from api.crud_endpoints import CRUDEndpoints
from api.powerbank_crud import PowerbankCRUD
from api.orders_crud import OrdersCRUD
from api.org_unit_crud import OrgUnitCRUD
from api.other_entities_crud import OtherEntitiesCRUD
from api.restart_cabinet_api import RestartCabinetAPI
from api.query_inventory_api import QueryInventoryAPI
from api.query_voice_volume_api import QueryVoiceVolumeAPI
from api.set_voice_volume_api import SetVoiceVolumeAPI
from api.set_server_address_api import SetServerAddressAPI
from api.query_server_address_api import QueryServerAddressAPI
from api.user_powerbank_api import UserPowerbankAPI
from api.powerbank_status_api import PowerbankStatusAPI
from api.bulk_user_import_api import BulkUserImportAPI
from api.logo_upload_api import LogoUploadAPI
from api.return_endpoints import ReturnEndpoints
from api.invitation_api import InvitationAPI
from api.invitation_storage_api import InvitationStorageAPI
from api.soft_delete_api import SoftDeleteAPI
from api.hard_delete_api import HardDeleteAPI
from middleware.auth_middleware import AuthMiddleware
from utils.user_notification_manager import user_notification_manager
import jwt
from config.settings import JWT_SECRET_KEY, JWT_ALGORITHM




class HTTPServer:
 
    
    def __init__(self):
        self.db_pool: aiomysql.Pool = None
        self.app: Application = None
        self.auth_handler: AuthHandler = None
        self.admin_endpoints: AdminEndpoints = None
        self.borrow_endpoints: BorrowEndpoints = None
        self.crud_endpoints: CRUDEndpoints = None
        self.powerbank_crud: PowerbankCRUD = None
        self.orders_crud: OrdersCRUD = None
        self.org_unit_crud: OrgUnitCRUD = None
        self.other_entities_crud: OtherEntitiesCRUD = None
        self.restart_cabinet_api: RestartCabinetAPI = None
        self.query_inventory_api: QueryInventoryAPI = None
        self.query_voice_volume_api: QueryVoiceVolumeAPI = None
        self.set_voice_volume_api: SetVoiceVolumeAPI = None
        self.set_server_address_api: SetServerAddressAPI = None
        self.query_server_address_api: QueryServerAddressAPI = None
        self.user_powerbank_api: UserPowerbankAPI = None
        self.powerbank_status_api: PowerbankStatusAPI = None
        self.bulk_user_import_api: BulkUserImportAPI = None
        self.return_endpoints: ReturnEndpoints = None
        self.invitation_api: InvitationAPI = None
        self.invitation_storage_api: InvitationStorageAPI = None
        self.soft_delete_api: SoftDeleteAPI = None
        self.hard_delete_api: HardDeleteAPI = None
        self.auth_middleware: AuthMiddleware = None
        
    
    async def initialize_database(self):
        
        try:
            self.db_pool = await aiomysql.create_pool(**DB_CONFIG)
            logger = get_logger('http_server')
            logger.info("HTTP сервер: подключение к базе данных установлено")
        except Exception as e:
            logger.error(f"HTTP сервер: ошибка подключения к базе данных: {e}")
            raise
    
    async def cleanup_database(self):
        """Закрывает подключение к базе данных"""
        if self.db_pool:
            self.db_pool.close()
            await self.db_pool.wait_closed()
            logger.info("HTTP сервер: подключение к базе данных закрыто")
    
    def create_app(self, connection_manager=None) -> Application:
        """Создает HTTP приложение"""
        
        client_max_size_bytes = 20 * 1024 * 1024  # 20 MB
        app = web.Application(client_max_size=client_max_size_bytes)
        app['client_max_size_bytes'] = client_max_size_bytes
        
        # Единый JSON-обработчик ошибок, чтобы 413 и другие ошибки не возвращались как HTML
        @web.middleware
        async def error_to_json_middleware(request, handler):
            try:
                return await handler(request)
            except HTTPRequestEntityTooLarge:
                return web.json_response({
                    'success': False,
                    'error': 'Request entity too large',
                    'max_size_bytes': app.get('client_max_size_bytes')
                }, status=413)
            except HTTPException as e:
                return web.json_response({
                    'success': False,
                    'error': e.reason
                }, status=e.status)
            except Exception as e:
                return web.json_response({
                    'success': False,
                    'error': f'Internal server error: {str(e)}'
                }, status=500)
  
        # Добавляем CORS middleware
        @web.middleware
        async def cors_middleware(request, handler):
            # Обрабатываем preflight запросы
            if request.method == 'OPTIONS':
                response = web.Response()
                # Устанавливаем CORS заголовки для preflight
                origin = request.headers.get('Origin', '')
                allowed_origins = os.getenv('CORS_ORIGINS', 'http://localhost,http://localhost:3000,http://localhost:8000').split(',')
                
                if origin in allowed_origins or 'localhost' in origin:
                    response.headers['Access-Control-Allow-Origin'] = origin
                else:
                    response.headers['Access-Control-Allow-Origin'] = 'http://localhost'
                
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
                response.headers['Access-Control-Allow-Credentials'] = 'true'
                response.headers['Access-Control-Max-Age'] = '86400'
                return response
            else:
                response = await handler(request)
            
            # Безопасная CORS конфигурация
            origin = request.headers.get('Origin', '')
            allowed_origins = os.getenv('CORS_ORIGINS', 'http://localhost,http://localhost:3000,http://localhost:8000').split(',')
            
            if origin in allowed_origins:
                response.headers['Access-Control-Allow-Origin'] = origin
            else:
                # Для локальной разработки разрешаем localhost
                if 'localhost' in origin:
                    response.headers['Access-Control-Allow-Origin'] = origin
                else:
                    response.headers['Access-Control-Allow-Origin'] = 'http://localhost'
            
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            
            return response
        
        app.middlewares.append(error_to_json_middleware)
        app.middlewares.append(cors_middleware)
        
        # Добавляем middleware авторизации
        auth_middleware = AuthMiddleware(self.db_pool)
        app.middlewares.append(auth_middleware.create_auth_middleware())
        
        # Создаем обработчики
        self.auth_handler = AuthHandler(self.db_pool)
        self.admin_endpoints = AdminEndpoints(self.db_pool, connection_manager)  
        shared_borrow_handler = None
        try:
            shared_borrow_handler = getattr(self, 'shared_borrow_handler', None)
        except Exception:
            shared_borrow_handler = None

        self.borrow_endpoints = BorrowEndpoints(self.db_pool, connection_manager, borrow_handler=shared_borrow_handler)  
        self.crud_endpoints = CRUDEndpoints(self.db_pool)
        self.powerbank_crud = PowerbankCRUD(self.db_pool)
        self.orders_crud = OrdersCRUD(self.db_pool)
        self.org_unit_crud = OrgUnitCRUD(self.db_pool)
        self.other_entities_crud = OtherEntitiesCRUD(self.db_pool)
        self.restart_cabinet_api = RestartCabinetAPI(self.db_pool, connection_manager)
        self.query_inventory_api = QueryInventoryAPI(self.db_pool, connection_manager)
        self.query_voice_volume_api = QueryVoiceVolumeAPI(self.db_pool, connection_manager)
        self.set_voice_volume_api = SetVoiceVolumeAPI(self.db_pool, connection_manager)
        self.set_server_address_api = SetServerAddressAPI(self.db_pool, connection_manager)
        self.query_server_address_api = QueryServerAddressAPI(self.db_pool, connection_manager)
        self.user_powerbank_api = UserPowerbankAPI(self.db_pool, connection_manager)
        self.powerbank_status_api = PowerbankStatusAPI(self.db_pool)
        self.bulk_user_import_api = BulkUserImportAPI(self.db_pool)
        self.logo_upload_api = LogoUploadAPI(self.db_pool)
        self.return_endpoints = ReturnEndpoints(self.db_pool, connection_manager)
        self.invitation_api = InvitationAPI(self.db_pool)
        self.invitation_storage_api = InvitationStorageAPI(self.db_pool)
        self.soft_delete_api = SoftDeleteAPI(self.db_pool)
        self.hard_delete_api = HardDeleteAPI(self.db_pool)
        self.auth_middleware = AuthMiddleware(self.db_pool)
        
        # Регистрируем маршруты
        self._setup_routes(app, connection_manager)
        
        # Сохраняем notification manager в app для доступа из роутов
        app['user_notification_manager'] = user_notification_manager
        
        return app
    
    def _setup_routes(self, app: Application, connection_manager):
        """Настраивает маршруты API"""
        
        # Авторизация и регистрация
        app.router.add_post('/api/auth/register', self.auth_handler.register_user)
        app.router.add_post('/api/auth/login', self.auth_handler.login_user)
        app.router.add_get('/api/auth/profile', self.auth_handler.get_user_profile)
        app.router.add_put('/api/auth/profile', self.auth_handler.update_user_profile)
        
        # Административные функции
        app.router.add_get('/api/admin/pending-users', self.auth_handler.get_pending_users)
        app.router.add_post('/api/admin/approve-user', self.auth_handler.approve_user)
        app.router.add_post('/api/admin/reject-user', self.auth_handler.reject_user)
        app.router.add_post('/api/admin/reset-email', self.auth_handler.reset_email_service)
        
        # API для приглашений (старое, через БД)
        app.router.add_post('/api/invitations/generate', self.invitation_api.generate_invitation_link)
        app.router.add_get('/api/invitations/{token}', self.invitation_api.get_invitation_info)
        app.router.add_post('/api/invitations/register', self.invitation_api.register_with_invitation)
        app.router.add_get('/api/invitations', self.invitation_api.list_invitations)
        
        # API для хранилища приглашений (новое, без БД)
        app.router.add_post('/api/invitations/storage/store', self.invitation_storage_api.store_invitation)
        app.router.add_get('/api/invitations/storage/{token}', self.invitation_storage_api.get_invitation)
        app.router.add_get('/api/invitations/storage/statistics', self.invitation_storage_api.get_statistics)
        
        # Административные функции для повербанков
        self.admin_endpoints.setup_routes(app)
        
        # API для выдачи повербанков
        self.borrow_endpoints.setup_routes(app)
        
        # API для возврата повербанков с ошибкой
        self.return_endpoints.setup_routes(app)
        
        # CRUD API для всех таблиц
        self.crud_endpoints.setup_routes(app)
        self.powerbank_crud.setup_routes(app)
        self.orders_crud.setup_routes(app)
        self.org_unit_crud.setup_routes(app)
        self.other_entities_crud.setup_routes(app)
        
        # API для команды перезагрузки кабинета
        app.router.add_post('/api/restart-cabinet', self.restart_cabinet_api.restart_cabinet)
        
        # API для запроса инвентаря кабинета
        app.router.add_post('/api/query-inventory', self.query_inventory_api.query_inventory)
        app.router.add_get('/api/query-inventory/station/{station_id}', self.query_inventory_api.get_station_inventory)
        
        # API для запроса уровня громкости голосового вещания
        app.router.add_post('/api/query-voice-volume', self.query_voice_volume_api.query_voice_volume)
        app.router.add_get('/api/query-voice-volume/station/{station_id}', self.query_voice_volume_api.get_voice_volume_data)
        
        # API для установки уровня громкости голосового вещания
        app.router.add_post('/api/set-voice-volume', self.set_voice_volume_api.set_voice_volume)
        
        # API для установки адреса сервера
        app.router.add_post('/api/set-server-address', self.set_server_address_api.set_server_address)
        
        # API для запроса адреса сервера
        app.router.add_post('/api/query-server-address', self.query_server_address_api.query_server_address)
        app.router.add_get('/api/query-server-address/station/{station_id}', self.query_server_address_api.get_server_address_data)
        
        # API для пользователей
        app.router.add_get('/api/user/powerbanks/available', self.user_powerbank_api.get_available_powerbanks)
        
        # SSE API
        app.router.add_get('/api/user/orders', self.user_powerbank_api.get_user_orders)
        app.router.add_post('/api/user/powerbanks/borrow', self.user_powerbank_api.borrow_powerbank)
        app.router.add_post('/api/user/powerbanks/return', self.user_powerbank_api.return_powerbank)
        app.router.add_post('/api/return-damage', self.user_powerbank_api.return_damage_powerbank) 
        app.router.add_post('/api/return-error', self.user_powerbank_api.return_error_powerbank) 
        app.router.add_get('/api/powerbank-error-types', self.user_powerbank_api.get_powerbank_error_types) 
        app.router.add_get('/api/user/stations', self.user_powerbank_api.get_stations)
        app.router.add_get('/api/user/stations/availability', self.user_powerbank_api.get_available_slots_with_limits)
        app.router.add_get('/api/user/profile', self.user_powerbank_api.get_user_profile)
        
        
        # API для статусов повербанков
        self.powerbank_status_api.setup_routes(app)
        
        # API для пакетного импорта пользователей
        self.bulk_user_import_api.setup_routes(app)
        
        # API для загрузки логотипов
        self.logo_upload_api.setup_routes(app)
        
        # API для отчетов об аномалиях слотов
        from api.slot_abnormal_report_endpoints import SlotAbnormalReportEndpoints
        self.slot_abnormal_report_endpoints = SlotAbnormalReportEndpoints(self.db_pool, connection_manager)
        self.slot_abnormal_report_endpoints.setup_routes(app)
        
        # API для мягкого и жесткого удаления
        # Мягкое удаление (soft delete)
        app.router.add_delete('/api/soft-delete/{entity_type}/{entity_id}', self.soft_delete_api.soft_delete_entity)
        app.router.add_post('/api/soft-delete/restore/{entity_type}/{entity_id}', self.soft_delete_api.restore_entity)
        app.router.add_get('/api/soft-delete/{entity_type}', self.soft_delete_api.get_deleted_entities)
        app.router.add_get('/api/soft-delete/statistics', self.soft_delete_api.get_statistics)
        
        # Жесткое удаление (hard delete) - только для service_admin
        app.router.add_delete('/api/hard-delete/{entity_type}/{entity_id}', self.hard_delete_api.hard_delete_entity)
        app.router.add_delete('/api/hard-delete/cleanup', self.hard_delete_api.cleanup_old_deleted)
        app.router.add_get('/api/hard-delete/cleanup/preview', self.hard_delete_api.get_cleanup_candidates)
        
        # Настройка раздачи статических файлов (логотипов)
        # Путь к папке с логотипами (tcp_server/uploads/logos)
        uploads_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads", "logos")
        os.makedirs(uploads_path, exist_ok=True)
        app.router.add_static('/logos/', uploads_path, show_index=False)
        
        # WebSocket для уведомлений пользователей
        app.router.add_get('/api/ws/notifications', self.handle_user_notifications_ws)
        
    
    async def handle_user_notifications_ws(self, request: web.Request):
        """Обработчик WebSocket для уведомлений пользователей"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        user_id = None
        logger = get_logger('websocket')
        
        logger.info("🔌 Новое WebSocket подключение")
        
        try:
            # Получаем токен из query параметров
            token = request.query.get('token')
            if not token:
                logger.warning("❌ WebSocket: токен не предоставлен")
                await ws.send_json({'error': 'Missing token'})
                await ws.close()
                return ws
            
            # Проверяем токен
            try:
                payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
                user_id = payload.get('user_id')
                logger.info(f"🔑 WebSocket: токен расшифрован, user_id={user_id}")
                
                if not user_id:
                    logger.warning("❌ WebSocket: user_id не найден в токене")
                    await ws.send_json({'error': 'Invalid token'})
                    await ws.close()
                    return ws
            except jwt.ExpiredSignatureError:
                logger.warning("❌ WebSocket: токен истёк")
                await ws.send_json({'error': 'Token expired'})
                await ws.close()
                return ws
            except jwt.InvalidTokenError as e:
                logger.warning(f"❌ WebSocket: неверный токен - {e}")
                await ws.send_json({'error': 'Invalid token'})
                await ws.close()
                return ws
            
            # Регистрируем пользователя
            logger.info(f"📝 Регистрируем пользователя {user_id} в WebSocket менеджере")
            await user_notification_manager.register_user(user_id, ws)
            await ws.send_json({
                'type': 'connected',
                'message': 'WebSocket connected successfully'
            })
            
            logger.info(f"✅ WebSocket: пользователь {user_id} успешно подключен и слушает сообщения")
            
            # Слушаем сообщения от клиента
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    if msg.data == 'ping':
                        await ws.send_json({'type': 'pong'})
                        logger.debug(f"🏓 Ping/Pong от пользователя {user_id}")
                elif msg.type == web.WSMsgType.ERROR:
                    logger.error(f'❌ WebSocket error for user {user_id}: {ws.exception()}')
        
        except Exception as e:
            logger.error(f'❌ WebSocket критическая ошибка для пользователя {user_id}: {e}', exc_info=True)
        finally:
            if user_id:
                logger.info(f"🔚 Закрываем WebSocket для пользователя {user_id}")
                user_notification_manager.unregister_user(user_id)
        
        return ws
    
    async def start_server(self):
        """Запускает HTTP сервер"""
        try:
            # Инициализируем базу данных
            await self.initialize_database()
            
            # Создаем приложение
            self.app = self.create_app()
            
            # Запускаем сервер
            runner = web.AppRunner(self.app)
            await runner.setup()
            
            site = web.TCPSite(runner, '0.0.0.0', HTTP_PORT)
            await site.start()
            
            logger.info(f"HTTP сервер запущен на порту {HTTP_PORT}")
            logger.info("Доступные endpoints зарегистрированы")
            
            # Ждем завершения
            await asyncio.Future()  # Бесконечное ожидание
            
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
        finally:
            await self.cleanup_database()
    
    def stop_server(self):
        """Останавливает HTTP сервер"""
        logger = get_logger('http_server')
        logger.info("Остановка HTTP сервера...")
        if self.app:
            pass


async def main():
    """Основная функция HTTP сервера"""
    server = HTTPServer()
    
    try:
        await server.start_server()
    except KeyboardInterrupt:
        logger.info("HTTP сервер остановлен")
    except Exception as e:
        logger.error(f"Критическая ошибка HTTP сервера: {e}")


if __name__ == "__main__":
    logger = get_logger('http_server')
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("HTTP сервер остановлен")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
