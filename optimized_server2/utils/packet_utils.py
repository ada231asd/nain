"""
Утилиты для работы с пакетами
"""
import struct
import hashlib
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple, Optional
from config.settings import MAX_PACKET_SIZE, PROTOCOL_COMMAND_RANGE, MAX_SUSPICIOUS_PACKETS

# Импортируем централизованные функции времени
from utils.time_utils import get_moscow_time, get_moscow_now

def log_packet(data: bytes, direction: str, station_box_id: str = "unknown", command_name: str = "Unknown"):
    """Логирование TCP пакета через логгер с точным временем"""
    try:
        from utils.tcp_packet_logger import log_tcp_packet
        import time
        
        hex_data = data.hex().upper()
        size = len(data)
        
        # Определяем команду
        command_hex = "Unknown"
        if size >= 3:
            command_hex = f"0x{data[2]:02X}"
        
        # Добавляем микросекундную точность времени
        timestamp = time.time()
        microseconds = int((timestamp - int(timestamp)) * 1000000)
        time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
        precise_time = f"{time_str}.{microseconds:06d}"
        
        # Логируем через TCP логгер с точным временем
        log_tcp_packet(
            direction=direction,
            packet_type=command_name,
            station_id=station_box_id,
            packet_size=size,
            command=command_hex,
            packet_data=hex_data,
            additional_info=f"TIME:{precise_time}"
        )
            
    except Exception as e:
        print(f"Ошибка логирования пакета: {e}")

def log_packet_with_station(data: bytes, direction: str, station_box_id: str, command_name: str):
    """Логирование пакета с информацией о станции"""
    log_packet(data, direction, station_box_id, command_name)

def validate_packet(data: bytes, connection) -> Tuple[bool, str]:
    """
    Проверяет валидность пакета - базовая проверка структуры
    """
    try:
        # Проверка размера пакета
        if len(data) > MAX_PACKET_SIZE:
            return False, f"Пакет слишком большой: {len(data)} байт (максимум {MAX_PACKET_SIZE})"
        
        if len(data) < 9:  # Минимум: 2(длина) + 1(команда) + 1(VSN) + 1(checksum) + 4(token)
            return False, f"Пакет слишком короткий: {len(data)} байт (минимум 9)"
        
        # Проверка команды
        command = data[2]
        min_cmd, max_cmd = PROTOCOL_COMMAND_RANGE
        if command < min_cmd or command > max_cmd:
            return False, f"Недопустимая команда: 0x{command:02X} (вне диапазона 0x{min_cmd:02X}-0x{max_cmd:02X})"
        
        
        packet_len = struct.unpack('>H', data[:2])[0]
       
       
        if command == 0x64:  # QueryInventory
            if abs(packet_len - len(data)) > 50:  
                return False, f"Критичное несоответствие длины: заявлено {packet_len}, фактически {len(data)}"
        else:
            if abs(packet_len - len(data)) > 10:  
                return False, f"Критичное несоответствие длины: заявлено {packet_len}, фактически {len(data)}"
        
  
        if len(data) >= 9:
            vsn = data[3]
            checksum = data[4]
            token = struct.unpack('>I', data[5:9])[0]
            payload = data[9:] 
            
            
            if vsn < 1 or vsn > 10:
                return False, f"Подозрительный VSN: {vsn}"
            
            # Проверяем checksum для payload
            if payload and len(payload) > 0:
                computed_checksum = compute_checksum(payload)
                if computed_checksum != checksum:
                    return False, f"Неверный checksum: ожидался 0x{computed_checksum:02X}, получен 0x{checksum:02X}"
            
            # Проверяем токен (для Login команды токен может быть нулевым)
            if token == 0 and command != 0x60:  # 0x60 = Login
                return False, f"Нулевой токен: 0x{token:08X}"
        
        return True, ""
        
    except Exception as e:
        return False, f"Ошибка валидации пакета: {e}"

def log_suspicious_packet(data: bytes, connection, reason: str) -> None:
    """Логирует подозрительный пакет"""
    try:
        from utils.tcp_packet_logger import log_tcp_error
        
        station_id = connection.box_id or "unknown"
        hex_data = data.hex().upper()
        
        log_tcp_error(
            station_id=station_id,
            error_message=f"ПОДОЗРИТЕЛЬНЫЙ ПАКЕТ: {reason}",
            packet_data=hex_data
        )
        
        
        log_packet(data, "SUSPICIOUS", station_id, f"SUSPICIOUS_{reason}")
        
    except Exception as e:
        print(f"Ошибка логирования подозрительного пакета: {e}")


def compute_checksum(payload_bytes: bytes) -> int:
    """Вычисляет контрольную сумму"""
    checksum = 0
    for b in payload_bytes:
        checksum ^= b
    return checksum

def generate_token(payload: bytes, secret_key: str) -> bytes:
  
    import hashlib  
    combined = payload + secret_key.encode('utf-8')
    md5_hash = hashlib.md5(combined).digest()
    token = bytes([
        md5_hash[15],  
        md5_hash[11],  
        md5_hash[7],   
        md5_hash[3]    
    ])
    
    return token


def parse_terminal_id(bytes8: bytes) -> str:
    """Парсит terminal ID из 8 байт"""
    try:
        # Пытаемся декодировать первые 4 байта как ASCII
        ascii_part = bytes8[:4].decode('ascii')
        hex_part = ''.join(f"{b:02X}" for b in bytes8[4:])
        return ascii_part + hex_part
    except UnicodeDecodeError:
        # Если не удается декодировать как ASCII, используем только hex
        return ''.join(f"{b:02X}" for b in bytes8)


def parse_login_packet(data: bytes) -> Dict[str, Any]:
    """Парсит пакет логина станции"""
    try:
        packet_format = ">H B B B I I H H"
        header_size = struct.calcsize(packet_format)
        packet_len, command, vsn, checksum, token, nonce, magic, boxid_len = struct.unpack(
            packet_format, data[:header_size]
        )

        if magic != 0xA0A0:
            raise ValueError(f"Magic неверный: {hex(magic)}")

        payload_bytes = data[header_size - 8:]
        if compute_checksum(payload_bytes) != checksum:
            raise ValueError("Неверный checksum")

        boxid_start = header_size
        boxid_end = boxid_start + boxid_len
        boxid = data[boxid_start:boxid_end].rstrip(b'\x00').decode('ascii')

        timestamp, slots_num, remain_num = struct.unpack(">I B B", data[boxid_end:boxid_end + 6])
        timestamp_str = datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        slot_data_start = boxid_end + 6
        slot_format = ">B 8s B H H b B B"
        slot_size = struct.calcsize(slot_format)
        slots = []
        offset = slot_data_start
        
        while offset + slot_size <= len(data):
            slot_bytes = data[offset:offset + slot_size]
            slot_number, terminal_id_bytes, level, voltage, current, temp, status, soh = struct.unpack(
                slot_format, slot_bytes
            )
            terminal_id = parse_terminal_id(terminal_id_bytes)
            status_bits = {
                "InsertionSwitch": (status >> 7) & 1,
                "LockStatus": (status >> 6) & 1,
                "PowerBankError": (status >> 5) & 1,
                "ChargingSwitch": (status >> 4) & 1,
                "ChargingStatus": (status >> 3) & 1,
                "TypeCError": (status >> 2) & 1,
                "LightningError": (status >> 1) & 1,
                "MicroUSBError": status & 1
            }
            slots.append({
                "Slot": slot_number,
                "TerminalID": terminal_id,
                "Level": level,
                "Voltage": voltage,
                "Current": current,
                "Temp": temp,
                "Status": status_bits,
                "SOH": soh
            })
            offset += slot_size

        parsed = {
            "Type": "Login",
            "CheckSumValid": True,
            "Token": f"0x{token:08X}",
            "Nonce": nonce,
            "Magic": hex(magic),
            "BoxID": boxid,
            "Timestamp": timestamp_str,
            "SlotsNumDeclared": slots_num,
            "RemainNum": remain_num,
            "SlotsParsed": len(slots),
            "Slots": slots,
            "PacketLen": packet_len,
            "Command": hex(command),
            "VSN": vsn,
            "CheckSum": hex(checksum),
            "RawPacket": data.hex()
        }
        return parsed
    except Exception as e:
        return {
            "Type": "Login",
            "Error": f"Ошибка парсинга: {str(e)}",
            "RawPacket": data.hex(),
            "Size": len(data)
        }


def build_login_response(vsn: int, nonce: int, secret_key: bytes) -> Tuple[bytes, int]:
    """Создает ответ на логин"""
    command = 0x60
    result = 1
    timestamp = int(get_moscow_time().timestamp())
    new_nonce = random.randint(0, 0xffffffff)
    payload = struct.pack(">BII", result, new_nonce, timestamp)
    checksum = compute_checksum(payload)
    md5 = hashlib.md5(payload + secret_key).digest()
    session_token = md5[3] + md5[7]*256 + md5[11]*65536 + md5[15]*16777216
    packet_len = 7 + len(payload)
    header = struct.pack(">hBBBL", packet_len, command, vsn, checksum, session_token)
    return header + payload, session_token


def build_heartbeat_response(secret_key: bytes, vsn: int = 1) -> bytes:
    """Создает ответ на heartbeat"""
    command = 0x61
    packet_len = 7
    checksum = 0
    payload = b''  # Для heartbeat payload пустой
    md5 = hashlib.md5(payload + secret_key).digest()
    token = md5[3] + md5[7]*256 + md5[11]*65536 + md5[15]*16777216
    header = struct.pack(">hBBBL", packet_len, command, vsn, checksum, token)
    packet = header
    
    # Проверяем валидность созданного пакета
    if len(packet) != 7:
        print(f"❌ ОШИБКА: HeartbeatResponse имеет неправильную длину: {len(packet)} байт")
    
    if packet[2] != 0x61:
        print(f"❌ ОШИБКА: HeartbeatResponse имеет неправильную команду: 0x{packet[2]:02X}")
    
    return packet
def build_borrow_power_bank(secret_key: bytes, slot: int = 1, vsn: int = 1):
    command = 0x65
    packet_len = 8
    payload = struct.pack(">B", slot)
    checksum = compute_checksum(payload)
    md5 = hashlib.md5(payload + secret_key).digest()
    token = md5[3] + md5[7]*256 + md5[11]*65536 + md5[15]*16777216
    header = struct.pack(">hBBBL", packet_len, command, vsn, checksum, token)
    packet = header + payload
    
    # Логируем пакет
    # Логирование происходит в server.py
    
    return packet

def build_return_power_bank(secret_key: bytes, slot: int = 1, vsn: int = 1):
    """Создает команду на возврат повербанка (команда 0x66)"""
    command = 0x66
    packet_len = 8
    payload = struct.pack(">B", slot)
    checksum = compute_checksum(payload)
    md5 = hashlib.md5(payload + secret_key).digest()
    token = md5[3] + md5[7]*256 + md5[11]*65536 + md5[15]*16777216
    header = struct.pack(">hBBBL", packet_len, command, vsn, checksum, token)
    packet = header + payload
    
    # Логируем пакет
    # Логирование происходит в server.py
    
    return packet

def build_return_power_bank_response(slot: int, result: int, terminal_id: bytes, level: int, voltage: int, current: int, temperature: int, status: int, soh: int, vsn: int, token: int):
    command = 0x66
    payload = struct.pack(">BB8sBHHBBB", slot, result, terminal_id, level, voltage, current, temperature, status, soh)
    checksum = compute_checksum(payload)
    header = struct.pack(">HBBBL", len(payload)+7, command, vsn, checksum, token)
    packet = header + payload
    
    # Логируем пакет
    # Логирование происходит в server.py
    
    return packet


def parse_borrow_request(data: bytes) -> Dict[str, Any]:
    """Парсит запрос на выдачу повербанка (команда 0x65)"""
    if len(data) < 9:
        raise ValueError("Слишком короткий пакет для запроса выдачи")
    
    packet_format = ">H B B B I"
    packet_len, command, vsn, checksum, token = struct.unpack(packet_format, data[:9])
    
    if command != 0x65:
        raise ValueError(f"Неверная команда: {hex(command)}")
    
    slot = data[8] if len(data) > 8 else 0
    
    # Проверяем checksum
    payload = struct.pack("B", slot)
    if compute_checksum(payload) != checksum:
        raise ValueError("Неверный checksum")
    
    return {
        "Type": "BorrowRequest",
        "PacketLen": packet_len,
        "Command": hex(command),
        "VSN": vsn,
        "CheckSum": hex(checksum),
        "Token": f"0x{token:08X}",
        "Slot": slot,
        "CheckSumValid": True
    }


def parse_borrow_response(data: bytes) -> Dict[str, Any]:
    """Парсит ответ на выдачу повербанка (команда 0x65)"""
    try:
        if len(data) < 21:  
            raise ValueError("Слишком короткий пакет для ответа BorrowResponse")

        packet_format = ">H B B B I"
        packet_len, command, vsn, checksum, token = struct.unpack(packet_format, data[:9])

        if command != 0x65:
            raise ValueError(f"Неверная команда: {hex(command)}")

        payload = data[9:]
        if len(payload) < 12:
            raise ValueError("Недостаточно данных для BorrowResponse payload")

        slot = payload[0]
        result_code = payload[1]
        terminal_id_bytes = payload[2:10]
        terminal_id = parse_terminal_id(terminal_id_bytes)
        current_slot_lock_status = payload[10]
        adjacent_slot_lock_status = payload[11]

        # Проверка checksum
        if compute_checksum(payload) != checksum:
            checksum_valid = False
            checksum_error = "Неверный checksum"
        else:
            checksum_valid = True
            checksum_error = None

        result = {
            "Type": "BorrowResponse",
            "PacketLen": packet_len,
            "Command": hex(command),
            "VSN": vsn,
            "CheckSum": hex(checksum),
            "CheckSumValid": checksum_valid,
            "Token": f"0x{token:08X}",
            "Slot": slot,
            "ResultCode": result_code,
            "TerminalID": terminal_id,
            "CurrentSlotLockStatus": current_slot_lock_status,
            "AdjacentSlotLockStatus": adjacent_slot_lock_status,
            "Success": result_code == 1,
            "ReceivedAt": get_moscow_time().isoformat(),
            "RawPacket": data.hex()
        }
        if not checksum_valid:
            result["CheckSumError"] = checksum_error

        return result

    except Exception as e:
        return {
            "Type": "BorrowResponse",
            "Error": str(e),
            "RawPacket": data.hex(),
            "Size": len(data)
        }



def parse_return_response(data: bytes) -> Dict[str, Any]:
    """Парсит ответ на возврат повербанка (команда 0x66)"""
    try:
        if len(data) < 21:  
            raise ValueError("Слишком короткий пакет для ответа ReturnResponse")

        packet_format = ">H B B B I"
        packet_len, command, vsn, checksum, token = struct.unpack(packet_format, data[:9])

        if command != 0x66:
            raise ValueError(f"Неверная команда: {hex(command)}")

        payload = data[9:]
        if len(payload) < 12:
            raise ValueError("Недостаточно данных для ReturnResponse payload")

        # Разбор payload
        slot = payload[0]
        result_code = payload[1]
        terminal_id_bytes = payload[2:10]
        terminal_id = parse_terminal_id(terminal_id_bytes)
        current_slot_lock_status = payload[10]
        adjacent_slot_lock_status = payload[11]

        # Проверка checksum
        if compute_checksum(payload) != checksum:
            checksum_valid = False
            checksum_error = "Неверный checksum"
        else:
            checksum_valid = True
            checksum_error = None

        result = {
            "Type": "ReturnResponse",
            "PacketLen": packet_len,
            "Command": hex(command),
            "VSN": vsn,
            "CheckSum": hex(checksum),
            "CheckSumValid": checksum_valid,
            "Token": f"0x{token:08X}",
            "Slot": slot,
            "ResultCode": result_code,
            "TerminalID": terminal_id,
            "CurrentSlotLockStatus": current_slot_lock_status,
            "AdjacentSlotLockStatus": adjacent_slot_lock_status,
            "Success": result_code == 1,
            "ReceivedAt": get_moscow_time().isoformat(),
            "RawPacket": data.hex()
        }
        if not checksum_valid:
            result["CheckSumError"] = checksum_error

        return result

    except Exception as e:
        return {
            "Type": "ReturnResponse",
            "Error": str(e),
            "RawPacket": data.hex(),
            "Size": len(data)
        }


def parse_return_power_bank_request(data: bytes) -> Dict[str, Any]:
    """Парсит запрос на возврат повербанка от станции"""
    try:
        if len(data) < 15:
            return {"error": "Недостаточно данных для парсинга запроса на возврат"}
        
        packet_len = struct.unpack('<H', data[0:2])[0]
        command = data[2]
        vsn = struct.unpack('<I', data[3:7])[0]
        checksum = data[7]
        token = struct.unpack('<I', data[8:12])[0]
        slot = data[12]
        
       
        calculated_checksum = compute_checksum(data[0:7] + data[8:])
        checksum_valid = calculated_checksum == checksum
        
        return {
            "Type": "ReturnRequest",
            "PacketLen": packet_len,
            "Command": f"0x{command:02X}",
            "VSN": vsn,
            "CheckSum": f"0x{checksum:02X}",
            "CheckSumValid": checksum_valid,
            "Token": f"0x{token:08X}",
            "Slot": slot,
            "ReceivedAt": get_moscow_time().isoformat(),
            "RawPacket": data.hex().upper()
        }
        
    except Exception as e:
        return {"error": f"Ошибка парсинга запроса на возврат: {str(e)}"}



def build_force_eject_request(secret_key: bytes, slot: int, vsn: int = 1):
    command = 0x80
    packet_len = 8
    payload = struct.pack(">B", slot)
    checksum = compute_checksum(payload)
    md5 = hashlib.md5(payload + secret_key).digest()
    token = md5[3] + md5[7]*256 + md5[11]*65536 + md5[15]*16777216
    header = struct.pack(">hBBBL", packet_len, command, vsn, checksum, token)
    packet = header + payload
    
   
    # Логирование происходит в server.py
    
    return packet






def build_query_iccid_request(secret_key: bytes, vsn: int = 1) -> bytes:
    """Создает запрос на получение ICCID SIM карты (команда 0x69)"""
    command = 0x69
    packet_len = 7  
    payload = b''  
    checksum = compute_checksum(payload)
    md5 = hashlib.md5(payload + secret_key).digest()
    token = md5[3] + md5[7]*256 + md5[11]*65536 + md5[15]*16777216
    header = struct.pack(">hBBBL", packet_len, command, vsn, checksum, token)
    packet = header + payload
    
    # Логируем пакет
    # Логирование происходит в server.py
    
    return packet


def parse_query_iccid_response(data: bytes) -> Dict[str, Any]:
    """Парсит ответ на запрос ICCID SIM карты (команда 0x69)"""
    try:
        if len(data) < 11:  
            raise ValueError("Слишком короткий пакет для ответа ICCID")
        
        packet_format = ">H B B B I H"
        packet_len, command, vsn, checksum, token, iccid_len = struct.unpack(packet_format, data[:11])
        
        if command != 0x69:
            raise ValueError(f"Неверная команда: {hex(command)}")
        
        
        if len(data) < 11 + iccid_len:
            raise ValueError(f"Недостаточно данных для ICCID. Ожидается {11 + iccid_len}, получено {len(data)}")
        
        # Извлекаем ICCID
        iccid_bytes = data[11:11 + iccid_len]
        iccid = iccid_bytes.decode('ascii', errors='ignore')
        
        # Проверяем checksum (payload = ICCIDLen + ICCID)
        payload = struct.pack(">H", iccid_len) + iccid_bytes
        if compute_checksum(payload) != checksum:
            raise ValueError("Неверный checksum")
        
        return {
            "Type": "QueryICCIDResponse",
            "PacketLen": packet_len,
            "Command": hex(command),
            "VSN": vsn,
            "CheckSum": hex(checksum),
            "Token": f"0x{token:08X}",
            "ICCIDLen": iccid_len,
            "ICCID": iccid,
            "CheckSumValid": True,
            "ReceivedAt": get_moscow_time().isoformat()
        }
        
    except Exception as e:
        return {
            "Type": "QueryICCIDResponse",
            "Error": f"Ошибка парсинга: {str(e)}",
            "RawPacket": data.hex(),
            "Size": len(data)
        }






def parse_slot_abnormal_report_request(data: bytes) -> Dict[str, Any]:
    """Парсит запрос отчета об аномалии слота (команда 0x83)"""
    if len(data) < 18:  
        raise ValueError("Слишком короткий пакет для отчета об аномалии слота")

    packet_format = ">H B B B I"
    packet_len, command, vsn, checksum, token = struct.unpack(packet_format, data[:9])
    
    if command != 0x83:
        raise ValueError(f"Неверная команда: {hex(command)}")
    event = data[9]
    
    slot_no = data[10]
    
    terminal_id = data[11:19]
    
    payload = struct.pack("BB8s", event, slot_no, terminal_id)
    if compute_checksum(payload) != checksum:
        raise ValueError("Неверный checksum")
    
    # Определяем тип события
    event_types = {
        1: "No unlock command",
        2: "Return detected but no power bank"
    }
    
    event_text = event_types.get(event, f"Unknown event type {event}")
    
    return {
        "Type": "SlotAbnormalReportRequest",
        "PacketLen": packet_len,
        "Command": hex(command),
        "VSN": vsn,
        "CheckSum": hex(checksum),
        "Token": f"0x{token:08X}",
        "Event": event,
        "EventText": event_text,
        "SlotNo": slot_no,
        "TerminalID": terminal_id.hex().upper(),
        "CheckSumValid": True,
        "ReceivedAt": get_moscow_time().isoformat()
    }


def build_slot_abnormal_report_response(secret_key: bytes, vsn: int = 1) -> bytes:
    """Создает ответ на отчет об аномалии слота (команда 0x83)"""
    command = 0x83
    packet_len = 7 
    payload = b''  
    checksum = compute_checksum(payload)
    md5 = hashlib.md5(payload + secret_key).digest()
    token = md5[3] + md5[7]*256 + md5[11]*65536 + md5[15]*16777216
    header = struct.pack(">hBBBL", packet_len, command, vsn, checksum, token)
    return header + payload


def parse_packet(data: bytes) -> Dict[str, Any]:
    """Универсальный парсер пакетов"""
    if len(data) < 3:
        return {
            "Type": "Unknown",
            "Error": "Пакет слишком короткий",
            "Size": len(data),
            "RawPacket": data.hex()
        }
    
    command = data[2]
    
    # Логируем входящий пакет
    command_names = {
        0x60: "Login", 0x61: "Heartbeat", 0x63: "SetServerAddress",
        0x64: "QueryInventory", 0x65: "BorrowPowerBank", 0x66: "ReturnPowerBank",
        0x67: "RestartCabinet", 0x69: "QueryICCID", 0x6A: "QueryServerAddress",
        0x70: "SetVoiceVolume", 0x77: "QueryVoiceVolume", 0x80: "ForceEject",
        0x83: "SlotAbnormalReport"
    }
    command_name = command_names.get(command, f"Unknown(0x{command:02X})")
    # Убираем логирование отсюда - оно должно быть в обработчиках
    
    try:
        if command == 0x60:  # Login
            return parse_login_packet(data)
        elif command == 0x61:  # Heartbeat
            return parse_heartbeat_packet(data)
        elif command == 0x65:  # Borrow Power Bank
            if len(data) >= 12:
                return parse_borrow_response(data)
            else:
                return parse_borrow_request(data)
        elif command == 0x66:  # Return Power Bank
            if len(data) >= 21:
                return parse_return_response(data)
            else:
                return parse_return_power_bank_request(data)
        elif command == 0x69:  # Query ICCID
            return parse_query_iccid_response(data)
        elif command == 0x80:  # Force Eject
            return parse_force_eject_response(data)
        elif command == 0x83:  # Slot Abnormal Report
            return parse_slot_abnormal_report_request(data)
        elif command == 0x67:  # Restart Cabinet
            return parse_restart_cabinet_response(data)
        elif command == 0x64:  # Query Inventory
            return parse_query_inventory_response(data)
        elif command == 0x77:  # Query Voice Volume
            return parse_query_voice_volume_response(data)
        elif command == 0x70:  # Set Voice Volume
            return parse_set_voice_volume_response(data)
        elif command == 0x63:  # Set Server Address
            return parse_set_server_address_response(data)
        elif command == 0x6A:  # Query Server Address
            return parse_query_server_address_response(data)
        else:
            return {
                "Type": "Unknown",
                "Command": f"0x{command:02X}",
                "Size": len(data),
                "RawPacket": data.hex()
            }
    except Exception as e:
        return {
            "Type": "ParseError",
            "Command": f"0x{command:02X}",
            "Error": str(e),
            "Size": len(data),
            "RawPacket": data.hex()
        }


def parse_heartbeat_packet(data: bytes) -> Dict[str, Any]:
    """Парсит пакет heartbeat"""
    try:
        if len(data) < 9:
            raise ValueError("Пакет слишком короткий для heartbeat")
        
        packet_format = ">H B B B I"
        packet_len, command, vsn, checksum, token = struct.unpack(packet_format, data[:9])  
        
        
        payload = b''
        if compute_checksum(payload) != checksum:
            raise ValueError("Неверный checksum")
        
        return {
            "Type": "Heartbeat",
            "PacketLen": packet_len,
            "Command": hex(command),
            "VSN": vsn,
            "CheckSum": hex(checksum),
            "Token": f"0x{token:08X}",
            "CheckSumValid": True,
            "ReceivedAt": get_moscow_time().isoformat()
        }
    except Exception as e:
        return {
            "Type": "Heartbeat",
            "Error": f"Ошибка парсинга: {str(e)}",
            "RawPacket": data.hex(),
            "Size": len(data)
        }


def parse_force_eject_response(data: bytes) -> Dict[str, Any]:
    """Парсит ответ на принудительное извлечение (команда 0x80)"""
    try:
        if len(data) < 9:
            raise ValueError("Пакет слишком короткий для ответа принудительного извлечения")
        
        
        packet_format = ">H B B B I"
        packet_len, command, vsn, checksum, token = struct.unpack(packet_format, data[:9])#2+1+1+1+4=9
        
        if command != 0x80:
            raise ValueError(f"Неверная команда: {hex(command)}")
        
        
        result = {
            "Type": "ForceEjectResponse",
            "PacketLen": packet_len,
            "Command": hex(command),
            "VSN": vsn,
            "CheckSum": hex(checksum),
            "Token": f"0x{token:08X}",
            "CheckSumValid": True,
            "Success": True,
            "ReceivedAt": get_moscow_time().isoformat()
        }
        
        
        if len(data) > 9:
            try:
                
                slot = data[9]
                result_code = data[10]
                terminal_id_bytes = data[11:19]
                terminal_id = parse_terminal_id(terminal_id_bytes)
                
                result.update({
                    "Slot": slot,
                    "TerminalID": terminal_id
                })
                
                
                payload = struct.pack("BB8s", slot, result_code, terminal_id_bytes)
                if compute_checksum(payload) != checksum:
                    result["CheckSumValid"] = False
                   
            except Exception as parse_error:
                result["ParseWarning"] = f"Ошибка парсинга дополнительных данных: {parse_error}"
        else:
            # Проверяем checksum (payload пустой для ответа)
            payload = b''
            if compute_checksum(payload) != checksum:
                result["CheckSumValid"] = False
                result["CheckSumError"] = "Неверный checksum"
        
        return result
        
    except Exception as e:
        return {
            "Type": "ForceEjectResponse",
            "Error": f"Ошибка парсинга: {str(e)}",
            "RawPacket": data.hex(),
            "Size": len(data)
        }


def build_restart_cabinet_request(secret_key: bytes, vsn: int = 1) -> bytes:
    """Создает запрос на перезагрузку кабинета (команда 0x67)"""
    command = 0x67
    packet_len = 7 
    payload = b''  
    checksum = compute_checksum(payload)
    md5 = hashlib.md5(payload + secret_key).digest()
    token = md5[3] + md5[7]*256 + md5[11]*65536 + md5[15]*16777216
    header = struct.pack(">hBBBL", packet_len, command, vsn, checksum, token)
    packet = header + payload
    
    # Логируем пакет
    # Логирование происходит в server.py
    
    return packet


def parse_restart_cabinet_response(data: bytes) -> Dict[str, Any]:
    """Парсит ответ на запрос перезагрузки кабинета (команда 0x67)"""
    try:
        if len(data) < 9:
            raise ValueError("Слишком короткий пакет для ответа перезагрузки")
        
       
        packet_format = ">H B B B I"
        packet_len, command, vsn, checksum, token = struct.unpack(packet_format, data[:9])
        
        if command != 0x67:
            raise ValueError(f"Неверная команда: {hex(command)}")
        
        
        payload = b''
        if compute_checksum(payload) != checksum:
            raise ValueError("Неверный checksum")
        
        return {
            "Type": "RestartCabinetResponse",
            "PacketLen": packet_len,
            "Command": hex(command),
            "VSN": vsn,
            "CheckSum": hex(checksum),
            "Token": f"0x{token:08X}",
            "CheckSumValid": True,
            "Success": True,
            "ReceivedAt": get_moscow_time().isoformat(),
            "RawPacket": data.hex()
        }
        
    except Exception as e:
        return {
            "Type": "RestartCabinetResponse",
            "Error": f"Ошибка парсинга: {str(e)}",
            "RawPacket": data.hex(),
            "Size": len(data)
        }


def build_query_inventory_request(secret_key: bytes, vsn: int = 1, station_box_id: str = "unknown") -> bytes:
    """Создает запрос на получение инвентаря кабинета (команда 0x64)"""
    command = 0x64
    packet_len = 7 
    payload = b''  
    checksum = compute_checksum(payload)
    md5_hash = hashlib.md5(payload + secret_key).digest()
    token_bytes = md5_hash[15:16] + md5_hash[11:12] + md5_hash[7:8] + md5_hash[3:4]
    header = struct.pack(">HBBB", packet_len, command, vsn, checksum) + token_bytes
    packet = header + payload
    
    # Логируем пакет
    # Логирование происходит в server.py
    
    return packet


def parse_query_inventory_response(data: bytes) -> Dict[str, Any]:
    """Парсит ответ на запрос инвентаря кабинета (команда 0x64)"""
    try:
        if len(data) < 10:  
            raise ValueError("Слишком короткий пакет для ответа инвентаря")
        
       
        packet_format = ">H B B B I"
        packet_len, command, vsn, checksum, token = struct.unpack(packet_format, data[:9])
        
        if command != 0x64:
            raise ValueError(f"Неверная команда: {hex(command)}")
        
       
        slots_num = data[9]
        remain_num = data[10]
        
       
        slots = []
        offset = 11
        
        
        slot_format = ">B 8s B H H b B B"
        slot_size = struct.calcsize(slot_format)
        
        while offset + slot_size <= len(data):
            slot_bytes = data[offset:offset + slot_size]
            slot_number, terminal_id_bytes, level, voltage, current, temperature, status, soh = struct.unpack(
                slot_format, slot_bytes
            )
            
            terminal_id = parse_terminal_id(terminal_id_bytes)
            
            
            status_bits = {
                "InsertionSwitch": (status >> 7) & 1,
                "LockStatus": (status >> 6) & 1,
                "PowerBankError": (status >> 5) & 1,
                "ChargingSwitch": (status >> 4) & 1,
                "ChargingStatus": (status >> 3) & 1,
                "TypeCError": (status >> 2) & 1,
                "LightningError": (status >> 1) & 1,
                "MicroUSBError": status & 1
            }
            
            slots.append({
                "Slot": slot_number,
                "TerminalID": terminal_id,
                "Level": level,
                "Voltage": voltage,
                "Current": current,
                "Temperature": temperature,
                "Status": status_bits,
                "SOH": soh
            })
            
            offset += slot_size
        
       
        payload = data[9:offset]  
        if compute_checksum(payload) != checksum:
            raise ValueError("Неверный checksum")
        
        return {
            "Type": "QueryInventoryResponse",
            "PacketLen": packet_len,
            "Command": hex(command),
            "VSN": vsn,
            "CheckSum": hex(checksum),
            "Token": f"0x{token:08X}",
            "SlotsNum": slots_num,
            "RemainNum": remain_num,
            "Slots": slots,
            "CheckSumValid": True,
            "ReceivedAt": get_moscow_time().isoformat(),
            "RawPacket": data.hex()
        }
        
    except Exception as e:
        return {
            "Type": "QueryInventoryResponse",
            "Error": f"Ошибка парсинга: {str(e)}",
            "RawPacket": data.hex(),
            "Size": len(data)
        }


def build_query_voice_volume_request(secret_key: bytes, vsn: int = 1) -> bytes:
    """Создает запрос на получение уровня громкости голосового вещания (команда 0x77)"""
    command = 0x77
    packet_len = 7 
    payload = b''  
    checksum = compute_checksum(payload)
    md5 = hashlib.md5(payload + secret_key).digest()
    token = md5[3] + md5[7]*256 + md5[11]*65536 + md5[15]*16777216
    header = struct.pack(">hBBBL", packet_len, command, vsn, checksum, token)
    packet = header + payload
    
    # Логируем пакет
    # Логирование происходит в server.py
    
    return packet


def parse_query_voice_volume_response(data: bytes) -> Dict[str, Any]:
    """Парсит ответ на запрос уровня громкости голосового вещания (команда 0x77)"""
    try:
        if len(data) < 9:  
            raise ValueError("Слишком короткий пакет для ответа громкости")
        
        
        packet_format = ">H B B B I"
        packet_len, command, vsn, checksum, token = struct.unpack(packet_format, data[:9])
        
        if command != 0x77:
            raise ValueError(f"Неверная команда: {hex(command)}")
        
        # Парсим уровень громкости
        volume_level = data[9]
        
       
        payload = data[9:10]  
        if compute_checksum(payload) != checksum:
            raise ValueError("Неверный checksum")
        
        return {
            "Type": "QueryVoiceVolumeResponse",
            "PacketLen": packet_len,
            "Command": hex(command),
            "VSN": vsn,
            "CheckSum": hex(checksum),
            "Token": f"0x{token:08X}",
            "VolumeLevel": volume_level,
            "CheckSumValid": True,
            "ReceivedAt": get_moscow_time().isoformat(),
            "RawPacket": data.hex()
        }
        
    except Exception as e:
        return {
            "Type": "QueryVoiceVolumeResponse",
            "Error": f"Ошибка парсинга: {str(e)}",
            "RawPacket": data.hex(),
            "Size": len(data)
        }


def build_set_voice_volume_request(secret_key: bytes, volume_level: int, vsn: int = 1) -> bytes:
    """Создает запрос на установку уровня громкости голосового вещания (команда 0x70)"""
    command = 0x70
    packet_len = 8 
    payload = struct.pack(">B", volume_level)  
    checksum = compute_checksum(payload)
    md5 = hashlib.md5(payload + secret_key).digest()
    token = md5[3] + md5[7]*256 + md5[11]*65536 + md5[15]*16777216
    header = struct.pack(">hBBBL", packet_len, command, vsn, checksum, token)
    packet = header + payload
    
    # Логируем пакет
    # Логирование происходит в server.py
    
    return packet


def parse_set_voice_volume_response(data: bytes) -> Dict[str, Any]:
    """Парсит ответ на установку уровня громкости голосового вещания (команда 0x70)"""
    try:
        if len(data) < 9:  
            raise ValueError("Слишком короткий пакет для ответа установки громкости")
        
       
        packet_format = ">H B B B I"
        packet_len, command, vsn, checksum, token = struct.unpack(packet_format, data[:9])
        
        if command != 0x70:
            raise ValueError(f"Неверная команда: {hex(command)}")
        
       
        payload = b''
        if compute_checksum(payload) != checksum:
            raise ValueError("Неверный checksum")
        
        return {
            "Type": "SetVoiceVolumeResponse",
            "PacketLen": packet_len,
            "Command": hex(command),
            "VSN": vsn,
            "CheckSum": hex(checksum),
            "Token": f"0x{token:08X}",
            "CheckSumValid": True,
            "Success": True,
            "ReceivedAt": get_moscow_time().isoformat(),
            "RawPacket": data.hex()
        }
        
    except Exception as e:
        return {
            "Type": "SetVoiceVolumeResponse",
            "Error": f"Ошибка парсинга: {str(e)}",
            "RawPacket": data.hex(),
            "Size": len(data)
        }


def build_set_server_address_request(secret_key: bytes, server_address: str, server_port: str, heartbeat_interval: int = 30, vsn: int = 1) -> bytes:
    """Создает запрос на установку адреса сервера (команда 0x63)"""
    command = 0x63
    
    
    address_bytes = server_address.encode('utf-8') + b'\x00'
    port_bytes = server_port.encode('utf-8') + b'\x00'  

    
    payload = struct.pack(">H", len(address_bytes))  # AddressLen 
    payload += address_bytes  
    payload += struct.pack(">H", len(port_bytes))  # PortLen 
    payload += port_bytes  
    payload += struct.pack(">B", heartbeat_interval)  # Heartbeat
    
 
    packet_len = 8 + len(payload)  
    
    # Вычисляем checksum и token
    checksum = compute_checksum(payload)
    md5 = hashlib.md5(payload + secret_key).digest()
    token = md5[3] + md5[7]*256 + md5[11]*65536 + md5[15]*16777216
    
   
    header = struct.pack(">HBBBI", packet_len, command, vsn, checksum, token)
    packet = header + payload
    
    # Логируем пакет
    # Логирование происходит в server.py
    
    return packet


def parse_set_server_address_response(data: bytes) -> Dict[str, Any]:
    """Парсит ответ на установку адреса сервера (команда 0x63)"""
    try:
        if len(data) < 9:  
            raise ValueError("Слишком короткий пакет для ответа установки адреса сервера")
        
        
        packet_format = ">H B B B I"
        packet_len, command, vsn, checksum, token = struct.unpack(packet_format, data[:9])
        
        if command != 0x63:
            raise ValueError(f"Неверная команда: {hex(command)}")
        
       
        payload = b''
        if compute_checksum(payload) != checksum:
            raise ValueError("Неверный checksum")
        
        return {
            "Type": "SetServerAddressResponse",
            "PacketLen": packet_len,
            "Command": hex(command),
            "VSN": vsn,
            "CheckSum": hex(checksum),
            "Token": f"0x{token:08X}",
            "CheckSumValid": True,
            "Success": True,
            "ReceivedAt": get_moscow_time().isoformat(),
            "RawPacket": data.hex()
        }
        
    except Exception as e:
        return {
            "Type": "SetServerAddressResponse",
            "Error": f"Ошибка парсинга: {str(e)}",
            "RawPacket": data.hex(),
            "Size": len(data)
        }


def build_query_server_address_request(secret_key: bytes, vsn: int = 1) -> bytes:
    """Создает запрос на получение адреса сервера (команда 0x6A)"""
    command = 0x6A
    packet_len = 7 
    payload = b''  
    checksum = compute_checksum(payload)
    md5 = hashlib.md5(payload + secret_key).digest()
    token = md5[3] + md5[7]*256 + md5[11]*65536 + md5[15]*16777216
    header = struct.pack(">hBBBL", packet_len, command, vsn, checksum, token)
    packet = header + payload
    
    # Логируем пакет
    # Логирование происходит в server.py
    
    return packet


def parse_query_server_address_response(data: bytes) -> Dict[str, Any]:
    """
    Парсит ответ станции на запрос адреса сервера (команда 0x6A).
    """
    try:
        if len(data) < 9:
            raise ValueError("Пакет слишком короткий для ответа QueryServerAddress")

        
        packet_format = ">H B B B I"
        packet_len, command, vsn, checksum, token = struct.unpack(packet_format, data[:9])

        if command != 0x6A:
            raise ValueError(f"Неверная команда: {hex(command)}")

        payload = data[9:]

       
        if compute_checksum(payload) != checksum:
            raise ValueError("Неверный checksum")

       
        if len(payload) < 2:
            raise ValueError("Нет данных для AddressLen")
        address_len = struct.unpack(">H", payload[:2])[0]

        if len(payload) < 2 + address_len:
            raise ValueError("Недостаточно данных для адреса")
        address_bytes = payload[2:2 + address_len]
        address = address_bytes.decode("ascii", errors="ignore")

       
        port_offset = 2 + address_len
        if len(payload) < port_offset + 2:
            raise ValueError("Нет данных для PortLen")
        port_len = struct.unpack(">H", payload[port_offset:port_offset + 2])[0]

        if len(payload) < port_offset + 2 + port_len:
            raise ValueError("Недостаточно данных для портов")
        ports_bytes = payload[port_offset + 2:port_offset + 2 + port_len]
        ports = ports_bytes.decode("ascii", errors="ignore")

       
        heartbeat_offset = port_offset + 2 + port_len
        if len(payload) < heartbeat_offset + 1:
            raise ValueError("Нет данных для Heartbeat")
        heartbeat = payload[heartbeat_offset]

        return {
            "Type": "QueryServerAddressResponse",
            "PacketLen": packet_len,
            "Command": hex(command),
            "VSN": vsn,
            "CheckSum": hex(checksum),
            "CheckSumValid": True,
            "Token": f"0x{token:08X}",
            "AddressLen": address_len,
            "Address": address,
            "PortLen": port_len,
            "Ports": ports,
            "Heartbeat": heartbeat,
            "ReceivedAt": get_moscow_time().isoformat(),
            "RawPacket": data.hex()
        }

    except Exception as e:
        return {
            "Type": "QueryServerAddressResponse",
            "Error": str(e),
            "RawPacket": data.hex(),
            "Size": len(data)
        }

