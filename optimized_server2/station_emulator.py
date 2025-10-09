import socket
from datetime import datetime
import time
import hashlib
import struct

SERVER_IP = "127.0.0.1"
PORT = 9066

# Логин пакет (91 байт - работает с сервером)
login_packet_hex = "0059600247A6F157F00408ED29A0A00011444348455930323530343030303031390068E62F1D080301444348415400001964101800001FC064024443484154000016640FDC00001EC06404444348415400000964100E00001EC064"
login_packet_bytes = bytes.fromhex(login_packet_hex)

# Секретный ключ для генерации токенов (должен совпадать с БД)
SECRET_KEY = "wZ8nY2xE"  # Ключ для станции DCHEY02504000019

def generate_heartbeat_token(secret_key: str) -> bytes:
    """Генерирует токен для heartbeat согласно протоколу"""
    payload = b''  # Для heartbeat payload пустой
    md5_hash = hashlib.md5(payload + secret_key.encode()).digest()
    token = bytes([
        md5_hash[15],  # 16-я позиция
        md5_hash[11],  # 12-я позиция  
        md5_hash[7],   # 8-я позиция
        md5_hash[3]    # 4-я позиция
    ])
    return token

def create_heartbeat_packet(secret_key: str) -> bytes:
    """Создает heartbeat пакет с правильным токеном"""
    command = 0x61
    vsn = 2
    checksum = 0
    payload = b''
    token = generate_heartbeat_token(secret_key)
    
    # Создаем пакет: PacketLen(2) + Command(1) + VSN(1) + CheckSum(1) + Token(4) = 9 байт общая длина
    packet = struct.pack(">HBBBI", 7, command, vsn, checksum, token)
    return packet

# Дополнительные пакеты для отправки после определенного количества heartbeat'ов
packet_after_2_heartbeats = bytes.fromhex("001180024c5762139302014443484154000015")
packet_after_3_heartbeats = bytes.fromhex("00266A020535DBDE0200157265646D696E652E7072696D65746563682E727500000539303636001E")
packet_after_4_heartbeats = bytes.fromhex("001465024cb30e7e5401014443484154000016010100")

# --- Функции для работы с соединением ---
def create_connection():
    """Создает новое соединение с сервером."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((SERVER_IP, PORT))
        print(f"[{datetime.now()}] Подключено к серверу {SERVER_IP}:{PORT}")
        return s
    except Exception as e:
        print(f"[{datetime.now()}] Ошибка подключения к серверу: {e}")
        return None

def attempt_login(socket_conn):
    """Попытка логина. Возвращает True если успешно, False если неудачно."""
    try:
        socket_conn.sendall(login_packet_bytes)
        print(f"[{datetime.now()}] Пакет логина отправлен серверу")
        
        response = socket_conn.recv(1024)
        if response:
            print(f"[{datetime.now()}] Ответ сервера на логин: {response.hex()}")
           
            return True
        else:
            print(f"[{datetime.now()}] Сервер не прислал ответ на логин")
            return False
    except Exception as e:
        print(f"[{datetime.now()}] Ошибка при логине: {e}")
        return False

def send_heartbeat(socket_conn):
    """Отправка heartbeat пакета."""
    try:
        # Создаем heartbeat пакет с правильным токеном
        heartbeat_packet = create_heartbeat_packet(SECRET_KEY)
        socket_conn.sendall(heartbeat_packet)
        print(f"[{datetime.now()}] Heartbeat отправлен: {heartbeat_packet.hex()}")
        
        response = socket_conn.recv(1024)
        if response:
            print(f"[{datetime.now()}] Ответ сервера: {response.hex()}")
        return True
    except Exception as e:
        print(f"[{datetime.now()}] Ошибка при отправке heartbeat: {e}")
        return False

def send_additional_packet(socket_conn, packet, packet_name):
    """Отправка дополнительного пакета после heartbeat."""
    try:
        socket_conn.sendall(packet)
        print(f"[{datetime.now()}] {packet_name} отправлен: {packet.hex()}")
        
        response = socket_conn.recv(1024)
        if response:
            print(f"[{datetime.now()}] Ответ сервера на {packet_name}: {response.hex()}")
        return True
    except Exception as e:
        print(f"[{datetime.now()}] Ошибка при отправке {packet_name}: {e}")
        return False

# Основной цикл работы эмулятора
def main():
    """Основная функция эмулятора станции"""
    s = None
    heartbeat_count = 0
    
    try:
        # Подключаемся к серверу
        print(f"[{datetime.now()}] Подключение к серверу...")
        s = create_connection()
        if s is None:
            print(f"[{datetime.now()}] Не удалось подключиться к серверу")
            return
        
        # Отправляем логин один раз
        print(f"[{datetime.now()}] Отправка логина...")
        if not attempt_login(s):
            print(f"[{datetime.now()}] Логин неудачен")
            s.close()
            return
        
        print(f"[{datetime.now()}] Логин успешен! Начинаем отправку heartbeat пакетов...")
        
        # Основной цикл - отправляем heartbeat каждые 30 секунд
        while True:
            try:
                # Отправляем heartbeat
                if not send_heartbeat(s):
                    print(f"[{datetime.now()}] Ошибка отправки heartbeat. Соединение разорвано.")
                    break
                
                heartbeat_count += 1
                print(f"[{datetime.now()}] Heartbeat #{heartbeat_count} отправлен")
                
                # Отправляем дополнительные пакеты после определенного количества heartbeat'ов
                if heartbeat_count == 2:
                    print(f"[{datetime.now()}] Отправка пакета после 2-го heartbeat...")
                    send_additional_packet(s, packet_after_2_heartbeats, "Пакет после 2-го heartbeat")
                elif heartbeat_count == 3:
                    print(f"[{datetime.now()}] Отправка пакета после 3-го heartbeat...")
                    send_additional_packet(s, packet_after_3_heartbeats, "Пакет после 3-го heartbeat")
                elif heartbeat_count == 4:
                    print(f"[{datetime.now()}] Отправка пакета после 4-го heartbeat...")
                    send_additional_packet(s, packet_after_4_heartbeats, "Пакет после 4-го heartbeat")
                
                # Ждем 30 секунд до следующего heartbeat
                print(f"[{datetime.now()}] Ожидание 30 секунд до следующего heartbeat...")
                time.sleep(30)
                
            except Exception as e:
                print(f"[{datetime.now()}] Ошибка в цикле heartbeat: {e}")
                break
                
    except KeyboardInterrupt:
        print(f"[{datetime.now()}] Эмулятор завершен пользователем")
    except Exception as e:
        print(f"[{datetime.now()}] Критическая ошибка: {e}")
    finally:
        if s:
            s.close()
            print(f"[{datetime.now()}] Соединение закрыто")

if __name__ == "__main__":
    main()