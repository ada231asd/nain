"""
API для загрузки логотипов организационных единиц
"""
import os
import uuid
import aiofiles
from aiohttp import web
from aiohttp.web import Request, Response
from utils.centralized_logger import get_logger
from utils.auth_middleware import require_auth


class LogoUploadAPI:
    """API для загрузки логотипов"""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
        self.logger = get_logger('logo_upload_api')
        
        # Настройки загрузки
        self.upload_dir = "uploads/logos"
        # Разрешаем до 15MB на файл (совместимо с глобальным лимитом 20MB)
        self.max_file_size = 15 * 1024 * 1024
        self.allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        
        # Создаем папку для загрузок если её нет
        os.makedirs(self.upload_dir, exist_ok=True)
    
    def setup_routes(self, app):
        """Настраивает маршруты для загрузки логотипов"""
        app.router.add_post('/api/org-units/{org_unit_id}/logo', self.upload_logo)
        app.router.add_delete('/api/org-units/{org_unit_id}/logo', self.delete_logo)
        app.router.add_get('/api/logos/{filename}', self.serve_logo)
    
    async def upload_logo(self, request: Request) -> Response:
        """POST /api/org-units/{org_unit_id}/logo - Загрузка логотипа"""
        try:
            # Проверяем авторизацию
            auth_result = await require_auth(request)
            if not auth_result['success']:
                return web.json_response({
                    "success": False,
                    "error": auth_result['error']
                }, status=401)
            
            org_unit_id = int(request.match_info['org_unit_id'])
            # Логируем попытку загрузки
            try:
                self.logger.info(f"Запрос загрузки логотипа: org_unit_id={org_unit_id}, user_id={auth_result.get('user', {}).get('user_id')}")
            except Exception:
                pass
            
            # Проверяем существование организационной единицы
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT org_unit_id FROM org_unit 
                        WHERE org_unit_id = %s
                    """, (org_unit_id,))
                    
                    if not await cur.fetchone():
                        return web.json_response({
                            "success": False,
                            "error": "Организационная единица не найдена"
                        }, status=404)
            
            # Проверяем права доступа к организационной единице
            user = auth_result['user']
            if not await self._check_org_unit_access(user, org_unit_id):
                return web.json_response({
                    "success": False,
                    "error": "Нет прав доступа к данной организационной единице"
                }, status=403)
            
            # Проверяем, что запрос содержит файл
            if not request.has_body:
                return web.json_response({
                    "success": False,
                    "error": "Отсутствует файл для загрузки"
                }, status=400)
            
            content_type = request.headers.get('Content-Type', '')
            file_content = None
            filename = None

            if 'multipart/form-data' in content_type:
                # Получаем multipart данные
                reader = await request.multipart()
                # Обрабатываем поля формы
                async for part in reader:
                    if part.name == 'logo':
                        # Читаем файл
                        filename = part.filename
                        file_content = await part.read()
                        break
            else:
                # Фолбэк: принимаем сырое тело как файл (например, если фронт не выставил multipart)
                try:
                    file_content = await request.read()
                    filename = f"{org_unit_id}_{uuid.uuid4().hex}.bin"
                except Exception as e:
                    self.logger.error(f"Не удалось прочитать тело запроса: {e}")
            
            if not file_content:
                return web.json_response({
                    "success": False,
                    "error": "Отсутствует файл логотипа в запросе"
                }, status=400)
            
            # Проверяем размер файла
            if len(file_content) > self.max_file_size:
                return web.json_response({
                    "success": False,
                    "error": f"Размер файла превышает {self.max_file_size // (1024*1024)}MB"
                }, status=400)
            
            # Проверяем расширение файла
            if filename:
                file_ext = os.path.splitext(filename)[1].lower()
                # Если пришел файл без расширения (фолбэк путь), пробуем по content-type
                if not file_ext:
                    ct = request.headers.get('Content-Type', '')
                    if 'image/jpeg' in ct:
                        file_ext = '.jpg'
                    elif 'image/png' in ct:
                        file_ext = '.png'
                    elif 'image/webp' in ct:
                        file_ext = '.webp'
                    elif 'image/gif' in ct:
                        file_ext = '.gif'
                    else:
                        file_ext = '.jpg'
                if file_ext not in self.allowed_extensions:
                    return web.json_response({
                        "success": False,
                        "error": f"Недопустимое расширение файла. Разрешены: {', '.join(self.allowed_extensions)}"
                    }, status=400)
            
            # Генерируем уникальное имя файла
            file_ext = os.path.splitext(filename)[1].lower() if filename else '.jpg'
            unique_filename = f"{org_unit_id}_{uuid.uuid4().hex}{file_ext}"
            file_path = os.path.join(self.upload_dir, unique_filename)
            
            # Сохраняем файл
            try:
                async with aiofiles.open(file_path, 'wb') as f:
                    await f.write(file_content)
                self.logger.info(f"Файл сохранен: {file_path}")
            except Exception as e:
                self.logger.error(f"Ошибка сохранения файла {file_path}: {e}")
                return web.json_response({
                    "success": False,
                    "error": "Ошибка сохранения файла"
                }, status=500)
            
            # Обновляем путь к логотипу в базе данных
            logo_url = f"/api/logos/{unique_filename}"
            
            try:
                async with self.db_pool.acquire() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute("""
                            UPDATE org_unit 
                            SET logo_url = %s 
                            WHERE org_unit_id = %s
                        """, (logo_url, org_unit_id))
                        
                        if cur.rowcount == 0:
                            # Удаляем загруженный файл если обновление не удалось
                            if os.path.exists(file_path):
                                os.remove(file_path)
                            return web.json_response({
                                "success": False,
                                "error": "Организационная единица не найдена"
                            }, status=404)
            except Exception as e:
                # Удаляем загруженный файл при ошибке БД
                if os.path.exists(file_path):
                    os.remove(file_path)
                self.logger.error(f"Ошибка обновления БД для org_unit_id={org_unit_id}: {e}")
                return web.json_response({
                    "success": False,
                    "error": "Ошибка сохранения данных"
                }, status=500)
            
            self.logger.info(f"Логотип загружен для org_unit_id={org_unit_id}, файл: {unique_filename}")
            
            return web.json_response({
                "success": True,
                "data": {
                    "logo_url": logo_url,
                    "filename": unique_filename
                },
                "message": "Логотип успешно загружен"
            })
            
        except ValueError:
            return web.json_response({
                "success": False,
                "error": "Некорректный ID организационной единицы"
            }, status=400)
        except Exception as e:
            self.logger.error(f"Ошибка загрузки логотипа: {e}")
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def delete_logo(self, request: Request) -> Response:
        """DELETE /api/org-units/{org_unit_id}/logo - Удаление логотипа"""
        try:
            # Проверяем авторизацию
            auth_result = await require_auth(request)
            if not auth_result['success']:
                return web.json_response({
                    "success": False,
                    "error": auth_result['error']
                }, status=401)
            
            org_unit_id = int(request.match_info['org_unit_id'])
            
            # Проверяем права доступа к организационной единице
            user = auth_result['user']
            if not await self._check_org_unit_access(user, org_unit_id):
                return web.json_response({
                    "success": False,
                    "error": "Нет прав доступа к данной организационной единице"
                }, status=403)
            
            # Получаем текущий путь к логотипу
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT logo_url FROM org_unit 
                        WHERE org_unit_id = %s
                    """, (org_unit_id,))
                    
                    row = await cur.fetchone()
                    if not row:
                        return web.json_response({
                            "success": False,
                            "error": "Организационная единица не найдена"
                        }, status=404)
                    
                    logo_url = row[0]
                    
                    # Удаляем путь к логотипу из базы данных
                    await cur.execute("""
                        UPDATE org_unit 
                        SET logo_url = NULL 
                        WHERE org_unit_id = %s
                    """, (org_unit_id,))
            
            # Удаляем файл с диска
            if logo_url and logo_url.startswith('/api/logos/'):
                filename = logo_url.replace('/api/logos/', '')
                file_path = os.path.join(self.upload_dir, filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    self.logger.info(f"Файл логотипа удален: {filename}")
            
            return web.json_response({
                "success": True,
                "message": "Логотип успешно удален"
            })
            
        except ValueError:
            return web.json_response({
                "success": False,
                "error": "Некорректный ID организационной единицы"
            }, status=400)
        except Exception as e:
            self.logger.error(f"Ошибка удаления логотипа: {e}")
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def serve_logo(self, request: Request) -> Response:
        """GET /api/logos/{filename} - Раздача статических файлов логотипов"""
        try:
            filename = request.match_info['filename']
            
            # Проверяем безопасность имени файла
            if '..' in filename or '/' in filename or '\\' in filename:
                self.logger.warning(f"Попытка доступа к небезопасному файлу: {filename}")
                return web.Response(status=400)
            
            file_path = os.path.join(self.upload_dir, filename)
            
            if not os.path.exists(file_path):
                self.logger.warning(f"Файл не найден: {file_path}")
                return web.Response(status=404)
            
            # Определяем MIME-тип по расширению
            file_ext = os.path.splitext(filename)[1].lower()
            mime_types = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp'
            }
            
            content_type = mime_types.get(file_ext, 'application/octet-stream')
            
            # Читаем файл и отправляем
            try:
                async with aiofiles.open(file_path, 'rb') as f:
                    content = await f.read()
                
                self.logger.info(f"Файл отправлен: {filename}")
                
                return web.Response(
                    body=content,
                    content_type=content_type,
                    headers={
                        'Cache-Control': 'public, max-age=3600',  # Кешируем на час
                        'Content-Length': str(len(content))
                    }
                )
            except Exception as e:
                self.logger.error(f"Ошибка чтения файла {file_path}: {e}")
                return web.Response(status=500)
            
        except Exception as e:
            self.logger.error(f"Ошибка раздачи файла логотипа: {e}")
            return web.Response(status=500)
    
    async def _check_org_unit_access(self, user, org_unit_id):
        """Проверяет права доступа пользователя к организационной единице"""
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # Проверяем роль пользователя
                    await cur.execute("""
                        SELECT role FROM user_role 
                        WHERE user_id = %s
                    """, (user['user_id'],))
                    
                    roles = await cur.fetchall()
                    user_roles = [role[0] for role in roles]
                    
                    # service_admin имеет доступ ко всем организационным единицам
                    if 'service_admin' in user_roles:
                        return True
                    
                    # Проверяем принадлежность к организационной единице
                    await cur.execute("""
                        SELECT org_unit_id FROM user_role 
                        WHERE user_id = %s AND org_unit_id = %s
                    """, (user['user_id'], org_unit_id))
                    
                    if await cur.fetchone():
                        return True
                    
                    # Проверяем дочерние организационные единицы
                    await cur.execute("""
                        SELECT COUNT(*) FROM org_unit 
                        WHERE parent_org_unit_id IN (
                            SELECT org_unit_id FROM user_role 
                            WHERE user_id = %s AND org_unit_id IS NOT NULL
                        ) AND org_unit_id = %s
                    """, (user['user_id'], org_unit_id))
                    
                    result = await cur.fetchone()
                    return result[0] > 0
                    
        except Exception as e:
            self.logger.error(f"Ошибка проверки прав доступа: {e}")
            return False
