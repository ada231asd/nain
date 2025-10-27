"""
Сервис для отправки напоминаний о возврате аккумуляторов
"""
import asyncio
import aiomysql
from datetime import datetime, timedelta
from typing import List, Dict, Any
from utils.notification_service import notification_service
from utils.centralized_logger import get_logger


class PowerbankReminderService:
    """Сервис для проверки и отправки напоминаний о невозвращенных аккумуляторах"""
    
    def __init__(self, db_pool: aiomysql.Pool):
        self.db_pool = db_pool
        self.logger = get_logger('powerbank_reminder')
        self.sent_reminders = set()  # Множество для отслеживания отправленных напоминаний (order_id)
    
    async def get_overdue_powerbanks(self) -> List[Dict[str, Any]]:
        """Получает список невозвращенных аккумуляторов, по которым нужно отправить напоминание"""
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Находим все невозвращенные аккумуляторы, где прошло больше reminder_hours
                    await cur.execute("""
                        SELECT 
                            o.id as order_id,
                            o.user_id,
                            o.powerbank_id,
                            o.timestamp as borrow_time,
                            u.fio as user_name,
                            u.email as user_email,
                            p.serial_number as powerbank_serial,
                            ou.name as org_unit_name,
                            ou.reminder_hours,
                            TIMESTAMPDIFF(HOUR, o.timestamp, NOW()) as hours_borrowed
                        FROM orders o
                        INNER JOIN app_user u ON o.user_id = u.user_id
                        INNER JOIN powerbank p ON o.powerbank_id = p.id
                        LEFT JOIN org_unit ou ON o.org_unit_id = ou.org_unit_id
                        WHERE o.status = 'borrow'
                          AND o.completed_at IS NULL
                          AND TIMESTAMPDIFF(HOUR, o.timestamp, NOW()) >= COALESCE(ou.reminder_hours, 24)
                          AND u.email IS NOT NULL
                          AND u.email != ''
                    """)
                    
                    overdue = await cur.fetchall()
                    
                    return overdue
                    
        except Exception as e:
            self.logger.error(f"Ошибка при получении списка невозвращенных аккумуляторов: {e}", exc_info=True)
            return []
    
    async def send_reminder(self, order_data: Dict[str, Any]) -> bool:
        """Отправляет напоминание пользователю о необходимости вернуть аккумулятор"""
        try:
            order_id = order_data['order_id']
            
            # Проверяем, не отправляли ли мы уже напоминание для этого заказа
            if order_id in self.sent_reminders:
                self.logger.debug(f"Напоминание для заказа {order_id} уже отправлено, пропускаем")
                return True
            
            user_email = order_data['user_email']
            user_name = order_data['user_name']
            powerbank_serial = order_data['powerbank_serial']
            org_unit_name = order_data['org_unit_name']
            hours_borrowed = order_data['hours_borrowed']
            
            # Отправляем email
            success = await notification_service.send_powerbank_reminder_email(
                user_email=user_email,
                full_name=user_name,
                powerbank_serial=powerbank_serial,
                hours_overdue=hours_borrowed,
                org_unit_name=org_unit_name
            )
            
            if success:
                # Добавляем order_id в множество отправленных напоминаний
                self.sent_reminders.add(order_id)
                
                # Логируем отправку напоминания в БД (опционально)
                await self._log_reminder_sent(order_data)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Ошибка при отправке напоминания: {e}", exc_info=True)
            return False
    
    async def _log_reminder_sent(self, order_data: Dict[str, Any]) -> None:
        """Логирует отправку напоминания в таблицу action_logs"""
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        INSERT INTO action_logs 
                        (user_id, action_type, entity_type, entity_id, description)
                        VALUES (%s, 'system_error', 'order', %s, %s)
                    """, (
                        order_data['user_id'],
                        order_data['order_id'],
                        f"Отправлено напоминание о возврате аккумулятора {order_data['powerbank_serial']}"
                    ))
        except Exception as e:
            self.logger.error(f"Ошибка при логировании отправки напоминания: {e}")
    
    async def check_and_send_reminders(self) -> int:
        """Проверяет невозвращенные аккумуляторы и отправляет напоминания"""
        try:
            # Получаем список невозвращенных аккумуляторов
            overdue_powerbanks = await self.get_overdue_powerbanks()
            
            if not overdue_powerbanks:
                return 0
            
            sent_count = 0
            
            # Отправляем напоминания
            for order_data in overdue_powerbanks:
                success = await self.send_reminder(order_data)
                if success:
                    sent_count += 1
                
                # Небольшая задержка между отправками, чтобы не перегружать SMTP сервер
                await asyncio.sleep(1)
            
            return sent_count
            
        except Exception as e:
            self.logger.error(f"Ошибка при проверке и отправке напоминаний: {e}", exc_info=True)
            return 0
    
    async def run_periodic_check(self, interval_hours: float = 0.5) -> None:
        """Запускает периодическую проверку невозвращенных аккумуляторов"""
        while True:
            try:
                await self.check_and_send_reminders()
                
                # Очищаем множество отправленных напоминаний раз в 24 часа
                # чтобы можно было отправлять повторные напоминания
                if len(self.sent_reminders) > 1000:  # Ограничение размера множества
                    self.sent_reminders.clear()
                
            except Exception as e:
                self.logger.error(f"Ошибка в периодической проверке: {e}", exc_info=True)
            
            # Ждем до следующей проверки
            await asyncio.sleep(interval_hours * 3600)  # Преобразуем часы в секунды
    
    def clear_sent_reminders(self) -> None:
        """Очищает множество отправленных напоминаний"""
        self.sent_reminders.clear()

