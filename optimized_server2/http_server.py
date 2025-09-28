"""
HTTP сервер с API endpoints
"""
import asyncio
import aiomysql
from aiohttp import web
from aiohttp.web import Application
from aiohttp_cors import setup as cors_setup, ResourceOptions

from config.settings import DB_CONFIG, HTTP_PORT
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
from api.powerbank_error_endpoints import PowerbankErrorEndpoints
from api.simple_return_endpoints import SimpleReturnEndpoints




class HTTPServer:
    """HTTP сервер с API"""
    
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
        self.powerbank_error_endpoints: PowerbankErrorEndpoints = None
        self.simple_return_endpoints: SimpleReturnEndpoints = None
        
    
    async def initialize_database(self):
        """Инициализирует подключение к базе данных"""
        try:
            self.db_pool = await aiomysql.create_pool(**DB_CONFIG)
            print("HTTP сервер: подключение к базе данных установлено")
        except Exception as e:
            print(f"HTTP сервер: ошибка подключения к базе данных: {e}")
            raise
    
    async def cleanup_database(self):
        """Закрывает подключение к базе данных"""
        if self.db_pool:
            self.db_pool.close()
            await self.db_pool.wait_closed()
            print("HTTP сервер: подключение к базе данных закрыто")
    
    def create_app(self, connection_manager=None) -> Application:
        """Создает HTTP приложение"""
        app = web.Application()
  
        # Добавляем CORS middleware
        @web.middleware
        async def cors_middleware(request, handler):
            # Обрабатываем preflight запросы
            if request.method == 'OPTIONS':
                response = web.Response()
            else:
                response = await handler(request)
            
            # Безопасная CORS конфигурация
            origin = request.headers.get('Origin', '')
            allowed_origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
            
            if origin in allowed_origins:
                response.headers['Access-Control-Allow-Origin'] = origin
            else:
                response.headers['Access-Control-Allow-Origin'] = 'null'
            
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            
            return response
        
        app.middlewares.append(cors_middleware)
        
        # Создаем обработчики
        self.auth_handler = AuthHandler(self.db_pool)
        self.admin_endpoints = AdminEndpoints(self.db_pool, connection_manager)  # Передаем connection_manager
        self.borrow_endpoints = BorrowEndpoints(self.db_pool, connection_manager)  # Передаем connection_manager
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
        self.powerbank_error_endpoints = PowerbankErrorEndpoints(self.db_pool)
        self.simple_return_endpoints = SimpleReturnEndpoints(self.db_pool, connection_manager)
        
        # Регистрируем маршруты
        self._setup_routes(app)
        
        return app
    
    def _setup_routes(self, app: Application):
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
        
        # Административные функции для повербанков
        self.admin_endpoints.setup_routes(app)
        
        # API для выдачи повербанков
        self.borrow_endpoints.setup_routes(app)
        
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
        app.router.add_get('/api/user/stations', self.user_powerbank_api.get_stations)
        app.router.add_get('/api/user/profile', self.user_powerbank_api.get_user_profile)
        
        # Новые API для возврата повербанков
        self.powerbank_error_endpoints.setup_routes(app)
        self.simple_return_endpoints.setup_routes(app)
        
        
    
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
            
            print(f"HTTP сервер запущен на порту {HTTP_PORT}")
            print("Доступные endpoints:")
            print("\n=== АВТОРИЗАЦИЯ ===")
            print("  POST /api/auth/register - Регистрация пользователя (статус pending)")
            print("  POST /api/auth/login - Авторизация по паролю (только для active)")
            print("  GET /api/auth/profile - Получение профиля пользователя")
            print("  PUT /api/auth/profile - Обновление профиля пользователя")
            print("\n=== АДМИНИСТРИРОВАНИЕ ===")
            print("  GET /api/admin/pending-users - Список пользователей на подтверждение (admin)")
            print("  POST /api/admin/approve-user - Подтвердить пользователя (admin)")
            print("  POST /api/admin/reject-user - Отклонить пользователя (admin)")
            print("  POST /api/admin/force-eject-powerbank - Принудительное извлечение повербанка (admin)")
            print("\n=== ВЫДАЧА ПОВЕРБАНКОВ ===")
            print("  GET /api/borrow/stations/{station_id}/powerbanks - Список доступных повербанков")
            print("  GET /api/borrow/stations/{station_id}/slots/{slot_number}/status - Статус слота")
            print("  POST /api/borrow/stations/{station_id}/request - Запрос на выдачу повербанка")
            print("  GET /api/borrow/stations/{station_id}/info - Информация о станции")
            print("  GET /api/borrow/stations/{station_id}/select-optimal - Выбор оптимального повербанка")
            print("  POST /api/borrow/stations/{station_id}/request-optimal - Запрос оптимальной выдачи")
            print("\n=== CRUD API - ПОЛЬЗОВАТЕЛИ ===")
            print("  POST /api/users - Создать пользователя")
            print("  GET /api/users - Получить список пользователей")
            print("  GET /api/users/{user_id} - Получить пользователя по ID")
            print("  PUT /api/users/{user_id} - Обновить пользователя")
            print("  DELETE /api/users/{user_id} - Удалить пользователя")
            print("\n=== CRUD API - СТАНЦИИ ===")
            print("  POST /api/stations - Создать станцию")
            print("  GET /api/stations - Получить список станций")
            print("  GET /api/stations/{station_id} - Получить станцию по ID")
            print("  PUT /api/stations/{station_id} - Обновить станцию")
            print("  DELETE /api/stations/{station_id} - Удалить станцию")
            print("\n=== CRUD API - ПОВЕРБАНКИ ===")
            print("  POST /api/powerbanks - Создать powerbank")
            print("  GET /api/powerbanks - Получить список powerbanks")
            print("  GET /api/powerbanks/{powerbank_id} - Получить powerbank по ID")
            print("  PUT /api/powerbanks/{powerbank_id} - Обновить powerbank")
            print("  DELETE /api/powerbanks/{powerbank_id} - Удалить powerbank")
            print("\n=== CRUD API - ЗАКАЗЫ ===")
            print("  POST /api/orders - Создать заказ")
            print("  GET /api/orders - Получить список заказов")
            print("  GET /api/orders/{order_id} - Получить заказ по ID")
            print("  PUT /api/orders/{order_id} - Обновить заказ")
            print("  DELETE /api/orders/{order_id} - Удалить заказ")
            print("\n=== CRUD API - ОРГАНИЗАЦИОННЫЕ ЕДИНИЦЫ ===")
            print("  POST /api/org-units - Создать организационную единицу")
            print("  GET /api/org-units - Получить список организационных единиц")
            print("  GET /api/org-units/{org_unit_id} - Получить организационную единицу по ID")
            print("  PUT /api/org-units/{org_unit_id} - Обновить организационную единицу")
            print("  DELETE /api/org-units/{org_unit_id} - Удалить организационную единицу")
            print("\n=== CRUD API - РОЛИ ПОЛЬЗОВАТЕЛЕЙ ===")
            print("  POST /api/user-roles - Создать роль пользователя")
            print("  GET /api/user-roles - Получить список ролей пользователей")
            print("  DELETE /api/user-roles/{role_id} - Удалить роль пользователя")
            print("\n=== CRUD API - ИЗБРАННЫЕ СТАНЦИИ ===")
            print("  POST /api/user-favorites - Добавить станцию в избранное")
            print("  GET /api/user-favorites - Получить избранные станции пользователя")
            print("  DELETE /api/user-favorites/{favorite_id} - Удалить из избранного")
            print("\n=== CRUD API - СВЯЗИ СТАНЦИЯ-ПОВЕРБАНК ===")
            print("  POST /api/station-powerbanks - Создать связь станция-powerbank")
            print("  GET /api/station-powerbanks - Получить связи станция-powerbank")
            print("  DELETE /api/station-powerbanks/{sp_id} - Удалить связь")
            print("\n=== CRUD API - СЕКРЕТНЫЕ КЛЮЧИ СТАНЦИЙ ===")
            print("  POST /api/station-secret-keys - Создать секретный ключ станции")
            print("  GET /api/station-secret-keys - Получить секретные ключи станций")
            print("  DELETE /api/station-secret-keys/{key_id} - Удалить секретный ключ")
            print("  DELETE /api/station-secret-keys - Удалить секретный ключ по station_id")
            print("\n=== ИНВЕНТАРЬ СТАНЦИЙ (0x64) ===")
            print("  GET /api/inventory/stations/{station_id} - Получить инвентарь станции")
            print("  POST /api/inventory/stations/{station_id}/query - Запросить инвентарь через TCP")
            print("  GET /api/inventory/stations/{station_id}/slots/{slot_number} - Детали слота")
            print("  GET /api/inventory/summary - Сводка по инвентарю")
            print("\n=== УДАЛЕННАЯ ПЕРЕЗАГРУЗКА СТАНЦИЙ (0x67) ===")
            print("  POST /api/restart/stations/{station_id} - Перезагрузить станцию")
            print("  POST /api/restart/stations/bulk - Массовая перезагрузка станций")
            print("\n=== ЗАПРОС АДРЕСА СЕРВЕРА (0x6A) ===")
            print("  POST /api/server-address/stations/{station_id}/query - Запросить адрес сервера")
            print("  GET /api/server-address/stations/{station_id} - Получить адрес сервера")
            print("\n=== УСТАНОВКА АДРЕСА СЕРВЕРА (0x63) ===")
            print("  POST /api/set-server-address/stations/{station_id}/set - Установить адрес сервера")
            print("  GET /api/set-server-address/stations/{station_id} - Получить результат установки")
            print("\n=== УПРАВЛЕНИЕ ГРОМКОСТЬЮ ГОЛОСОВОГО ВЕЩАНИЯ (0x77, 0x70) ===")
            print("  POST /api/voice-volume/stations/{station_id}/query - Запросить уровень громкости")
            print("  POST /api/voice-volume/stations/{station_id}/set - Установить уровень громкости")
            print("  GET /api/voice-volume/stations/{station_id} - Получить уровень громкости")
            print("  GET /api/voice-volume/stations/{station_id}/setting - Получить результат установки")
            
            # Ждем завершения
            await asyncio.Future()  # Бесконечное ожидание
            
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
        finally:
            await self.cleanup_database()
    
    def stop_server(self):
        """Останавливает HTTP сервер"""
        print("Остановка HTTP сервера...")
        if self.app:
            pass


async def main():
    """Основная функция HTTP сервера"""
    server = HTTPServer()
    
    try:
        await server.start_server()
    except KeyboardInterrupt:
        print("HTTP сервер остановлен")
    except Exception as e:
        print(f"Критическая ошибка HTTP сервера: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("HTTP сервер остановлен")
    except Exception as e:
        print(f"Критическая ошибка: {e}")
