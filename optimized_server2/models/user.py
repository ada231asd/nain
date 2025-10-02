"""
Модель пользователя
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import aiomysql
import bcrypt
from utils.time_utils import get_moscow_time
import secrets
import string
import json
from config.settings import PASSWORD_MIN_LENGTH, PASSWORD_MAX_LENGTH, PASSWORD_HASH_ROUNDS
from utils.centralized_logger import get_logger


class User:
    """Модель пользователя"""
    
    def __init__(self, user_id: int, phone_e164: str, email: str, 
                 password_hash: str, fio: Optional[str] = None,
                 status: str = 'active', role: str = 'user', 
                 created_at: Optional[datetime] = None,
                 last_login_at: Optional[datetime] = None):
        self.user_id = user_id
        self.phone_e164 = phone_e164
        self.email = email
        self.password_hash = password_hash
        self.fio = fio
        self.status = status
        self.role = role
        self.created_at = created_at or get_moscow_time()
        self.last_login_at = last_login_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует пользователя в словарь"""
        return {
            'user_id': self.user_id,
            'phone_e164': self.phone_e164,
            'email': self.email,
            'fio': self.fio,
            'status': self.status,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None
        }
    
    @staticmethod
    def generate_password(length: int = 8) -> str:
        """Генерирует случайный пароль"""
        characters = string.ascii_letters + string.digits
        return ''.join(secrets.choice(characters) for _ in range(length))
    
    @staticmethod
    def validate_password(password: str) -> tuple[bool, str]:
        """
        Валидирует пароль для защиты от атак по стороннему каналу
        Возвращает
        """
        if not password:
            return False, "Пароль не может быть пустым"
        
        if len(password) < PASSWORD_MIN_LENGTH:
            return False, f"Пароль должен содержать минимум {PASSWORD_MIN_LENGTH} символов"
        
        if len(password) > PASSWORD_MAX_LENGTH:
            return False, f"Пароль не должен превышать {PASSWORD_MAX_LENGTH} символов"
        
        # Проверяем на наличие только пробельных символов
        if password.strip() != password:
            return False, "Пароль не должен начинаться или заканчиваться пробелами"
        
        return True, ""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Хеширует пароль с использованием bcrypt"""
        # Валидируем пароль перед хешированием
        is_valid, error = User.validate_password(password)
        if not is_valid:
            raise ValueError(f"Некорректный пароль: {error}")
        
        # Используем настраиваемое количество раундов
        salt = bcrypt.gensalt(rounds=PASSWORD_HASH_ROUNDS)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Проверяет пароль с защитой от атак по стороннему каналу"""
        # Ограничиваем длину пароля перед проверкой
        if len(password) > PASSWORD_MAX_LENGTH:
            return False
        
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except (ValueError, TypeError):
            return False
    
    @classmethod
    async def create_user(cls, pool, phone_e164: str, email: str, 
                        fio: Optional[str] = None) -> tuple['User', str]:
        """Создает нового пользователя с автоматически сгенерированным паролем"""
        # Генерируем пароль
        password = cls.generate_password()
        password_hash = cls.hash_password(password)
        
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                # Проверяем, не существует ли уже пользователь с таким телефоном или email
                await cur.execute(
                    "SELECT user_id FROM app_user WHERE phone_e164 = %s OR email = %s",
                    (phone_e164, email)
                )
                existing_user = await cur.fetchone()
                
                if existing_user:
                    raise ValueError("Пользователь с таким телефоном или email уже существует")
                
                # Создаем пользователя
                await cur.execute("""
                    INSERT INTO app_user (phone_e164, email, password_hash, fio, status)
                    VALUES (%s, %s, %s, %s, %s)
                """, (phone_e164, email, password_hash, fio, 'pending'))
                
                user_id = cur.lastrowid
                
                user = cls(
                    user_id=user_id,
                    phone_e164=phone_e164,
                    email=email,
                    password_hash=password_hash,
                    fio=fio,
                    status='pending',
                    created_at=get_moscow_time()
                )
                
                return user, password
    
    @classmethod
    async def get_by_id(cls, pool, user_id: int) -> Optional['User']:
        """Получает пользователя по ID"""
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    "SELECT * FROM app_user WHERE user_id = %s",
                    (user_id,)
                )
                user_data = await cur.fetchone()
                
                if not user_data:
                    return None
                
                # Получаем роль пользователя
                await cur.execute(
                    "SELECT role FROM user_role ur JOIN app_user au ON ur.user_id = au.user_id WHERE au.user_id = %s",
                    (user_data['user_id'],)
                )
                role_data = await cur.fetchone()
                role = role_data['role'] if role_data else 'user'
                
                return cls(
                    user_id=user_data['user_id'],
                    phone_e164=user_data['phone_e164'],
                    email=user_data['email'],
                    password_hash=user_data['password_hash'],
                    fio=user_data['fio'],
                    status=user_data['status'],
                    role=role,
                    created_at=user_data['created_at'],
                    last_login_at=user_data['last_login_at']
                )
    
    @classmethod
    async def get_by_phone(cls, pool, phone_e164: str) -> Optional['User']:
        """Получает пользователя по номеру телефона"""
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    "SELECT * FROM app_user WHERE phone_e164 = %s AND status = 'active'",
                    (phone_e164,)
                )
                user_data = await cur.fetchone()
                
                if not user_data:
                    return None
                
                # Получаем роль пользователя
                await cur.execute(
                    "SELECT role FROM user_role ur JOIN app_user au ON ur.user_id = au.user_id WHERE au.user_id = %s",
                    (user_data['user_id'],)
                )
                role_data = await cur.fetchone()
                role = role_data['role'] if role_data else 'user'
                
                return cls(
                    user_id=user_data['user_id'],
                    phone_e164=user_data['phone_e164'],
                    email=user_data['email'],
                    password_hash=user_data['password_hash'],
                    fio=user_data['fio'],
                    status=user_data['status'],
                    role=role,
                    created_at=user_data['created_at'],
                    last_login_at=user_data['last_login_at']
                )
    
    @classmethod
    async def authenticate(cls, pool, phone_e164: str, password: str) -> Optional['User']:
        """Аутентифицирует пользователя с защитой от атак по стороннему каналу"""
       
        if len(password) > PASSWORD_MAX_LENGTH:
            # Логируем подозрительную попытку
            logger = get_logger('user_auth')
            logger.warning(f"Подозрительная попытка: пароль длиной {len(password)} символов для телефона {phone_e164}")
            return None
        
        user = await cls.get_by_phone(pool, phone_e164)
        if not user:
            return None
        
        # Проверяем пароль с защитой от timing атак
        if not cls.verify_password(password, user.password_hash):
            return None
        
        # Проверяем статус пользователя
        if user.status != 'active':
            return None
        
        return user




class VerificationCode:
    """Модель кода подтверждения"""
    
    def __init__(self, code: str, phone_e164: str, email: str, 
                 expires_at: datetime, is_used: bool = False):
        self.code = code
        self.phone_e164 = phone_e164
        self.email = email
        self.expires_at = expires_at
        self.is_used = is_used
    
    @staticmethod
    def generate_code(length: int = 6) -> str:
        """Генерирует код подтверждения"""
        return ''.join(secrets.choice(string.digits) for _ in range(length))
    
    @classmethod
    async def create_code(cls, pool, phone_e164: str, email: str, 
                         expiration_minutes: int = 10) -> 'VerificationCode':
        """Создает новый код подтверждения"""
        code = cls.generate_code()
        expires_at = get_moscow_time() + timedelta(minutes=expiration_minutes)
        
        verification_code = cls(
            code=code,
            phone_e164=phone_e164,
            email=email,
            expires_at=expires_at
        )
        
       
        await cls._save_code_to_storage(verification_code)
        
        return verification_code
    
    @classmethod
    async def verify_code(cls, pool, phone_e164: str, code: str) -> bool:
        """Проверяет код подтверждения"""
        stored_code = await cls._get_code_from_storage(phone_e164)
        
        if not stored_code:
            return False
        
        if stored_code['code'] != code:
            return False
        
        if stored_code['is_used']:
            return False
        
        if get_moscow_time() > datetime.fromisoformat(stored_code['expires_at']):
            return False
        
        # Помечаем код как использованный
        await cls._mark_code_as_used(phone_e164)
        
        return True
    
    @staticmethod
    async def _save_code_to_storage(code_obj: 'VerificationCode'):
        """Сохраняет код в хранилище"""
        # Простая реализация с JSON файлом
        import json
        import os
        
        storage_file = "verification_codes.json"
        
        # Загружаем существующие коды
        if os.path.exists(storage_file):
            with open(storage_file, 'r', encoding='utf-8') as f:
                codes = json.load(f)
        else:
            codes = {}
        
        # Добавляем новый код
        codes[code_obj.phone_e164] = {
            'code': code_obj.code,
            'email': code_obj.email,
            'expires_at': code_obj.expires_at.isoformat(),
            'is_used': code_obj.is_used
        }
        
        # Сохраняем
        with open(storage_file, 'w', encoding='utf-8') as f:
            json.dump(codes, f, ensure_ascii=False, indent=2)
    
    @staticmethod
    async def _get_code_from_storage(phone_e164: str) -> Optional[dict]:
        """Получает код из хранилища"""
        import json
        import os
        
        storage_file = "verification_codes.json"
        
        if not os.path.exists(storage_file):
            return None
        
        with open(storage_file, 'r', encoding='utf-8') as f:
            codes = json.load(f)
        
        return codes.get(phone_e164)
    
    @staticmethod
    async def _mark_code_as_used(phone_e164: str):
        """Помечает код как использованный"""
        import json
        import os
        
        storage_file = "verification_codes.json"
        
        if not os.path.exists(storage_file):
            return
        
        with open(storage_file, 'r', encoding='utf-8') as f:
            codes = json.load(f)
        
        if phone_e164 in codes:
            codes[phone_e164]['is_used'] = True
            
            with open(storage_file, 'w', encoding='utf-8') as f:
                json.dump(codes, f, ensure_ascii=False, indent=2)
    
    @classmethod
    async def get_all_active_users(cls, pool, limit: int = 10) -> List['User']:
        """Получает всех активных пользователей"""
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT user_id, fio, password_hash, email, phone_e164, status, created_at, last_login_at
                    FROM app_user 
                    WHERE status = 'active'
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (limit,))
                
                results = await cursor.fetchall()
                
                users = []
                for result in results:
                    users.append(cls(
                        user_id=result[0],
                        fio=result[1],
                        password_hash=result[2],
                        email=result[3],
                        phone_e164=result[4],
                        status=result[5],
                        created_at=result[6],
                        last_login_at=result[7]
                    ))
                
                return users
