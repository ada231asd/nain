"""
HTTP сервер с API endpoints
"""
import asyncio
import aiomysql
import os
from aiohttp import web
from aiohttp.web import Application
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
        app = web.Application()
  
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
        
        app.middlewares.append(cors_middleware)
        
        # Создаем обработчики
        self.auth_handler = AuthHandler(self.db_pool)
        self.admin_endpoints = AdminEndpoints(self.db_pool, connection_manager)  
        # Используем общий экземпляр borrow_handler из серверного слоя, если доступен
        shared_borrow_handler = None
        try:
            # server.py создаёт self.borrow_handler; если create_app вызывается оттуда,
            # мы можем получить общий экземпляр из connection_manager-хранилища или передать явно.
            # Здесь пробуем взять из self (если атрибут внедрён извне)
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
        
        # Регистрируем маршруты
        self._setup_routes(app, connection_manager)
        
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
        # app.router.add_post('/api/return-powerbank', self.user_powerbank_api.return_powerbank)  # Удален неправильный алиас
        app.router.add_post('/api/return-damage', self.user_powerbank_api.return_damage_powerbank)  # Возврат с поломкой
        app.router.add_post('/api/return-error', self.user_powerbank_api.return_error_powerbank)  # Возврат с ошибкой
        app.router.add_get('/api/powerbank-error-types', self.user_powerbank_api.get_powerbank_error_types)  # Типы ошибок
        app.router.add_get('/api/user/stations', self.user_powerbank_api.get_stations)
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
