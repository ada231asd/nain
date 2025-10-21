"""
API endpoints для пакетного импорта пользователей из Excel файлов
"""
import aiomysql
import asyncio
import uuid
from aiohttp import web
from aiohttp.web import Request, Response
from typing import Dict, Any
from models.bulk_user_import import BulkUserImport
from utils.json_utils import serialize_for_json
from utils.centralized_logger import get_logger


class BulkUserImportAPI:
    """API для пакетного импорта пользователей"""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
        self.bulk_import = BulkUserImport(db_pool)
    
    
    async def import_users_from_excel(self, request: Request) -> Response:
        """POST /api/users/bulk-import - Импорт пользователей из Excel файла"""
        try:
            logger = get_logger('bulk_user_import_api')
            
            # Проверяем, что запрос содержит файл
            if not request.has_body:
                return web.json_response({
                    "success": False,
                    "error": "Отсутствует файл для импорта"
                }, status=400)
            
            # Получаем multipart данные
            reader = await request.multipart()
            
            file_content = None
            filename = None
            org_unit_id = None
            
            # Обрабатываем поля формы
            while True:
                part = await reader.next()
                if part is None:
                    break
                
                if part.name == 'file':
                    # Читаем файл сразу, пока поток доступен
                    filename = part.filename
                    file_content = await part.read()
                elif part.name == 'org_unit_id':
                    org_unit_id_text = await part.text()
                    if org_unit_id_text:
                        try:
                            org_unit_id = int(org_unit_id_text)
                        except ValueError:
                            return web.json_response({
                                "success": False,
                                "error": "org_unit_id должен быть числом"
                            }, status=400)
            
            if not file_content:
                return web.json_response({
                    "success": False,
                    "error": "Отсутствует файл в запросе"
                }, status=400)
            
            # Проверяем тип файла
            if not filename:
                return web.json_response({
                    "success": False,
                    "error": "Имя файла не указано"
                }, status=400)
            
            # Проверяем расширение файла
            allowed_extensions = ['.xlsx', '.xls']
            if not any(filename.lower().endswith(ext) for ext in allowed_extensions):
                return web.json_response({
                    "success": False,
                    "error": f"Неподдерживаемый формат файла. Разрешены: {', '.join(allowed_extensions)}"
                }, status=400)
            
            if not file_content:
                return web.json_response({
                    "success": False,
                    "error": "Файл пустой"
                }, status=400)
            
            # Проверяем размер файла (максимум 10MB)
            max_file_size = 10 * 1024 * 1024  # 10MB
            if len(file_content) > max_file_size:
                return web.json_response({
                    "success": False,
                    "error": f"Файл слишком большой. Максимальный размер: {max_file_size // (1024*1024)}MB"
                }, status=400)
            
            logger.info(f"Начало импорта пользователей из файла {filename} (размер: {len(file_content)} байт)")
            
            # Засекаем время начала
            import time
            start_time = time.time()
            
            # Выполняем импорт
            result = await self.bulk_import.import_users_from_excel(file_content, org_unit_id)
            
            # Вычисляем затраченное время
            elapsed_time = time.time() - start_time
            
            # Логируем результат
            if result['success']:
                logger.info(f"Импорт успешно завершен за {elapsed_time:.2f} секунд: {result['message']}")
            else:
                logger.warning(f"Импорт завершен с ошибками за {elapsed_time:.2f} секунд: {result['message']}")
            
            return web.json_response(serialize_for_json(result))
            
        except Exception as e:
            logger = get_logger('bulk_user_import_api')
            logger.error(f"Ошибка импорта пользователей: {e}")
            return web.json_response({
                "success": False,
                "error": f"Ошибка импорта: {str(e)}"
            }, status=500)
    
    async def get_import_template(self, request: Request) -> Response:
        """GET /api/users/bulk-import/template - Получить шаблон Excel файла для импорта"""
        try:
            logger = get_logger('bulk_user_import_api')
            
            # Создаем шаблон Excel файла
            import pandas as pd
            import io
            
            # Создаем DataFrame с примером данных
            template_data = {
                'fio': ['Иванов Иван Иванович', 'Петрова Мария Сергеевна'],
                'email': ['ivanov@example.com', 'petrova@example.com'],
                'phone': ['+79012345678', '+79098765432']
            }
            
            df = pd.DataFrame(template_data)
            
            # Создаем Excel файл в памяти
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Пользователи', index=False)
                
                # Получаем workbook для дополнительного форматирования
                workbook = writer.book
                worksheet = writer.sheets['Пользователи']
                
                # Устанавливаем ширину колонок
                worksheet.column_dimensions['A'].width = 30  # fio
                worksheet.column_dimensions['B'].width = 25  # email
                worksheet.column_dimensions['C'].width = 20  # phone
            
            output.seek(0)
            file_content = output.getvalue()
            
            logger.info("Создан шаблон Excel файла для импорта пользователей")
            
            # Возвращаем файл
            response = web.Response(
                body=file_content,
                headers={
                    'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    'Content-Disposition': 'attachment; filename="users_import_template.xlsx"',
                    'Content-Length': str(len(file_content))
                }
            )
            
            return response
            
        except Exception as e:
            logger = get_logger('bulk_user_import_api')
            logger.error(f"Ошибка создания шаблона: {e}")
            return web.json_response({
                "success": False,
                "error": f"Ошибка создания шаблона: {str(e)}"
            }, status=500)
    
    async def validate_excel_file(self, request: Request) -> Response:
        """POST /api/users/bulk-import/validate - Валидация Excel файла без создания пользователей"""
        try:
            logger = get_logger('bulk_user_import_api')
            
            # Проверяем, что запрос содержит файл
            if not request.has_body:
                return web.json_response({
                    "success": False,
                    "error": "Отсутствует файл для валидации"
                }, status=400)
            
            # Получаем multipart данные
            reader = await request.multipart()
            
            file_content = None
            filename = None
            
            # Обрабатываем поля формы
            while True:
                part = await reader.next()
                if part is None:
                    break
                
                if part.name == 'file':
                    # Читаем файл сразу, пока поток доступен
                    filename = part.filename
                    file_content = await part.read()
            
            if not file_content:
                return web.json_response({
                    "success": False,
                    "error": "Отсутствует файл в запросе"
                }, status=400)
            
            # Проверяем тип файла
            if not filename:
                return web.json_response({
                    "success": False,
                    "error": "Имя файла не указано"
                }, status=400)
            
            # Проверяем расширение файла
            allowed_extensions = ['.xlsx', '.xls']
            if not any(filename.lower().endswith(ext) for ext in allowed_extensions):
                return web.json_response({
                    "success": False,
                    "error": f"Неподдерживаемый формат файла. Разрешены: {', '.join(allowed_extensions)}"
                }, status=400)
            
            if not file_content:
                return web.json_response({
                    "success": False,
                    "error": "Файл пустой"
                }, status=400)
            
            logger.info(f"Валидация файла {filename}")
            
            # Парсим файл
            users, parse_errors = await self.bulk_import.parse_excel_file(file_content)
            
            # Проверяем существующих пользователей
            new_users, existing_errors = await self.bulk_import.check_existing_users(users)
            
            # Собираем все ошибки
            all_errors = parse_errors + existing_errors
            
            # Статистика
            statistics = {
                'total_rows': len(users) + len(parse_errors),
                'valid_users': len(users),
                'new_users': len(new_users),
                'existing_users': len(existing_errors),
                'errors': len(all_errors)
            }
            
            success = len(all_errors) == 0
            
            message = f"Валидация завершена. Найдено {len(users)} валидных пользователей"
            if existing_errors:
                message += f", {len(existing_errors)} уже существуют"
            if parse_errors:
                message += f", {len(parse_errors)} с ошибками"
            
            logger.info(f"Валидация завершена: {message}")
            
            return web.json_response(serialize_for_json({
                'success': success,
                'message': message,
                'errors': all_errors,
                'statistics': statistics,
                'preview_users': new_users[:10]  # Показываем первые 10 пользователей для предварительного просмотра
            }))
            
        except Exception as e:
            logger = get_logger('bulk_user_import_api')
            logger.error(f"Ошибка валидации файла: {e}")
            return web.json_response({
                "success": False,
                "error": f"Ошибка валидации: {str(e)}"
            }, status=500)
    
    def setup_routes(self, app):
        """Настраивает маршруты API для пакетного импорта пользователей"""
        
        # Bulk import routes (только REST)
        app.router.add_post('/api/users/bulk-import', self.import_users_from_excel)
        app.router.add_get('/api/users/bulk-import/template', self.get_import_template)
        app.router.add_post('/api/users/bulk-import/validate', self.validate_excel_file)
