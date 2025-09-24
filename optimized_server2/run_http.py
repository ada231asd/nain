"""
Запуск HTTP сервера с API авторизации
"""
import asyncio
import signal
import sys
from http_server import HTTPServer


async def main():
    """Основная функция"""
    server = HTTPServer()
    
    # Обработчик сигналов для корректного завершения
    def signal_handler():
        print("Получен сигнал завершения")
        server.stop_server()
    
    # Устанавливаем обработчики сигналов
    if sys.platform != 'win32':
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, signal_handler)
    else:
        # На Windows используем другой подход
        def windows_signal_handler(signum, frame):
            signal_handler()
        
        signal.signal(signal.SIGINT, windows_signal_handler)
        signal.signal(signal.SIGTERM, windows_signal_handler)
    
    try:
        await server.start_server()
    except KeyboardInterrupt:
        print("Получен сигнал прерывания")
    finally:
        server.stop_server()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("HTTP сервер остановлен")
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        sys.exit(1)
