"""
Сервис для отправки уведомлений (SMS, Email)
"""
import smtplib
import logging
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from config.settings import NOTIFICATION_CONFIG


class NotificationService:
    """Сервис для отправки уведомлений"""
    
    def __init__(self):
        self.logger = logging.getLogger('notification_service')
        self.smtp_config = NOTIFICATION_CONFIG.get('smtp', {})
        self.email_enabled = self.smtp_config.get('enabled', True)
        self.last_disable_time = None  # Время последнего отключения
        self.disable_duration = 300  # 5 минут до автоматического включения
        
        # Проверяем доступность SMTP при инициализации
        if self.email_enabled:
            self._check_smtp_config()
    
    def _validate_email(self, email: str) -> bool:
        """Валидирует email адрес"""
        if not email or not isinstance(email, str):
            return False
        
        # Простая валидация email
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, email.strip()))
    
    def _check_smtp_config(self):
        """Проверяет конфигурацию SMTP"""
        if not self.smtp_config:
            self.logger.warning("SMTP конфигурация не найдена, отправка email отключена")
            self.email_enabled = False
            return
            
        required_fields = ['host', 'port', 'username', 'password', 'from_email']
        missing_fields = [field for field in required_fields if not self.smtp_config.get(field)]
        if missing_fields:
            self.logger.warning(f"Отсутствуют обязательные поля SMTP конфигурации: {missing_fields}, отправка email отключена")
            self.email_enabled = False
            return
        
        # Валидируем from_email
        if not self._validate_email(self.smtp_config.get('from_email')):
            self.logger.warning(f"Некорректный from_email: {self.smtp_config.get('from_email')}, отправка email отключена")
            self.email_enabled = False
            return
            
        self.logger.info(f"SMTP настроен: {self.smtp_config.get('host')}:{self.smtp_config.get('port')}")
    
    def _check_auto_reenable(self):
        """Проверяет, нужно ли автоматически включить email после временного отключения"""
        import time
        if (not self.email_enabled and 
            self.last_disable_time and 
            time.time() - self.last_disable_time > self.disable_duration):
            
            self.logger.info("Автоматически включаем отправку email после временного отключения")
            self.email_enabled = True
            self.last_disable_time = None
    
    def force_enable_email(self):
        """Принудительно включает отправку email"""
        self.email_enabled = True
        self.last_disable_time = None
        self.logger.info("Email принудительно включен")
    
    async def verify_email_delivery(self, to_email: str) -> bool:
        """Проверяет возможность доставки email (базовая проверка)"""
        if not self._validate_email(to_email):
            self.logger.warning(f"Некорректный email адрес: {to_email}")
            return False
        
        # Проверяем, что email не является тестовым или несуществующим
        test_emails = ['test@example.com', 'krug@gmail.com', 'nonexistent@test.com']
        if to_email.lower() in test_emails:
            self.logger.warning(f"Попытка отправки на тестовый/несуществующий email: {to_email}")
            return False
        
        return True
    
    async def send_email(self, to_email: str, subject: str, body: str, 
                        html_body: Optional[str] = None, max_retries: int = 2) -> bool:
        """Отправляет email с повторными попытками"""
        # Валидируем email адрес получателя
        if not self._validate_email(to_email):
            self.logger.error(f"Некорректный email адрес получателя: {to_email}")
            return False
        
        # Проверяем возможность доставки
        if not await self.verify_email_delivery(to_email):
            self.logger.warning(f"Email {to_email} не прошел проверку доставки, пропускаем отправку")
            return True  # Возвращаем True чтобы не блокировать регистрацию
        
        # Проверяем автоматическое включение
        self._check_auto_reenable()
        
        # Проверяем, включена ли отправка email
        if not self.email_enabled:
            self.logger.info(f"Отправка email отключена. Сообщение для {to_email}: {subject}")
            return True  # Возвращаем True чтобы не блокировать регистрацию
        
        import asyncio
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    self.logger.info(f"Повторная попытка отправки email #{attempt} на {to_email}")
                    await asyncio.sleep(2)  # Пауза между попытками
                else:
                    self.logger.info(f"Отправка email на {to_email} через {self.smtp_config.get('host')}:{self.smtp_config.get('port')}")
                
                # Создаем сообщение
                msg = MIMEMultipart('alternative')
                msg['From'] = self.smtp_config.get('from_email')
                msg['To'] = to_email
                msg['Subject'] = subject
                msg['Reply-To'] = 'noreply@zarayd.ru'  
                msg['X-Auto-Response-Suppress'] = 'All'  # Подавляем автоответы
                msg['Precedence'] = 'bulk'  # Помечаем как массовую рассылку
                
                # Добавляем текстовую версию
                text_part = MIMEText(body, 'plain', 'utf-8')
                msg.attach(text_part)
                
                # Добавляем HTML версию если есть
                if html_body:
                    html_part = MIMEText(html_body, 'html', 'utf-8')
                    msg.attach(html_part)
                
                # Отправляем email
                with smtplib.SMTP(self.smtp_config.get('host'), self.smtp_config.get('port')) as server:
                    server.set_debuglevel(0)  # Отключаем отладку для продакшена
                    
                    if self.smtp_config.get('use_tls', True):
                        if attempt == 0:  # Логируем только в первой попытке
                            self.logger.info("Включаем TLS...")
                        server.starttls()
                    
                    if self.smtp_config.get('username') and self.smtp_config.get('password'):
                        if attempt == 0:  # Логируем только в первой попытке
                            self.logger.info(f"Авторизация как {self.smtp_config['username']}")
                        server.login(self.smtp_config['username'], self.smtp_config['password'])
                    
                    server.send_message(msg)
                
                self.logger.info(f"Email успешно отправлен на {to_email}")
                return True
                
            except smtplib.SMTPAuthenticationError as e:
                self.logger.error(f"Ошибка аутентификации SMTP для {to_email}: {e}")
                # Отключаем email при ошибке аутентификации (не повторяем)
                self.email_enabled = False
                return False
            except smtplib.SMTPRecipientsRefused as e:
                # Ошибка "пользователь не существует" или "почтовый ящик недоступен"
                self.logger.error(f"Отклонен получатель {to_email}: {e}")
                # Не отключаем email полностью, но не повторяем для этого адреса
                return False
            except smtplib.SMTPDataError as e:
                # Ошибка данных (например, неправильный формат сообщения)
                self.logger.error(f"Ошибка данных SMTP для {to_email}: {e}")
                if attempt == max_retries:
                    return False
                continue  # Повторяем попытку
            except smtplib.SMTPConnectError as e:
                self.logger.error(f"Ошибка подключения к SMTP серверу для {to_email}: {e}")
                if attempt == max_retries:
                    # Временно отключаем email после всех попыток
                    import time
                    self.email_enabled = False
                    self.last_disable_time = time.time()
                    self.logger.warning(f"Временно отключаем email на {self.disable_duration} секунд из-за ошибок подключения")
                    return False
                continue  # Повторяем попытку
            except smtplib.SMTPException as e:
                self.logger.error(f"Ошибка SMTP при отправке на {to_email}: {e}")
                if attempt == max_retries:
                    return False
                continue  # Повторяем попытку
            except OSError as e:
                # DNS resolution errors, network issues
                self.logger.error(f"Сетевая ошибка при отправке email на {to_email}: {e}")
                if attempt == max_retries:
                    return False
                continue  # Повторяем попытку
            except Exception as e:
                self.logger.error(f"Общая ошибка отправки email на {to_email}: {e}")
                if attempt == max_retries:
                    return False
                continue  # Повторяем попытку
        
        # Если дошли сюда, все попытки исчерпаны
        self.logger.error(f"Не удалось отправить email на {to_email} после {max_retries + 1} попыток")
        return False
    
    async def send_password_email(self, user_email: str, password: str, 
                                 full_name: Optional[str] = None, phone_number: Optional[str] = None) -> bool:
        """Отправляет пароль на email с улучшенным форматированием"""
        subject = f"Подтверждение аккаунта {self.smtp_config.get('app_name', 'ЗАРЯД')}"
        max_retries = self.smtp_config.get('max_retries', 2)
        
        # Телефон теперь используется как логин, дублирование не нужно
        
        # Текстовая версия
        if full_name:
            body = f"""Здравствуйте, {full_name}!

Ваш аккаунт успешно создан в системе ЗАРЯД.

Данные для входа:
Логин (телефон): {phone_number}
Пароль: {password}

Ожидайте одобрения администратором. Администратор одобрит вас в ближайшее время.

С уважением,
Команда ЗАРЯД"""
        else:
            body = f"""Ваш аккаунт успешно создан в системе ЗАРЯД.

Данные для входа:
Логин (телефон): {phone_number}
Пароль: {password}

Ожидайте одобрения администратором. Администратор одобрит вас в ближайшее время.

С уважением,
Команда ЗАРЯД"""
        
        # HTML версия с жирным текстом
        if full_name:
            html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #2c5aa0;">Подтверждение аккаунта ЗАРЯД</h2>
    
    <p>Здравствуйте, <strong>{full_name}</strong>!</p>
    
    <p>Ваш аккаунт успешно создан в системе ЗАРЯД.</p>
    
    <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #2c5aa0; margin: 20px 0;">
        <h3 style="margin-top: 0; color: #2c5aa0;">Данные для входа:</h3>
        <p><strong>Логин (телефон):</strong> <span style="font-weight: 600; color: #495057;">{phone_number}</span></p>
        <p><strong>Пароль:</strong> <span style="font-family: 'Courier New', monospace; font-weight: 600; color: #495057; background-color: #e9ecef; padding: 4px 8px; border-radius: 4px; font-size: 16px;">{password}</span></p>
    </div>
    
    <p style="color: #050300;">Ожидайте одобрения администратором. Администратор одобрит вас в ближайшее время.</p>
    
    <p style="color: #999; font-size: 12px; margin-top: 30px; text-align: center;">
        Это автоматическое сообщение. Пожалуйста, не отвечайте на него.
    </p>
    
    <hr style="border: none; border-top: 1px solid #dee2e6; margin: 30px 0;">
    <p style="color: #6c757d; font-size: 14px;">
        С уважением,<br>
        <strong>Команда ЗАРЯД</strong>
    </p>
</body>
</html>"""
        else:
            html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #2c5aa0;">Подтверждение аккаунта ЗАРЯД</h2>
    
    <p>Ваш аккаунт успешно создан в системе ЗАРЯД.</p>
    
    <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #2c5aa0; margin: 20px 0;">
        <h3 style="margin-top: 0; color: #2c5aa0;">Данные для входа:</h3>
        <p><strong>Логин (телефон):</strong> <span style="font-weight: 600; color: #495057;">{phone_number}</span></p>
        <p><strong>Пароль:</strong> <span style="font-family: 'Courier New', monospace; font-weight: 600; color: #495057; background-color: #e9ecef; padding: 4px 8px; border-radius: 4px; font-size: 16px;">{password}</span></p>
    </div>
    
    <p style="color: #050300;">Ожидайте одобрения администратором. Администратор одобрит вас в ближайшее время.</p>
    
    <p style="color: #999; font-size: 12px; margin-top: 30px; text-align: center;">
        Это автоматическое сообщение. Пожалуйста, не отвечайте на него.
    </p>
    
    <hr style="border: none; border-top: 1px solid #dee2e6; margin: 30px 0;">
    <p style="color: #6c757d; font-size: 14px;">
        С уважением,<br>
        <strong>Команда ЗАРЯД</strong>
    </p>
</body>
</html>"""
        
        return await self.send_email(user_email, subject, body, html_body, max_retries)
    
    async def send_account_approved_email(self, user_email: str, full_name: Optional[str] = None, 
                                        phone_number: Optional[str] = None) -> bool:
        """Отправляет уведомление об одобрении аккаунта"""
        subject = f"Аккаунт одобрен - {self.smtp_config.get('app_name', 'ЗАРЯД')}"
        max_retries = self.smtp_config.get('max_retries', 2)
        
        
        # Текстовая версия
        if full_name:
            body = f"""Здравствуйте, {full_name}!

 Отличные новости! Ваш аккаунт в системе ЗАРЯД был одобрен администратором.

Теперь вы можете войти в систему, используя ранее отправленные данные:
Логин (телефон): {phone_number}

Добро пожаловать в систему ЗАРЯД!

С уважением,
Команда ЗАРЯД"""
        else:
            body = f""" Отличные новости! Ваш аккаунт в системе ЗАРЯД был одобрен администратором.

Теперь вы можете войти в систему, используя ранее отправленные данные:
Логин (телефон): {phone_number}

Добро пожаловать в систему ЗАРЯД!

С уважением,
Команда ЗАРЯД"""
        
        # HTML версия
        if full_name:
            html_body = f"""
<html>
<head>
    <style>
        .welcome-button:hover {{
            background-color: #28a745 !important;
            color: #fff !important;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(40, 167, 69, 0.3);
        }}
    </style>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #28a745;"> Аккаунт одобрен!</h2>
    
    <p>Здравствуйте, <strong>{full_name}</strong>!</p>
    
    <div style="background-color: #d4edda; padding: 15px; border-left: 4px solid #28a745; margin: 20px 0; border-radius: 5px;">
        <p style="margin: 0; color: #155724;"><strong>Отличные новости!</strong> Ваш аккаунт в системе ЗАРЯД был одобрен администратором.</p>
    </div>
    
    <p>Теперь вы можете войти в систему, используя ранее отправленные данные:</p>
    <p><strong>Логин (телефон):</strong> <span style="font-weight: 600; color: #495057;">{phone_number}</span></p>
    
    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; text-align: center;">
        <a href="https://redmine.primetech.ru:8443" class="welcome-button" style="text-decoration: none; color: #28a745; font-size: 18px; font-weight: bold; display: inline-block; padding: 10px 20px; border: 2px solid #28a745; border-radius: 5px; background-color: #fff; transition: all 0.3s ease;">
            Добро пожаловать в систему ЗАРЯД!
        </a>
    </div>
    
    <p style="color: #999; font-size: 12px; margin-top: 30px; text-align: center;">
        Это автоматическое сообщение. Пожалуйста, не отвечайте на него.
    </p>
    
    <hr style="border: none; border-top: 1px solid #dee2e6; margin: 30px 0;">
    <p style="color: #6c757d; font-size: 14px;">
        С уважением,<br>
        <strong>Команда ЗАРЯД</strong>
    </p>
</body>
</html>"""
        else:
            html_body = f"""
<html>
<head>
    <style>
        .welcome-button:hover {{
            background-color: #28a745 !important;
            color: #fff !important;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(40, 167, 69, 0.3);
        }}
    </style>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #28a745;"> Аккаунт одобрен!</h2>
    
    <div style="background-color: #d4edda; padding: 15px; border-left: 4px solid #28a745; margin: 20px 0; border-radius: 5px;">
        <p style="margin: 0; color: #155724;"><strong>Отличные новости!</strong> Ваш аккаунт в системе ЗАРЯД был одобрен администратором.</p>
    </div>
    
    <p>Теперь вы можете войти в систему, используя ранее отправленные данные:</p>
    <p><strong>Логин (телефон):</strong> <span style="font-weight: 600; color: #495057;">{phone_number}</span></p>
    
    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; text-align: center;">
        <a href="https://redmine.primetech.ru:8443" class="welcome-button" style="text-decoration: none; color: #28a745; font-size: 18px; font-weight: bold; display: inline-block; padding: 10px 20px; border: 2px solid #28a745; border-radius: 5px; background-color: #fff; transition: all 0.3s ease;">
            Добро пожаловать в систему ЗАРЯД!
        </a>
    </div>
    
    <p style="color: #999; font-size: 12px; margin-top: 30px; text-align: center;">
        Это автоматическое сообщение. Пожалуйста, не отвечайте на него.
    </p>
    
    <hr style="border: none; border-top: 1px solid #dee2e6; margin: 30px 0;">
    <p style="color: #6c757d; font-size: 14px;">
        С уважением,<br>
        <strong>Команда ЗАРЯД</strong>
    </p>
</body>
</html>"""
        
        return await self.send_email(user_email, subject, body, html_body, max_retries)


# Глобальный экземпляр сервиса
notification_service = NotificationService()

def reset_email_service():
    """Сброс состояния email сервиса (для отладки)"""
    global notification_service
    notification_service.force_enable_email()
    print("Email сервис сброшен и включен")

async def test_email_sending(test_email: str = "test@example.com") -> bool:
    """Тестирует отправку email"""
    global notification_service
    
    print(f"Тестируем отправку email на {test_email}")
    
    # Проверяем валидацию
    is_valid = notification_service._validate_email(test_email)
    print(f"Email валиден: {is_valid}")
    
    # Проверяем возможность доставки
    can_deliver = await notification_service.verify_email_delivery(test_email)
    print(f"Можно доставить: {can_deliver}")
    
    # Пробуем отправить тестовое сообщение
    success = await notification_service.send_email(
        to_email=test_email,
        subject="Тестовое сообщение",
        body="Это тестовое сообщение для проверки работы email сервиса.",
        html_body="<p>Это <strong>тестовое сообщение</strong> для проверки работы email сервиса.</p>"
    )
    
    print(f"Результат отправки: {success}")
    return success
