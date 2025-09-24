#!/usr/bin/env python3
"""
Тест создания пакета Set Server Address (0x63)
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.packet_utils import build_set_server_address_request, parse_set_server_address_response

def test_set_server_address_packet():
    """Тестирует создание пакета Set Server Address"""
    
    # Тестовые данные (как в примере)
    secret_key = b'test_secret_key_12345'  # 20 байт
    server_address = "redmine.primeteh.ru"
    server_port = "9066"
    heartbeat_interval = 30
    vsn = 1
    
    print("=== Тест создания пакета Set Server Address (0x63) ===")
    print(f"Secret Key: {secret_key.hex()}")
    print(f"Server Address: {server_address}")
    print(f"Server Port: {server_port}")
    print(f"Heartbeat Interval: {heartbeat_interval}")
    print(f"VSN: {vsn}")
    print()
    
    # Создаем пакет
    packet = build_set_server_address_request(
        secret_key=secret_key,
        server_address=server_address,
        server_port=server_port,
        heartbeat_interval=heartbeat_interval,
        vsn=vsn
    )
    
    print("=== Созданный пакет ===")
    print(f"Длина пакета: {len(packet)} байт")
    print(f"Hex: {packet.hex().upper()}")
    print()
    
    # Анализируем структуру пакета
    print("=== Анализ структуры пакета ===")
    
    # Заголовок (8 байт)
    packet_len = int.from_bytes(packet[0:2], 'big')
    command = packet[2]
    vsn_parsed = packet[3]
    checksum = packet[4]
    token = int.from_bytes(packet[5:9], 'big')
    
    print(f"PacketLen: {packet_len} (0x{packet_len:04X})")
    print(f"Command: 0x{command:02X}")
    print(f"VSN: {vsn_parsed}")
    print(f"CheckSum: 0x{checksum:02X}")
    print(f"Token: 0x{token:08X}")
    print()
    
    # Payload
    payload = packet[8:]
    print(f"Payload длина: {len(payload)} байт")
    print(f"Payload hex: {payload.hex().upper()}")
    print()
    
    # Анализируем payload
    if len(payload) >= 2:
        address_len = int.from_bytes(payload[0:2], 'big')
        print(f"AddressLen: {address_len}")
        
        if len(payload) >= 2 + address_len:
            address_bytes = payload[2:2 + address_len]
            address = address_bytes.decode('utf-8')
            print(f"Address: '{address}'")
            
            if len(payload) >= 4 + address_len:
                port_len = int.from_bytes(payload[2 + address_len:4 + address_len], 'big')
                print(f"PortLen: {port_len}")
                
                if len(payload) >= 4 + address_len + port_len:
                    port_bytes = payload[4 + address_len:4 + address_len + port_len]
                    port = port_bytes.decode('utf-8', errors='ignore')
                    print(f"Port: '{port}'")
                    
                    if len(payload) >= 5 + address_len + port_len:
                        heartbeat = payload[4 + address_len + port_len]
                        print(f"Heartbeat: {heartbeat}")
    
    print()
    
    # Проверяем checksum
    from utils.packet_utils import compute_checksum
    computed_checksum = compute_checksum(payload)
    print(f"=== Проверка CheckSum ===")
    print(f"Вычисленный CheckSum: 0x{computed_checksum:02X}")
    print(f"CheckSum в пакете: 0x{checksum:02X}")
    print(f"CheckSum корректен: {computed_checksum == checksum}")
    print()
    
    # Проверяем token
    import hashlib
    md5 = hashlib.md5(payload + secret_key).digest()
    computed_token = md5[3] + md5[7]*256 + md5[11]*65536 + md5[15]*16777216
    print(f"=== Проверка Token ===")
    print(f"MD5 hash: {md5.hex().upper()}")
    print(f"Вычисленный Token: 0x{computed_token:08X}")
    print(f"Token в пакете: 0x{token:08X}")
    print(f"Token корректен: {computed_token == token}")
    print()
    
    # Тестируем парсинг ответа (симуляция)
    print("=== Тест парсинга ответа ===")
    # Создаем симулированный ответ (только заголовок)
    response_packet = packet[:8]  # Только заголовок для ответа
    response_parsed = parse_set_server_address_response(response_packet)
    print(f"Парсинг ответа: {response_parsed}")
    print()
    
    # Сравнение с ожидаемым результатом
    print("=== Сравнение с ожидаемым результатом ===")
    expected_hex = "00276301049574CD2100157265646D696E652E7072696D65746563682E727500000539303636001E"
    expected_bytes = bytes.fromhex(expected_hex)
    
    print(f"Ожидаемый пакет: {expected_hex}")
    print(f"Наш пакет:      {packet.hex().upper()}")
    print(f"Пакеты совпадают: {packet.hex().upper() == expected_hex}")
    
    if packet.hex().upper() != expected_hex:
        print("\n=== Детальное сравнение ===")
        print(f"Ожидаемая длина: {len(expected_bytes)} байт")
        print(f"Наша длина: {len(packet)} байт")
        
        # Сравниваем по байтам
        min_len = min(len(expected_bytes), len(packet))
        for i in range(min_len):
            if expected_bytes[i] != packet[i]:
                print(f"Байт {i}: ожидается 0x{expected_bytes[i]:02X}, получено 0x{packet[i]:02X}")
        
        if len(expected_bytes) != len(packet):
            print(f"Разная длина: ожидается {len(expected_bytes)}, получено {len(packet)}")
    
    print("\n=== Тест завершен ===")

if __name__ == "__main__":
    test_set_server_address_packet()
