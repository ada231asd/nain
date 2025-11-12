"""
Модель пользователя
"""
from typing import Optional, Dict, Any
from datetime import datetime
import aiomysql
import bcrypt
from utils.time_utils import get_moscow_time
import secrets
import string
from config.settings import PASSWORD_MIN_LENGTH, PASSWORD_MAX_LENGTH, PASSWORD_HASH_ROUNDS
from utils.centralized_logger import get_logger


class User:
    """Модель пользователя"""
    
    def __init__(self, user_id: int, phone_e164: str, email: str, 
                 password_hash: str, fio: Optional[str] = None,
                 status: str = 'active', role: str = 'user', 
                 created_at: Optional[datetime] = None,
                 last_login_at: Optional[datetime] = None,
                 powerbank_limit: Optional[int] = None):
        self.user_id = user_id
        self.phone_e164 = phone_e164
        self.email = email
        self.password_hash = password_hash
        self.fio = fio
        self.status = status
        self.role = role
        self.created_at = created_at or get_moscow_time()
        self.last_login_at = last_login_at
        self.powerbank_limit = powerbank_limit
    
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
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
            'powerbank_limit': self.powerbank_limit
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
                    INSERT INTO app_user (phone_e164, email, password_hash, fio, status, powerbank_limit)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (phone_e164, email, password_hash, fio, 'pending', None))
                
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
                    last_login_at=user_data['last_login_at'],
                    powerbank_limit=user_data.get('powerbank_limit')
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
                    last_login_at=user_data['last_login_at'],
                    powerbank_limit=user_data.get('powerbank_limit')
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
        
        
        if not cls.verify_password(password, user.password_hash):
            return None
        
        # Проверяем статус пользователя
        if user.status != 'active':
            return None
        
        return user
