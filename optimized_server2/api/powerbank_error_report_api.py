"""
API для отчетов об ошибках повербанков
"""
from aiohttp import web
from typing import Dict, Any
from datetime import datetime

from models.powerbank import Powerbank
from models.order import Order
from models.station import Station


class PowerbankErrorReportAPI:
    """API для управления отчетами об ошибках повербанков"""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
    
    async def report_powerbank_error(self, order_id: int, powerbank_id: int, 
                                   station_id: int, user_id: int, 
                                   error_type: str, additional_notes: str = None) -> Dict[str, Any]:
        """
        Создает отчет об ошибке повербанка
        """
        try:
            print(f" PowerbankErrorReportAPI: Отчет об ошибке - order_id={order_id}, powerbank_id={powerbank_id}, error_type={error_type}")
            
            # Проверяем, что заказ существует и принадлежит пользователю
            order = await Order.get_by_id(self.db_pool, order_id)
            if not order:
                return {"error": "Заказ не найден", "success": False}
            
            if order.user_id != user_id:
                return {"error": "Заказ не принадлежит пользователю", "success": False}
            
            if order.status != 'borrow':
                return {"error": "Заказ неактивен", "success": False}
            
            # Проверяем, что повербанк существует
            powerbank = await Powerbank.get_by_id(self.db_pool, powerbank_id)
            if not powerbank:
                return {"error": "Повербанк не найден", "success": False}
            
            # Проверяем, что станция существует
            station = await Station.get_by_id(self.db_pool, station_id)
            if not station:
                return {"error": "Станция не найдена", "success": False}
            
            # Обновляем статус повербанка в зависимости от типа ошибки
            new_status = self._map_error_type_to_status(error_type)
            if new_status:
                await powerbank.update_status(self.db_pool, new_status)
                print(f" Статус повербанка {powerbank_id} изменен на {new_status}")
            
            # Обновляем write_off_reason
            write_off_reason = self._map_error_type_to_write_off_reason(error_type)
            if write_off_reason:
                await powerbank.update_write_off_reason(self.db_pool, write_off_reason)
                print(f" Причина списания повербанка {powerbank_id} изменена на {write_off_reason}")
            
            return {
                "success": True,
                "message": "Отчет об ошибке создан успешно",
                "powerbank_id": powerbank_id,
                "error_type": error_type,
                "new_status": new_status,
                "write_off_reason": write_off_reason,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f" Ошибка создания отчета об ошибке: {e}")
            return {"error": f"Ошибка создания отчета об ошибке: {str(e)}", "success": False}
    
    def _map_error_type_to_status(self, error_type: str) -> str:
        """Маппинг типа ошибки на статус повербанка"""
        error_mapping = {
            'cable_type_c_damaged': 'user_reported_broken',
            'cable_lightning_damaged': 'user_reported_broken', 
            'cable_micro_usb_damaged': 'user_reported_broken',
            'powerbank_not_working': 'user_reported_broken',
            'cable_damaged': 'user_reported_broken',
            'other': 'user_reported_broken'
        }
        return error_mapping.get(error_type, 'user_reported_broken')
    
    def _map_error_type_to_write_off_reason(self, error_type: str) -> str:
        """Маппинг типа ошибки на причину списания"""
        reason_mapping = {
            'cable_type_c_damaged': 'broken',
            'cable_lightning_damaged': 'broken',
            'cable_micro_usb_damaged': 'broken', 
            'powerbank_not_working': 'broken',
            'cable_damaged': 'broken',
            'other': 'other'
        }
        return reason_mapping.get(error_type, 'broken')
