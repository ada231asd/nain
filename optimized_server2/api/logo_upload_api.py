"""
API для загрузки логотипов организационных единиц
"""
import os
import uuid
import aiofiles
import aiohttp
from aiohttp import web
from aiohttp.web import Request, Response
from urllib.parse import urlparse
from utils.auth_middleware import require_auth


class LogoUploadAPI:
    """API для загрузки логотипов"""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
        
        # Настройки загрузки
        self.upload_dir = "uploads/logos"
        # Разрешаем до 15MB на файл (совместимо с глобальным лимитом 20MB)
        self.max_file_size = 15 * 1024 * 1024
        self.allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        
        # Создаем папку для загрузок если её нет
        os.makedirs(self.upload_dir, exist_ok=True)
    
    async def _validate_and_download_url(self, url: str) -> tuple[bytes, str]:
        """Валидирует URL и загружает изображение"""
        try:
            # Парсим URL
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise ValueError("Некорректный URL")
            
            # Проверяем, что это HTTP или HTTPS
            if parsed_url.scheme not in ['http', 'https']:
                raise ValueError("Поддерживаются только HTTP и HTTPS URL")
            
            # Проверяем размер URL (защита от слишком длинных URL)
            if len(url) > 2048:
                raise ValueError("URL слишком длинный")
            
            # Загружаем изображение
            timeout = aiohttp.ClientTimeout(total=30)  # 30 секунд таймаут
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise ValueError(f"Не удалось загрузить изображение. HTTP статус: {response.status}")
                    
                    # Проверяем Content-Type
                    content_type = response.headers.get('Content-Type', '').lower()
                    if not content_type.startswith('image/'):
                        raise ValueError("URL не указывает на изображение")
                    
                    # Проверяем размер файла
                    content_length = response.headers.get('Content-Length')
                    if content_length and int(content_length) > self.max_file_size:
                        raise ValueError(f"Размер изображения превышает {self.max_file_size // (1024*1024)}MB")
                    
                    # Читаем содержимое
                    content = await response.read()
                    
                    # Дополнительная проверка размера после загрузки
                    if len(content) > self.max_file_size:
                        raise ValueError(f"Размер изображения превышает {self.max_file_size // (1024*1024)}MB")
                    
                    # Определяем расширение файла по Content-Type
                    file_ext = '.jpg'  # по умолчанию
                    if 'image/png' in content_type:
                        file_ext = '.png'
                    elif 'image/gif' in content_type:
                        file_ext = '.gif'
                    elif 'image/webp' in content_type:
                        file_ext = '.webp'
                    elif 'image/jpeg' in content_type:
                        file_ext = '.jpg'
                    
                    return content, file_ext
                    
        except aiohttp.ClientError as e:
            raise ValueError(f"Ошибка загрузки изображения: {str(e)}")
        except Exception as e:
            raise ValueError(f"Ошибка обработки URL: {str(e)}")
    
    def setup_routes(self, app):
        """Настраивает маршруты для загрузки логотипов"""
        app.router.add_post('/api/org-units/{org_unit_id}/logo', self.upload_logo)
        app.router.add_post('/api/org-units/{org_unit_id}/logo-url', self.upload_logo_from_url)
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
            
            # Проверяем, что запрос содержит данные
            if not request.has_body:
                return web.json_response({
                    "success": False,
                    "error": "Отсутствуют данные для загрузки"
                }, status=400)
            
            content_type = request.headers.get('Content-Type', '')
            file_content = None
            filename = None
            file_ext = None
            logo_url = None

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
                    elif part.name == 'logo_url':
                        # Получаем URL логотипа
                        logo_url = await part.read()
                        logo_url = logo_url.decode('utf-8').strip()
                        break
            else:
                # Проверяем, является ли запрос JSON с URL
                try:
                    data = await request.json()
                    if 'logo_url' in data:
                        logo_url = data['logo_url'].strip()
                    else:
                        # Фолбэк: принимаем сырое тело как файл
                        file_content = await request.read()
                        filename = f"{org_unit_id}_{uuid.uuid4().hex}.bin"
                except Exception as e:
                    # Если не JSON, пробуем как файл
                    try:
                        file_content = await request.read()
                        filename = f"{org_unit_id}_{uuid.uuid4().hex}.bin"
                    except Exception:
                        pass
            
            # Обрабатываем URL логотипа
            if logo_url:
                try:
                    file_content, file_ext = await self._validate_and_download_url(logo_url)
                    filename = f"{org_unit_id}_{uuid.uuid4().hex}{file_ext}"
                except ValueError as e:
                    return web.json_response({
                        "success": False,
                        "error": str(e)
                    }, status=400)
            
            if not file_content:
                return web.json_response({
                    "success": False,
                    "error": "Отсутствует файл логотипа или URL в запросе"
                }, status=400)
            
            # Проверяем размер файла
            if len(file_content) > self.max_file_size:
                return web.json_response({
                    "success": False,
                    "error": f"Размер файла превышает {self.max_file_size // (1024*1024)}MB"
                }, status=400)
            
            # Определяем расширение файла
            if not file_ext:  # Если расширение не определено из URL
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
                else:
                    file_ext = '.jpg'  # по умолчанию
            
            # Проверяем расширение файла
            if file_ext not in self.allowed_extensions:
                return web.json_response({
                    "success": False,
                    "error": f"Недопустимое расширение файла. Разрешены: {', '.join(self.allowed_extensions)}"
                }, status=400)
            
            # Генерируем уникальное имя файла
            unique_filename = f"{org_unit_id}_{uuid.uuid4().hex}{file_ext}"
            file_path = os.path.join(self.upload_dir, unique_filename)
            
            # Сохраняем файл
            try:
                async with aiofiles.open(file_path, 'wb') as f:
                    await f.write(file_content)
            except Exception:
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
            except Exception:
                # Удаляем загруженный файл при ошибке БД
                if os.path.exists(file_path):
                    os.remove(file_path)
                return web.json_response({
                    "success": False,
                    "error": "Ошибка сохранения данных"
                }, status=500)
            
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
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def upload_logo_from_url(self, request: Request) -> Response:
        """POST /api/org-units/{org_unit_id}/logo-url - Загрузка логотипа по URL"""
        try:
            # Проверяем авторизацию
            auth_result = await require_auth(request)
            if not auth_result['success']:
                return web.json_response({
                    "success": False,
                    "error": auth_result['error']
                }, status=401)
            
            org_unit_id = int(request.match_info['org_unit_id'])
            
            # Получаем URL из запроса
            try:
                data = await request.json()
                logo_url = data.get('logo_url', '').strip()
                if not logo_url:
                    return web.json_response({
                        "success": False,
                        "error": "URL логотипа не указан"
                    }, status=400)
            except Exception:
                return web.json_response({
                    "success": False,
                    "error": "Некорректный JSON в запросе"
                }, status=400)
            
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
            
            # Загружаем изображение по URL
            try:
                file_content, file_ext = await self._validate_and_download_url(logo_url)
                filename = f"{org_unit_id}_{uuid.uuid4().hex}{file_ext}"
            except ValueError as e:
                return web.json_response({
                    "success": False,
                    "error": str(e)
                }, status=400)
            
            # Генерируем уникальное имя файла
            unique_filename = f"{org_unit_id}_{uuid.uuid4().hex}{file_ext}"
            file_path = os.path.join(self.upload_dir, unique_filename)
            
            # Сохраняем файл
            try:
                async with aiofiles.open(file_path, 'wb') as f:
                    await f.write(file_content)
            except Exception:
                return web.json_response({
                    "success": False,
                    "error": "Ошибка сохранения файла"
                }, status=500)
            
            # Обновляем путь к логотипу в базе данных
            logo_url_path = f"/api/logos/{unique_filename}"
            
            try:
                async with self.db_pool.acquire() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute("""
                            UPDATE org_unit 
                            SET logo_url = %s 
                            WHERE org_unit_id = %s
                        """, (logo_url_path, org_unit_id))
                        
                        if cur.rowcount == 0:
                            # Удаляем загруженный файл если обновление не удалось
                            if os.path.exists(file_path):
                                os.remove(file_path)
                            return web.json_response({
                                "success": False,
                                "error": "Организационная единица не найдена"
                            }, status=404)
            except Exception:
                # Удаляем загруженный файл при ошибке БД
                if os.path.exists(file_path):
                    os.remove(file_path)
                return web.json_response({
                    "success": False,
                    "error": "Ошибка сохранения данных"
                }, status=500)
            
            return web.json_response({
                "success": True,
                "data": {
                    "logo_url": logo_url_path,
                    "filename": unique_filename,
                    "source_url": logo_url
                },
                "message": "Логотип успешно загружен по URL"
            })
            
        except ValueError:
            return web.json_response({
                "success": False,
                "error": "Некорректный ID организационной единицы"
            }, status=400)
        except Exception as e:
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
                return web.Response(status=400)
            
            file_path = os.path.join(self.upload_dir, filename)
            
            if not os.path.exists(file_path):
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
                
                return web.Response(
                    body=content,
                    content_type=content_type,
                    headers={
                        'Cache-Control': 'public, max-age=3600',  # Кешируем на час
                        'Content-Length': str(len(content))
                    }
                )
            except Exception:
                return web.Response(status=500)
            
        except Exception:
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
                    
        except Exception:
            return False
