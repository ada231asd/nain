"""
Сервис для отправки уведомлений (SMS, Email)
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from config.settings import NOTIFICATION_CONFIG


class NotificationService:
    """Сервис для отправки уведомлений"""
    
    def __init__(self):
        self.logger = logging.getLogger('notification_service')
        self.smtp_config = NOTIFICATION_CONFIG.get('smtp', {})
    
    async def send_email(self, to_email: str, subject: str, body: str, 
                        html_body: Optional[str] = None) -> bool:
        """Отправляет email"""
        try:
            # Создаем сообщение
            msg = MIMEMultipart('alternative')
            msg['From'] = self.smtp_config.get('from_email')
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Добавляем текстовую версию
            text_part = MIMEText(body, 'plain', 'utf-8')
            msg.attach(text_part)
            
            # Добавляем HTML версию если есть
            if html_body:
                html_part = MIMEText(html_body, 'html', 'utf-8')
                msg.attach(html_part)
            
            # Отправляем email
            with smtplib.SMTP(self.smtp_config.get('host'), self.smtp_config.get('port')) as server:
                if self.smtp_config.get('use_tls', True):
                    server.starttls()
                
                if self.smtp_config.get('username') and self.smtp_config.get('password'):
                    server.login(self.smtp_config['username'], self.smtp_config['password'])
                
                server.send_message(msg)
            
            self.logger.info(f"Email успешно отправлен на {to_email}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка отправки email на {to_email}: {e}")
            return False
    
    async def send_password_email(self, user_email: str, password: str, 
                                 full_name: Optional[str] = None, phone_number: Optional[str] = None) -> bool:
        """Отправляет пароль на email с улучшенным форматированием"""
        subject = f"Подтверждение аккаунта {self.smtp_config.get('app_name', 'ЗАРЯД')}"
        
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
        <p><strong>Логин (телефон):</strong> <span style="font-weight: bold; color: #d63384;">{phone_number}</span></p>
        <p><strong>Пароль:</strong> <span style="font-weight: bold; color: #d63384; font-size: 18px; background-color: #fff3cd; padding: 2px 6px; border-radius: 3px;">{password}</span></p>
    </div>
    
    <p style="color: #6c757d;"> Ожидайте одобрения администратором. Администратор одобрит вас в ближайшее время.</p>
    
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
        <p><strong>Логин (телефон):</strong> <span style="font-weight: bold; color: #d63384;">{phone_number}</span></p>
        <p><strong>Пароль:</strong> <span style="font-weight: bold; color: #d63384; font-size: 18px; background-color: #fff3cd; padding: 2px 6px; border-radius: 3px;">{password}</span></p>
    </div>
    
    <p style="color: #6c757d;"> Ожидайте одобрения администратором. Администратор одобрит вас в ближайшее время.</p>
    
    <hr style="border: none; border-top: 1px solid #dee2e6; margin: 30px 0;">
    <p style="color: #6c757d; font-size: 14px;">
        С уважением,<br>
        <strong>Команда ЗАРЯД</strong>
    </p>
</body>
</html>"""
        
        return await self.send_email(user_email, subject, body, html_body)
    
    async def send_account_approved_email(self, user_email: str, full_name: Optional[str] = None, 
                                        phone_number: Optional[str] = None) -> bool:
        """Отправляет уведомление об одобрении аккаунта"""
        subject = f"Аккаунт одобрен - {self.smtp_config.get('app_name', 'ЗАРЯД')}"
        
        
        # Текстовая версия
        if full_name:
            body = f"""Здравствуйте, {full_name}!

🎉 Отличные новости! Ваш аккаунт в системе ЗАРЯД был одобрен администратором.

Теперь вы можете войти в систему, используя ранее отправленные данные:
Логин (телефон): {phone_number}

Добро пожаловать в систему ЗАРЯД!

С уважением,
Команда ЗАРЯД"""
        else:
            body = f"""🎉 Отличные новости! Ваш аккаунт в системе ЗАРЯД был одобрен администратором.

Теперь вы можете войти в систему, используя ранее отправленные данные:
Логин (телефон): {phone_number}

Добро пожаловать в систему ЗАРЯД!

С уважением,
Команда ЗАРЯД"""
        
        # HTML версия
        if full_name:
            html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #28a745;"> Аккаунт одобрен!</h2>
    
    <p>Здравствуйте, <strong>{full_name}</strong>!</p>
    
    <div style="background-color: #d4edda; padding: 15px; border-left: 4px solid #28a745; margin: 20px 0; border-radius: 5px;">
        <p style="margin: 0; color: #155724;"><strong>Отличные новости!</strong> Ваш аккаунт в системе ЗАРЯД был одобрен администратором.</p>
    </div>
    
    <p>Теперь вы можете войти в систему, используя ранее отправленные данные:</p>
    <p><strong>Логин (телефон):</strong> <span style="font-weight: bold; color: #2c5aa0;">{phone_number}</span></p>
    
    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; text-align: center;">
        <p style="margin: 0; color: #28a745; font-size: 18px;"><strong>Добро пожаловать в систему ЗАРЯД!</strong></p>
    </div>
    
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
    <h2 style="color: #28a745;"> Аккаунт одобрен!</h2>
    
    <div style="background-color: #d4edda; padding: 15px; border-left: 4px solid #28a745; margin: 20px 0; border-radius: 5px;">
        <p style="margin: 0; color: #155724;"><strong>Отличные новости!</strong> Ваш аккаунт в системе ЗАРЯД был одобрен администратором.</p>
    </div>
    
    <p>Теперь вы можете войти в систему, используя ранее отправленные данные:</p>
    <p><strong>Логин (телефон):</strong> <span style="font-weight: bold; color: #2c5aa0;">{phone_number}</span></p>
    
    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; text-align: center;">
        <p style="margin: 0; color: #28a745; font-size: 18px;"><strong>Добро пожаловать в систему ЗАРЯД!</strong></p>
    </div>
    
    <hr style="border: none; border-top: 1px solid #dee2e6; margin: 30px 0;">
    <p style="color: #6c757d; font-size: 14px;">
        С уважением,<br>
        <strong>Команда ЗАРЯД</strong>
    </p>
</body>
</html>"""
        
        return await self.send_email(user_email, subject, body, html_body)


# Глобальный экземпляр сервиса
notification_service = NotificationService()
