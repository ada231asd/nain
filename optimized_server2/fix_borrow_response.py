from typing import Dict, Any
import struct
from datetime import datetime, timezone

def parse_terminal_id(terminal_id_bytes: bytes) -> str:
    """Парсит terminal_id из байтов"""
    return terminal_id_bytes.hex().upper()

def compute_checksum(payload: bytes) -> int:
    """Вычисляет checksum для payload"""
    return sum(payload) & 0xFF

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
        if len(data) > 9:
            try:
                # Парсим слот и terminal_id
                slot = data[9]
                terminal_id_bytes = data[10:18]
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
