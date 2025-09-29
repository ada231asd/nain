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
                                 full_name: Optional[str] = None) -> bool:
        """Отправляет пароль на email"""
        subject = f"Пароль от аккаунта {self.smtp_config.get('app_name', 'ЗАРЯД')}"
        
        if full_name:
            body = f"Здравствуйте, {full_name}!\n\nВаш пароль от аккаунта: {password}\n\nОжидайте одобрения администратором. Администратор одобрит вас в ближайшее время.\n\nС уважением,\nКоманда ЗАРЯД"
        else:
            body = f"Ваш пароль от аккаунта: {password}\n\nОжидайте одобрения администратором. Администратор одобрит вас в ближайшее время.\n\nС уважением,\nКоманда ЗАРЯД"
        
        return await self.send_email(user_email, subject, body)
    


# Глобальный экземпляр сервиса
notification_service = NotificationService()
