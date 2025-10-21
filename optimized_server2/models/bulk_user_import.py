"""
Модель для пакетного импорта пользователей из Excel файлов
"""
import io
import pandas as pd
import aiomysql
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from models.user import User
from utils.centralized_logger import get_logger
from utils.notification_service import notification_service
import re


class BulkUserImport:
    """Модель для пакетного импорта пользователей"""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
        self.logger = get_logger('bulk_user_import')
    
    def validate_phone(self, phone: str) -> bool:
        """Валидирует номер телефона в формате E164"""
        if not phone or not isinstance(phone, str):
            return False
        
        # Убираем все пробелы и дефисы
        phone = re.sub(r'[\s\-\(\)]', '', phone.strip())
        
        # Проверяем формат E164 
        if phone.startswith('+') and len(phone) >= 10 and phone[1:].isdigit():
            return True
        
        # Если номер без +, добавляем +7
        if phone.startswith('7') and len(phone) == 11 and phone.isdigit():
            return True
        
        # Если номер начинается с 8, заменяем на +7
        if phone.startswith('8') and len(phone) == 11 and phone.isdigit():
            return True
        
        return False
    
    def normalize_phone(self, phone: str) -> str:
        """Нормализует номер телефона в формат E164"""
        if not phone:
            return ""
        
        # Убираем все пробелы и дефисы
        phone = re.sub(r'[\s\-\(\)]', '', phone.strip())
        
        # Если уже в формате E164
        if phone.startswith('+'):
            return phone
        
        # Если начинается с 8, заменяем на +7
        if phone.startswith('8') and len(phone) == 11:
            return '+7' + phone[1:]
        
        # Если начинается с 7, добавляем +
        if phone.startswith('7') and len(phone) == 11:
            return '+' + phone
        
        return phone
    
    def validate_email(self, email: str) -> bool:
        """Валидирует email адрес"""
        if not email or not isinstance(email, str):
            return False
        
        email = email.strip()
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, email))
    
    def validate_fio(self, fio: str) -> bool:
        """Валидирует ФИО"""
        if not fio or not isinstance(fio, str):
            return False
        
        # ФИО должно содержать хотя бы 2 слова
        words = fio.strip().split()
        return len(words) >= 2 and all(len(word) >= 2 for word in words)
    
    async def parse_excel_file(self, file_content: bytes) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Парсит Excel файл и возвращает список пользователей и ошибки валидации
       
        """
        try:
            # Читаем Excel файл
            df = pd.read_excel(io.BytesIO(file_content))
            
            # Проверяем наличие обязательных колонок
            required_columns = ['fio', 'email', 'phone']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return [], [f"Отсутствуют обязательные колонки: {', '.join(missing_columns)}"]
            
            users = []
            errors = []
            
            for index, row in df.iterrows():
                row_number = index + 2
                
                # Извлекаем данные
                fio = str(row['fio']).strip() if pd.notna(row['fio']) else ""
                email = str(row['email']).strip() if pd.notna(row['email']) else ""
                phone = str(row['phone']).strip() if pd.notna(row['phone']) else ""
                
                # Валидируем данные
                row_errors = []
                
                if not self.validate_fio(fio):
                    row_errors.append(f"Строка {row_number}: Некорректное ФИО '{fio}'")
                
                if not self.validate_email(email):
                    row_errors.append(f"Строка {row_number}: Некорректный email '{email}'")
                
                if not self.validate_phone(phone):
                    row_errors.append(f"Строка {row_number}: Некорректный телефон '{phone}'")
                
                if row_errors:
                    errors.extend(row_errors)
                    continue
                
                # Нормализуем телефон
                normalized_phone = self.normalize_phone(phone)
                
                users.append({
                    'fio': fio,
                    'email': email,
                    'phone_e164': normalized_phone,
                    'row_number': row_number
                })
            
            self.logger.info(f"Парсинг Excel файла: найдено {len(users)} валидных пользователей, {len(errors)} ошибок")
            return users, errors
            
        except Exception as e:
            error_msg = f"Ошибка парсинга Excel файла: {str(e)}"
            self.logger.error(error_msg)
            return [], [error_msg]
    
    async def check_existing_users(self, users: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Проверяет существующих пользователей в базе данных
        
        """
        try:
            if not users:
                return [], []
            
            # Собираем все телефоны и email для проверки
            phones = [user['phone_e164'] for user in users]
            emails = [user['email'] for user in users]
            
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Проверяем существующих пользователей
                    placeholders_phone = ','.join(['%s'] * len(phones))
                    placeholders_email = ','.join(['%s'] * len(emails))
                    
                    await cur.execute(f"""
                        SELECT phone_e164, email, fio 
                        FROM app_user 
                        WHERE phone_e164 IN ({placeholders_phone}) 
                        OR email IN ({placeholders_email})
                    """, phones + emails)
                    
                    existing_users = await cur.fetchall()
            
            # Создаем множества для быстрого поиска
            existing_phones = {user['phone_e164'] for user in existing_users}
            existing_emails = {user['email'] for user in existing_users}
            
            new_users = []
            errors = []
            
            for user in users:
                user_errors = []
                
                if user['phone_e164'] in existing_phones:
                    user_errors.append(f"Строка {user['row_number']}: Пользователь с телефоном {user['phone_e164']} уже существует")
                
                if user['email'] in existing_emails:
                    user_errors.append(f"Строка {user['row_number']}: Пользователь с email {user['email']} уже существует")
                
                if user_errors:
                    errors.extend(user_errors)
                else:
                    new_users.append(user)
            
            self.logger.info(f"Проверка существующих пользователей: {len(new_users)} новых, {len(errors)} конфликтов")
            return new_users, errors
            
        except Exception as e:
            error_msg = f"Ошибка проверки существующих пользователей: {str(e)}"
            self.logger.error(error_msg)
            return [], [error_msg]
    
    async def create_users_bulk(self, users: List[Dict[str, Any]], org_unit_id: Optional[int] = None, 
                                progress_callback=None) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Создает пользователей в базе данных и отправляет пароли на email
       
        """
        try:
            if not users:
                return [], []
            
            created_users = []
            errors = []
            total_users = len(users)
            for index, user in enumerate(users, 1):
                try:
                    # Отправляем прогресс через callback
                    if progress_callback:
                        await progress_callback({
                            'type': 'bulk_import_progress',
                            'current': index,
                            'total': total_users,
                            'user': user['fio'],
                            'status': 'creating'
                        })
                    
                    # Создаем пользователя
                    user_obj, password = await User.create_user(
                        self.db_pool, 
                        user['phone_e164'], 
                        user['email'], 
                        user['fio']
                    )
                    
                    # Если указана группа, привязываем пользователя к ней
                    if org_unit_id:
                        async with self.db_pool.acquire() as conn:
                            async with conn.cursor(aiomysql.DictCursor) as cur:
                                await cur.execute("""
                                    INSERT INTO user_role (user_id, org_unit_id, role, created_at)
                                    VALUES (%s, %s, 'user', NOW())
                                """, (user_obj.user_id, org_unit_id))
                    
                    # Отправляем прогресс
                    if progress_callback:
                        await progress_callback({
                            'type': 'bulk_import_progress',
                            'current': index,
                            'total': total_users,
                            'user': user['fio'],
                            'status': 'sending_email'
                        })
                    
                    # Отправляем пароль на email
                    email_sent = await notification_service.send_password_email(
                        user['email'], 
                        password, 
                        user['fio'], 
                        user['phone_e164']
                    )
                    
                    created_users.append({
                        'user_id': user_obj.user_id,
                        'fio': user['fio'],
                        'email': user['email'],
                        'phone_e164': user['phone_e164'],
                        'password': password,
                        'email_sent': email_sent,
                        'row_number': user['row_number']
                    })
                    
                    # Отправляем прогресс о завершении создания пользователя
                    if progress_callback:
                        await progress_callback({
                            'type': 'bulk_import_progress',
                            'current': index,
                            'total': total_users,
                            'user': user['fio'],
                            'status': 'completed',
                            'email_sent': email_sent
                        })
                    
                    self.logger.info(f"Создан пользователь {user['fio']} (ID: {user_obj.user_id})")
                    
                except Exception as e:
                    error_msg = f"Строка {user['row_number']}: Ошибка создания пользователя {user['fio']}: {str(e)}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
                    
                    # Отправляем прогресс об ошибке
                    if progress_callback:
                        await progress_callback({
                            'type': 'bulk_import_progress',
                            'current': index,
                            'total': total_users,
                            'user': user['fio'],
                            'status': 'error',
                            'error': str(e)
                        })
            
            self.logger.info(f"Пакетное создание пользователей: создано {len(created_users)}, ошибок {len(errors)}")
            return created_users, errors
            
        except Exception as e:
            error_msg = f"Ошибка пакетного создания пользователей: {str(e)}"
            self.logger.error(error_msg)
            return [], [error_msg]
    
    async def import_users_from_excel(self, file_content: bytes, org_unit_id: Optional[int] = None, 
                                      progress_callback=None) -> Dict[str, Any]:
        """
        Полный процесс импорта пользователей из Excel файла
        
        """
        try:
            self.logger.info("Начало импорта пользователей из Excel файла")
            
            # 1. Парсим Excel файл
            users, parse_errors = await self.parse_excel_file(file_content)
            
            if not users:
                return {
                    'success': False,
                    'message': 'Не найдено валидных пользователей для импорта',
                    'errors': parse_errors,
                    'statistics': {
                        'total_parsed': 0,
                        'valid_users': 0,
                        'existing_users': 0,
                        'created_users': 0,
                        'errors': len(parse_errors)
                    }
                }
            
            # 2. Проверяем существующих пользователей
            new_users, existing_errors = await self.check_existing_users(users)
            
            # 3. Создаем новых пользователей
            created_users, creation_errors = await self.create_users_bulk(new_users, org_unit_id, progress_callback)
            
            # Собираем все ошибки
            all_errors = parse_errors + existing_errors + creation_errors
            
            # Статистика
            statistics = {
                'total_parsed': len(users) + len(parse_errors),
                'valid_users': len(users),
                'existing_users': len(existing_errors),
                'created_users': len(created_users),
                'errors': len(all_errors)
            }
            
            success = len(created_users) > 0
            
            message = f"Импорт завершен. Создано пользователей: {len(created_users)}"
            if existing_errors:
                message += f", пропущено существующих: {len(existing_errors)}"
            if creation_errors:
                message += f", ошибок: {len(creation_errors)}"
            
            self.logger.info(f"Импорт завершен: {message}")
            
            return {
                'success': success,
                'message': message,
                'created_users': created_users,
                'errors': all_errors,
                'statistics': statistics
            }
            
        except Exception as e:
            error_msg = f"Критическая ошибка импорта: {str(e)}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'message': error_msg,
                'errors': [error_msg],
                'statistics': {
                    'total_parsed': 0,
                    'valid_users': 0,
                    'existing_users': 0,
                    'created_users': 0,
                    'errors': 1
                }
            }
