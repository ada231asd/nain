"""
Обработчик для отчетов об аномалиях слотов
"""
from typing import Optional, Dict, Any
from datetime import datetime

from utils.packet_utils import parse_slot_abnormal_report_request, build_slot_abnormal_report_response


class SlotAbnormalReportHandler:
    """Обработчик для отчетов об аномалиях слотов"""
    
    def __init__(self, db_pool, connection_manager):
        self.db_pool = db_pool
        self.connection_manager = connection_manager
    
    async def handle_slot_abnormal_report_request(self, data: bytes, connection) -> Optional[bytes]:
        """
        Обрабатывает запрос отчета об аномалии слота
        Возвращает ответ для отправки на станцию или None
        """
        try:
            # Парсим запрос от станции
            abnormal_report = parse_slot_abnormal_report_request(data)
            print(f"Обработан отчет об аномалии слота: {abnormal_report}")
            
            station_id = connection.station_id
            if not station_id:
                print("Станция не найдена для соединения")
                return None
            
            # Сохраняем отчет об аномалии в базу данных
            await self._save_abnormal_report_to_database(station_id, abnormal_report)
            
            # Создаем ответ для станции
            secret_key = connection.secret_key
            if not secret_key:
                print("Нет секретного ключа для ответа на отчет об аномалии")
                return None
            
            response = build_slot_abnormal_report_response(
                secret_key=secret_key,
                vsn=1  # Можно получить из соединения
            )
            
            print(f"Создан ответ на отчет об аномалии слота для станции {station_id}")
            return response
            
        except Exception as e:
            print(f"Ошибка обработки отчета об аномалии слота: {e}")
            return None
    
    async def _save_abnormal_report_to_database(self, station_id: int, abnormal_report: Dict[str, Any]) -> None:
        """Сохраняет отчет об аномалии слота в базу данных и в parsed_packets.json"""
        try:
            # Сохраняем отчет в таблицу slot_abnormal_reports
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        INSERT INTO slot_abnormal_reports 
                        (station_id, slot_number, terminal_id, event_type, event_text, 
                         reported_at, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    """, (
                        station_id,
                        abnormal_report['SlotNo'],
                        abnormal_report['TerminalID'],
                        abnormal_report['Event'],
                        abnormal_report['EventText'],
                        abnormal_report['ReceivedAt']
                    ))
                    await conn.commit()
            
            # Сохраняем в parsed_packets.json
            await self._save_to_parsed_packets(abnormal_report)
            
            print(f"Отчет об аномалии слота сохранен для станции {station_id}, слот {abnormal_report['SlotNo']}")
            
        except Exception as e:
            print(f"Ошибка сохранения отчета об аномалии в БД: {e}")
    
    async def _save_to_parsed_packets(self, abnormal_report: Dict[str, Any]) -> None:
        """Сохраняет разобранные данные в parsed_packets.json"""
        try:
            import json
            import os
            from datetime import datetime
            
            # Читаем существующий файл или создаем новый
            filename = 'parsed_packets.json'
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = []
            
            # Добавляем новый пакет
            packet_data = {
                "timestamp": datetime.now().isoformat(),
                "command": "0x83",
                "type": "Slot Status Abnormal Report",
                "data": abnormal_report
            }
            
            data.append(packet_data)
            
            # Сохраняем обратно в файл
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"Данные команды 0x83 сохранены в {filename}")
            
        except Exception as e:
            print(f"Ошибка сохранения в parsed_packets.json: {e}")
    
    async def get_station_abnormal_reports(self, station_id: int, limit: int = 50) -> Dict[str, Any]:
        """
        Получает отчеты об аномалиях слотов станции из базы данных
        """
        try:
            # Получаем отчеты об аномалиях для станции
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT 
                            report_id,
                            station_id,
                            slot_number,
                            terminal_id,
                            event_type,
                            event_text,
                            reported_at,
                            created_at
                        FROM slot_abnormal_reports 
                        WHERE station_id = %s
                        ORDER BY reported_at DESC
                        LIMIT %s
                    """, (station_id, limit))
                    reports_data = await cur.fetchall()
            
            reports = []
            for report_data in reports_data:
                report = {
                    "report_id": report_data[0],
                    "station_id": report_data[1],
                    "slot_number": report_data[2],
                    "terminal_id": report_data[3],
                    "event_type": report_data[4],
                    "event_text": report_data[5],
                    "reported_at": report_data[6].isoformat() if report_data[6] else None,
                    "created_at": report_data[7].isoformat() if report_data[7] else None
                }
                reports.append(report)
            
            return {
                "success": True,
                "station_id": station_id,
                "reports_count": len(reports),
                "reports": reports
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Ошибка получения отчетов об аномалиях: {str(e)}"
            }
    
    async def get_all_abnormal_reports(self, limit: int = 100) -> Dict[str, Any]:
        """
        Получает все отчеты об аномалиях слотов из базы данных
        """
        try:
            # Получаем все отчеты об аномалиях
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT 
                            sar.report_id,
                            sar.station_id,
                            s.box_id,
                            sar.slot_number,
                            sar.terminal_id,
                            sar.event_type,
                            sar.event_text,
                            sar.reported_at,
                            sar.created_at
                        FROM slot_abnormal_reports sar
                        LEFT JOIN station s ON sar.station_id = s.station_id
                        ORDER BY sar.reported_at DESC
                        LIMIT %s
                    """, (limit,))
                    reports_data = await cur.fetchall()
            
            reports = []
            for report_data in reports_data:
                report = {
                    "report_id": report_data[0],
                    "station_id": report_data[1],
                    "box_id": report_data[2],
                    "slot_number": report_data[3],
                    "terminal_id": report_data[4],
                    "event_type": report_data[5],
                    "event_text": report_data[6],
                    "reported_at": report_data[7].isoformat() if report_data[7] else None,
                    "created_at": report_data[8].isoformat() if report_data[8] else None
                }
                reports.append(report)
            
            return {
                "success": True,
                "reports_count": len(reports),
                "reports": reports
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Ошибка получения всех отчетов об аномалиях: {str(e)}"
            }
    
    async def get_abnormal_reports_statistics(self) -> Dict[str, Any]:
        """
        Получает статистику по отчетам об аномалиях слотов
        """
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # Общая статистика
                    await cur.execute("""
                        SELECT 
                            COUNT(*) as total_reports,
                            COUNT(DISTINCT station_id) as stations_with_reports,
                            COUNT(CASE WHEN reported_at > DATE_SUB(NOW(), INTERVAL 1 DAY) THEN 1 END) as reports_today,
                            COUNT(CASE WHEN reported_at > DATE_SUB(NOW(), INTERVAL 7 DAY) THEN 1 END) as reports_week,
                            COUNT(CASE WHEN reported_at > DATE_SUB(NOW(), INTERVAL 30 DAY) THEN 1 END) as reports_month
                        FROM slot_abnormal_reports
                    """)
                    stats = await cur.fetchone()
                    
                    # Статистика по типам событий
                    await cur.execute("""
                        SELECT 
                            event_type,
                            event_text,
                            COUNT(*) as count
                        FROM slot_abnormal_reports 
                        GROUP BY event_type, event_text
                        ORDER BY count DESC
                    """)
                    event_stats = await cur.fetchall()
                    
                    # Статистика по станциям
                    await cur.execute("""
                        SELECT 
                            s.station_id,
                            s.box_id,
                            COUNT(sar.report_id) as reports_count
                        FROM station s
                        LEFT JOIN slot_abnormal_reports sar ON s.station_id = sar.station_id
                        GROUP BY s.station_id, s.box_id
                        ORDER BY reports_count DESC
                        LIMIT 10
                    """)
                    station_stats = await cur.fetchall()
            
            return {
                "success": True,
                "statistics": {
                    "total_reports": stats[0],
                    "stations_with_reports": stats[1],
                    "reports_today": stats[2],
                    "reports_week": stats[3],
                    "reports_month": stats[4]
                },
                "event_statistics": [
                    {
                        "event_type": row[0],
                        "event_text": row[1],
                        "count": row[2]
                    } 
                    for row in event_stats
                ],
                "station_statistics": [
                    {
                        "station_id": row[0],
                        "box_id": row[1],
                        "reports_count": row[2]
                    } 
                    for row in station_stats
                ]
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Ошибка получения статистики отчетов об аномалиях: {str(e)}"
            }
