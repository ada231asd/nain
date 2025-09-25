"""
Утилиты для работы с пакетами
"""
import struct
import hashlib
import random
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional
from config.settings import MAX_PACKET_SIZE, PROTOCOL_COMMAND_RANGE, MAX_SUSPICIOUS_PACKETS

def log_packet(data: bytes, direction: str, station_box_id: str = "unknown", command_name: str = "Unknown"):
    """Логирование TCP пакета через специализированный логгер"""
    try:
        from utils.tcp_packet_logger import log_tcp_packet
        
        hex_data = data.hex().upper()
        size = len(data)
        
        # Определяем команду
        command_hex = "Unknown"
        if size >= 3:
            command_hex = f"0x{data[2]:02X}"
        
        # Логируем через TCP логгер
        log_tcp_packet(
            direction=direction,
            packet_type=command_name,
            station_id=station_box_id,
            packet_size=size,
            command=command_hex,
            packet_data=hex_data
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
        
        # Проверка длины пакета - станция не всегда корректно указывает длину
        packet_len = struct.unpack('>H', data[:2])[0]
        # Допускаем расхождение, но не критичное (станция может ошибаться в длине)
        if abs(packet_len - len(data)) > 10:  # Допускаем расхождение до 10 байт
            return False, f"Критичное несоответствие длины: заявлено {packet_len}, фактически {len(data)}"
        
        # Проверка структуры пакета согласно протоколу
        if len(data) >= 9:
            vsn = data[3]
            checksum = data[4]
            token = struct.unpack('>I', data[5:9])[0]
            payload = data[9:]  # Payload начинается после токена
            
            
            if vsn < 1 or vsn > 10:
                return False, f"Подозрительный VSN: {vsn}"
            
            # Проверяем checksum для payload (если есть)
            if payload and len(payload) > 0:
                computed_checksum = compute_checksum(payload)
                if computed_checksum != checksum:
                    return False, f"Неверный checksum: ожидался 0x{computed_checksum:02X}, получен 0x{checksum:02X}"
            
            # Проверяем токен (должен быть ненулевым для большинства команд)
            if token == 0 and command not in [0x60]:  # Login может иметь нулевой токен
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
        
        # Также логируем через обычный логгер
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
    """
    Генерирует токен по протоколу:
    md5_hash = MD5(payload + SecretKey)
    token = bytes(md5_hash[15:16] + md5_hash[11:12] + md5_hash[7:8] + md5_hash[3:4])
    """
    import hashlib
    
    # Создаем MD5 хеш от payload + secret_key
    combined = payload + secret_key.encode('utf-8')
    md5_hash = hashlib.md5(combined).digest()
    
    # Извлекаем байты по позициям 16, 12, 8, 4 (индексы 15, 11, 7, 3)
    token = bytes([
        md5_hash[15],  # Позиция 16
        md5_hash[11],  # Позиция 12  
        md5_hash[7],   # Позиция 8
        md5_hash[3]    # Позиция 4
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
    timestamp = int(datetime.now(timezone.utc).timestamp())
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
    
    # Логируем пакет
    log_packet(packet, "OUTGOING", "unknown", "HeartbeatResponse")
    
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
    log_packet(packet, "OUTGOING", "unknown", "BorrowPowerBank")
    
    return packet

def build_return_power_bank_response(slot: int, result: int, terminal_id: bytes, level: int, voltage: int, current: int, temperature: int, status: int, soh: int, vsn: int, token: int):
    command = 0x66
    payload = struct.pack(">BB8sBHHBBB", slot, result, terminal_id, level, voltage, current, temperature, status, soh)
    checksum = compute_checksum(payload)
    header = struct.pack(">HBBBL", len(payload)+7, command, vsn, checksum, token)
    packet = header + payload
    
    # Логируем пакет
    log_packet(packet, "OUTGOING", "unknown", "ReturnPowerBank")
    
    return packet


def parse_borrow_request(data: bytes) -> Dict[str, Any]:
    """Парсит запрос на выдачу повербанка (команда 0x65)"""
    if len(data) < 9:
        raise ValueError("Слишком короткий пакет для запроса выдачи")
    
    # Парсим заголовок (PacketLen не входит в заголовок)
    packet_format = ">H B B B I"
    packet_len, command, vsn, checksum, token = struct.unpack(packet_format, data[:9])
    
    if command != 0x65:
        raise ValueError(f"Неверная команда: {hex(command)}")
    
    # Парсим слот (1 байт)
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
        if len(data) < 9:
            raise ValueError("Слишком короткий пакет для ответа выдачи")
        
        # Парсим заголовок согласно протоколу:
        # PacketLen (2) + Command (1) + VSN (1) + CheckSum (1) + Token (4) = 9 байт
        packet_format = ">H B B B I"
        packet_len, command, vsn, checksum, token = struct.unpack(packet_format, data[:9])
        
        if command != 0x65:
            raise ValueError(f"Неверная команда: {hex(command)}")
        
        # Если есть дополнительные данные, парсим их
        result = {
            "Type": "BorrowResponse",
            "PacketLen": packet_len,
            "Command": hex(command),
            "VSN": vsn,
            "CheckSum": hex(checksum),
            "Token": f"0x{token:08X}",
            "CheckSumValid": True,
            "Success": True,
            "ReceivedAt": datetime.now(timezone.utc).isoformat(),
            "RawPacket": data.hex()
        }
        
        # Если есть дополнительные данные (слот и terminal_id)
        if len(data) > 8:
            try:
                # Парсим слот и terminal_id
                slot = data[8]
                terminal_id_bytes = data[9:17]
                terminal_id = parse_terminal_id(terminal_id_bytes)
                
                result.update({
                    "Slot": slot,
                    "TerminalID": terminal_id
                })
                
                # Проверяем checksum с учетом дополнительных данных
                payload = struct.pack("B8s", slot, terminal_id_bytes)
                if compute_checksum(payload) != checksum:
                    result["CheckSumValid"] = False
                    result["CheckSumError"] = "Неверный checksum с дополнительными данными"
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
            "Type": "BorrowResponse",
            "Error": f"Ошибка парсинга: {str(e)}",
            "RawPacket": data.hex(),
            "Size": len(data)
        }


def parse_return_power_bank_request(data: bytes) -> Dict[str, Any]:
    """Парсит запрос на возврат повербанка (команда 0x66)"""
    if len(data) < 26:
        raise ValueError("Пакет слишком короткий для Return Power Bank Request")
    
    packet_len, command, vsn, checksum = struct.unpack(">HBBB", data[:5])
    token = struct.unpack(">I", data[5:9])[0]
    slot = data[9]
    terminal_id_bytes = data[10:18]
    terminal_id = parse_terminal_id(terminal_id_bytes)
    level = data[18]
    voltage, current = struct.unpack(">HH", data[19:23])
    temperature = data[23]
    status = data[24]
    soh = data[25]
    
    # Парсим статус биты
    status_bits = {
        "LockStatus": (status >> 7) & 1,
        "MicroUSBError": (status >> 2) & 1,
        "TypeCError": (status >> 1) & 1,
        "LightningError": status & 1
    }
    
    # Проверяем checksum
    payload = data[9:26]  # slot + terminal_id + level + voltage + current + temperature + status + soh
    if compute_checksum(payload) != checksum:
        raise ValueError("Неверный checksum")
    
    return {
        "Type": "ReturnPowerBankRequest",
        "PacketLen": packet_len,
        "Command": hex(command),
        "VSN": vsn,
        "CheckSum": hex(checksum),
        "Token": f"0x{token:08X}",
        "Slot": slot,
        "TerminalID": terminal_id,
        "Level": level,
        "Voltage": voltage,
        "Current": current,
        "Temperature": temperature,
        "Status": status_bits,
        "SOH": soh,
        "RawPacket": data.hex(),
        "ReceivedAt": datetime.now(timezone.utc).isoformat(),
        "CheckSumValid": True
    }


def build_force_eject_request(secret_key: bytes, slot: int, vsn: int = 1):
    command = 0x80
    packet_len = 8
    payload = struct.pack(">B", slot)
    checksum = compute_checksum(payload)
    md5 = hashlib.md5(payload + secret_key).digest()
    token = md5[3] + md5[7]*256 + md5[11]*65536 + md5[15]*16777216
    header = struct.pack(">hBBBL", packet_len, command, vsn, checksum, token)
    packet = header + payload
    
    # Логируем пакет
    log_packet(packet, "OUTGOING", "unknown", "ForceEject")
    
    return packet






def build_query_iccid_request(secret_key: bytes, vsn: int = 1) -> bytes:
    """Создает запрос на получение ICCID SIM карты (команда 0x69)"""
    command = 0x69
    packet_len = 7  # Только заголовок, payload пустой
    payload = b''  # Пустой payload для запроса ICCID
    checksum = compute_checksum(payload)
    md5 = hashlib.md5(payload + secret_key).digest()
    token = md5[3] + md5[7]*256 + md5[11]*65536 + md5[15]*16777216
    header = struct.pack(">hBBBL", packet_len, command, vsn, checksum, token)
    packet = header + payload
    
    # Логируем пакет
    log_packet(packet, "OUTGOING", "unknown", "QueryICCID")
    
    return packet


def parse_query_iccid_response(data: bytes) -> Dict[str, Any]:
    """Парсит ответ на запрос ICCID SIM карты (команда 0x69)"""
    try:
        if len(data) < 11:  # Минимум 9 байт заголовка + 2 байта ICCIDLen
            raise ValueError("Слишком короткий пакет для ответа ICCID")
        
        # Парсим заголовок согласно протоколу:
        # PacketLen (2) + Command (1) + VSN (1) + CheckSum (1) + Token (4) + ICCIDLen (2) = 11 байт
        packet_format = ">H B B B I H"
        packet_len, command, vsn, checksum, token, iccid_len = struct.unpack(packet_format, data[:11])
        
        if command != 0x69:
            raise ValueError(f"Неверная команда: {hex(command)}")
        
        # Проверяем, что пакет содержит достаточно данных
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
            "ReceivedAt": datetime.now(timezone.utc).isoformat()
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
    if len(data) < 18:  # Минимум 8 байт заголовка + 1 байт Event + 1 байт SlotNo + 8 байт TerminalID
        raise ValueError("Слишком короткий пакет для отчета об аномалии слота")
    
    # Парсим заголовок (9 байт: 2+1+1+1+4)
    packet_format = ">H B B B I"
    packet_len, command, vsn, checksum, token = struct.unpack(packet_format, data[:9])
    
    if command != 0x83:
        raise ValueError(f"Неверная команда: {hex(command)}")
    
    # Парсим Event
    event = data[9]
    
    # Парсим SlotNo
    slot_no = data[10]
    
    # Парсим TerminalID (8 байт)
    terminal_id = data[11:19]
    
    # Проверяем checksum
    payload = struct.pack("BB8s", event, slot_no, terminal_id)
    if compute_checksum(payload) != checksum:
        raise ValueError("Неверный checksum")
    
    # Определяем тип события
    event_types = {
        1: "No unlock command",
        2: "Return detected but no power bank",
        3: "Power bank malfunction",
        4: "Slot jammed",
        5: "Communication error"
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
        "ReceivedAt": datetime.now(timezone.utc).isoformat()
    }


def build_slot_abnormal_report_response(secret_key: bytes, vsn: int = 1) -> bytes:
    """Создает ответ на отчет об аномалии слота (команда 0x83)"""
    command = 0x83
    packet_len = 7  # Только заголовок, payload пустой
    payload = b''  # Пустой payload для ответа
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
    log_packet(data, "INCOMING", "unknown", command_name)
    
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
        packet_len, command, vsn, checksum, token = struct.unpack(packet_format, data[:9])  # 2+1+1+1+4=9
        
        # Проверяем checksum (payload пустой для heartbeat)
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
            "ReceivedAt": datetime.now(timezone.utc).isoformat()
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
        
        # Парсим заголовок
        packet_format = ">H B B B I"
        packet_len, command, vsn, checksum, token = struct.unpack(packet_format, data[:9])#2+1+1+1+4=9
        
        if command != 0x80:
            raise ValueError(f"Неверная команда: {hex(command)}")
        
        # Если есть дополнительные данные, парсим их
        result = {
            "Type": "ForceEjectResponse",
            "PacketLen": packet_len,
            "Command": hex(command),
            "VSN": vsn,
            "CheckSum": hex(checksum),
            "Token": f"0x{token:08X}",
            "CheckSumValid": True,
            "Success": True,
            "ReceivedAt": datetime.now(timezone.utc).isoformat()
        }
        
        # Если есть дополнительные данные (слот и terminal_id)
        if len(data) > 9:
            try:
                # Парсим слот и terminal_id
                slot = data[9]
                result_code = data[10]
                terminal_id_bytes = data[11:19]
                terminal_id = parse_terminal_id(terminal_id_bytes)
                
                result.update({
                    "Slot": slot,
                    "TerminalID": terminal_id
                })
                
                # Проверяем checksum с учетом дополнительных данных
                payload = struct.pack("BB8s", slot, result_code, terminal_id_bytes)
                if compute_checksum(payload) != checksum:
                    result["CheckSumValid"] = False
                    result["CheckSumError"] = "Неверный checksum с дополнительными данными"
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
    packet_len = 7  # Только заголовок, payload пустой
    payload = b''  # Пустой payload для запроса перезагрузки
    checksum = compute_checksum(payload)
    md5 = hashlib.md5(payload + secret_key).digest()
    token = md5[3] + md5[7]*256 + md5[11]*65536 + md5[15]*16777216
    header = struct.pack(">hBBBL", packet_len, command, vsn, checksum, token)
    packet = header + payload
    
    # Логируем пакет
    log_packet(packet, "OUTGOING", "unknown", "RestartCabinet")
    
    return packet


def parse_restart_cabinet_response(data: bytes) -> Dict[str, Any]:
    """Парсит ответ на запрос перезагрузки кабинета (команда 0x67)"""
    try:
        if len(data) < 9:
            raise ValueError("Слишком короткий пакет для ответа перезагрузки")
        
        # Парсим заголовок согласно протоколу:
        # PacketLen (2) + Command (1) + VSN (1) + CheckSum (1) + Token (4) = 9 байт
        packet_format = ">H B B B I"
        packet_len, command, vsn, checksum, token = struct.unpack(packet_format, data[:9])
        
        if command != 0x67:
            raise ValueError(f"Неверная команда: {hex(command)}")
        
        # Проверяем checksum (payload пустой для ответа)
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
            "ReceivedAt": datetime.now(timezone.utc).isoformat(),
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
    packet_len = 7  # Command + VSN + CheckSum + Token (payload отсутствует)
    payload = b''  # Пустой payload для запроса инвентаря
    checksum = compute_checksum(payload)
    md5_hash = hashlib.md5(payload + secret_key).digest()
    token_bytes = md5_hash[15:16] + md5_hash[11:12] + md5_hash[7:8] + md5_hash[3:4]
    header = struct.pack(">HBBB", packet_len, command, vsn, checksum) + token_bytes
    packet = header + payload
    
    # Логируем пакет
    log_packet(packet, "OUTGOING", station_box_id, "QueryInventory")
    
    return packet


def parse_query_inventory_response(data: bytes) -> Dict[str, Any]:
    """Парсит ответ на запрос инвентаря кабинета (команда 0x64)"""
    try:
        if len(data) < 10:  
            raise ValueError("Слишком короткий пакет для ответа инвентаря")
        
        # Парсим заголовок (9 байт: 2+1+1+1+4)
        packet_format = ">H B B B I"
        packet_len, command, vsn, checksum, token = struct.unpack(packet_format, data[:9])
        
        if command != 0x64:
            raise ValueError(f"Неверная команда: {hex(command)}")
        
        # Парсим SlotsNum и RemainNum
        slots_num = data[9]
        remain_num = data[10]
        
        # Парсим слоты (если есть)
        slots = []
        offset = 11
        
        # Формат слота: Slot (1) + TerminalID (8) + Level (1) + Voltage (2) + Current (2) + Temperature (1) + Status (1) + SOH (1) = 17 байт
        slot_format = ">B 8s B H H b B B"
        slot_size = struct.calcsize(slot_format)
        
        while offset + slot_size <= len(data):
            slot_bytes = data[offset:offset + slot_size]
            slot_number, terminal_id_bytes, level, voltage, current, temperature, status, soh = struct.unpack(
                slot_format, slot_bytes
            )
            
            terminal_id = parse_terminal_id(terminal_id_bytes)
            
            # Парсим статус биты
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
        
        # Проверяем checksum
        payload = data[9:offset]  # SlotsNum + RemainNum + все слоты (начинаем с 9-го байта, после заголовка)
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
            "ReceivedAt": datetime.now(timezone.utc).isoformat(),
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
    packet_len = 7  # Только заголовок, payload пустой
    payload = b''  # Пустой payload для запроса громкости
    checksum = compute_checksum(payload)
    md5 = hashlib.md5(payload + secret_key).digest()
    token = md5[3] + md5[7]*256 + md5[11]*65536 + md5[15]*16777216
    header = struct.pack(">hBBBL", packet_len, command, vsn, checksum, token)
    packet = header + payload
    
    # Логируем пакет
    log_packet(packet, "OUTGOING", "unknown", "QueryVoiceVolume")
    
    return packet


def parse_query_voice_volume_response(data: bytes) -> Dict[str, Any]:
    """Парсит ответ на запрос уровня громкости голосового вещания (команда 0x77)"""
    try:
        if len(data) < 9:  # Минимум 8 байт заголовка + 1 байт Lvl
            raise ValueError("Слишком короткий пакет для ответа громкости")
        
        # Парсим заголовок (9 байт: 2+1+1+1+4)
        packet_format = ">H B B B I"
        packet_len, command, vsn, checksum, token = struct.unpack(packet_format, data[:9])
        
        if command != 0x77:
            raise ValueError(f"Неверная команда: {hex(command)}")
        
        # Парсим уровень громкости
        volume_level = data[9]
        
        # Проверяем checksum
        payload = data[9:10]  # Только Lvl
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
            "ReceivedAt": datetime.now(timezone.utc).isoformat(),
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
    packet_len = 8  # Заголовок + Lvl
    payload = struct.pack(">B", volume_level)  # Lvl (1 байт)
    checksum = compute_checksum(payload)
    md5 = hashlib.md5(payload + secret_key).digest()
    token = md5[3] + md5[7]*256 + md5[11]*65536 + md5[15]*16777216
    header = struct.pack(">hBBBL", packet_len, command, vsn, checksum, token)
    packet = header + payload
    
    # Логируем пакет
    log_packet(packet, "OUTGOING", "unknown", "SetVoiceVolume")
    
    return packet


def parse_set_voice_volume_response(data: bytes) -> Dict[str, Any]:
    """Парсит ответ на установку уровня громкости голосового вещания (команда 0x70)"""
    try:
        if len(data) < 9:  # Минимум 9 байт заголовка
            raise ValueError("Слишком короткий пакет для ответа установки громкости")
        
        # Парсим заголовок (9 байт: 2+1+1+1+4)
        packet_format = ">H B B B I"
        packet_len, command, vsn, checksum, token = struct.unpack(packet_format, data[:9])
        
        if command != 0x70:
            raise ValueError(f"Неверная команда: {hex(command)}")
        
        # Проверяем checksum (payload пустой для ответа)
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
            "ReceivedAt": datetime.now(timezone.utc).isoformat(),
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
    
    # Кодируем строки в UTF-8
    address_bytes = server_address.encode('utf-8') + b'\x00'
    port_bytes = server_port.encode('utf-8') + b'\x00'  # Добавляем null-terminator

    # AddressLen (2) + Address (AddressLen) + PortLen (2) + Port (PortLen) + Heartbeat (1)
    payload = struct.pack(">H", len(address_bytes))  # AddressLen 
    payload += address_bytes  
    payload += struct.pack(">H", len(port_bytes))  # PortLen 
    payload += port_bytes  
    payload += struct.pack(">B", heartbeat_interval)  # Heartbeat
    
 
    packet_len = 8 + len(payload)  # 8 байт заголовка + payload
    
    # Вычисляем checksum и token
    checksum = compute_checksum(payload)
    md5 = hashlib.md5(payload + secret_key).digest()
    token = md5[3] + md5[7]*256 + md5[11]*65536 + md5[15]*16777216
    
    # Создаем заголовок (8 байт: 2+1+1+1+4)
    header = struct.pack(">HBBBI", packet_len, command, vsn, checksum, token)
    packet = header + payload
    
    # Логируем пакет
    log_packet(packet, "OUTGOING", "unknown", "SetServerAddress")
    
    return packet


def parse_set_server_address_response(data: bytes) -> Dict[str, Any]:
    """Парсит ответ на установку адреса сервера (команда 0x63)"""
    try:
        if len(data) < 9:  # Минимум 9 байт заголовка
            raise ValueError("Слишком короткий пакет для ответа установки адреса сервера")
        
        # Парсим заголовок (9 байт: 2+1+1+1+4)
        packet_format = ">H B B B I"
        packet_len, command, vsn, checksum, token = struct.unpack(packet_format, data[:9])
        
        if command != 0x63:
            raise ValueError(f"Неверная команда: {hex(command)}")
        
        # Проверяем checksum (payload пустой для ответа)
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
            "ReceivedAt": datetime.now(timezone.utc).isoformat(),
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
    payload = b''  # Пустой payload для запроса адреса сервера
    checksum = compute_checksum(payload)
    md5 = hashlib.md5(payload + secret_key).digest()
    token = md5[3] + md5[7]*256 + md5[11]*65536 + md5[15]*16777216
    header = struct.pack(">hBBBL", packet_len, command, vsn, checksum, token)
    packet = header + payload
    
    # Логируем пакет
    log_packet(packet, "OUTGOING", "unknown", "QueryServerAddress")
    
    return packet


def parse_query_server_address_response(data: bytes) -> Dict[str, Any]:
    """
    Парсит ответ станции на запрос адреса сервера (команда 0x6A).
    """
    try:
        if len(data) < 9:
            raise ValueError("Пакет слишком короткий для ответа QueryServerAddress")

        # Заголовок: 2 + 1 + 1 + 1 + 4 = 9 байт
        packet_format = ">H B B B I"
        packet_len, command, vsn, checksum, token = struct.unpack(packet_format, data[:9])

        if command != 0x6A:
            raise ValueError(f"Неверная команда: {hex(command)}")

        payload = data[9:]

        # Проверка контрольной суммы
        if compute_checksum(payload) != checksum:
            raise ValueError("Неверный checksum")

        # Разбор AddressLen + Address
        if len(payload) < 2:
            raise ValueError("Нет данных для AddressLen")
        address_len = struct.unpack(">H", payload[:2])[0]

        if len(payload) < 2 + address_len:
            raise ValueError("Недостаточно данных для адреса")
        address_bytes = payload[2:2 + address_len]
        address = address_bytes.decode("ascii", errors="ignore")

        # Разбор PortLen + Ports
        port_offset = 2 + address_len
        if len(payload) < port_offset + 2:
            raise ValueError("Нет данных для PortLen")
        port_len = struct.unpack(">H", payload[port_offset:port_offset + 2])[0]

        if len(payload) < port_offset + 2 + port_len:
            raise ValueError("Недостаточно данных для портов")
        ports_bytes = payload[port_offset + 2:port_offset + 2 + port_len]
        ports = ports_bytes.decode("ascii", errors="ignore")

        # Разбор Heartbeat
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
            "ReceivedAt": datetime.now(timezone.utc).isoformat(),
            "RawPacket": data.hex()
        }

    except Exception as e:
        return {
            "Type": "QueryServerAddressResponse",
            "Error": str(e),
            "RawPacket": data.hex(),
            "Size": len(data)
        }

