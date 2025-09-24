#!/usr/bin/env python3
"""
Скрипт для создания таблицы логов в базе данных
"""
import asyncio
import aiomysql
from config.settings import DB_CONFIG


async def setup_logs_table():
    """Создает таблицу логов в базе данных"""
    
    # SQL для создания таблицы логов
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS `action_logs` (
      `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
      `user_id` bigint(20) UNSIGNED DEFAULT NULL,
      `action_type` enum('login','logout','user_approve','user_reject','user_create','user_update','user_delete','station_create','station_update','station_delete','powerbank_create','powerbank_update','powerbank_delete','group_create','group_update','group_delete','order_create','order_update','order_delete','system_error','api_call') COLLATE utf8mb4_unicode_ci NOT NULL,
      `entity_type` enum('user','station','powerbank','group','order','system') COLLATE utf8mb4_unicode_ci DEFAULT NULL,
      `entity_id` bigint(20) UNSIGNED DEFAULT NULL,
      `description` text COLLATE utf8mb4_unicode_ci,
      `ip_address` varchar(45) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
      `user_agent` text COLLATE utf8mb4_unicode_ci,
      `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (`id`),
      KEY `idx_user_id` (`user_id`),
      KEY `idx_action_type` (`action_type`),
      KEY `idx_entity_type` (`entity_type`),
      KEY `idx_entity_id` (`entity_id`),
      KEY `idx_created_at` (`created_at`),
      CONSTRAINT `fk_logs_user` FOREIGN KEY (`user_id`) REFERENCES `app_user` (`user_id`) ON DELETE SET NULL ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    
    # SQL для создания индексов
    create_indexes_sql = [
        "CREATE INDEX IF NOT EXISTS `idx_logs_composite` ON `action_logs` (`action_type`, `entity_type`, `created_at`);",
        "CREATE INDEX IF NOT EXISTS `idx_logs_user_actions` ON `action_logs` (`user_id`, `action_type`, `created_at`);"
    ]
    
    # SQL для вставки тестовых данных
    insert_test_data_sql = """
    INSERT IGNORE INTO `action_logs` (`user_id`, `action_type`, `entity_type`, `entity_id`, `description`, `ip_address`, `created_at`) VALUES
    (6, 'login', 'user', 6, 'Вход в систему', '127.0.0.1', NOW()),
    (8, 'login', 'user', 8, 'Вход в систему', '127.0.0.1', NOW()),
    (6, 'user_approve', 'user', 8, 'Подтверждение пользователя', '127.0.0.1', NOW()),
    (8, 'station_create', 'station', 7, 'Создание станции DCHEY02504000018', '127.0.0.1', NOW()),
    (8, 'powerbank_create', 'powerbank', 7, 'Создание повербанка DCHA54000016', '127.0.0.1', NOW()),
    (8, 'order_create', 'order', 11, 'Создание заказа на выдачу повербанка', '127.0.0.1', NOW()),
    (8, 'order_update', 'order', 13, 'Обновление заказа - возврат повербанка', '127.0.0.1', NOW()),
    (NULL, 'system_error', 'system', NULL, 'Ошибка подключения к базе данных', '127.0.0.1', NOW() - INTERVAL 1 HOUR),
    (NULL, 'api_call', 'system', NULL, 'API вызов: GET /api/users', '127.0.0.1', NOW() - INTERVAL 30 MINUTE),
    (NULL, 'api_call', 'system', NULL, 'API вызов: GET /api/stations', '127.0.0.1', NOW() - INTERVAL 25 MINUTE);
    """
    
    try:
        # Подключаемся к базе данных
        print("Подключение к базе данных...")
        pool = await aiomysql.create_pool(**DB_CONFIG)
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                print("Создание таблицы action_logs...")
                await cur.execute(create_table_sql)
                
                print("Создание индексов...")
                for index_sql in create_indexes_sql:
                    await cur.execute(index_sql)
                
                print("Вставка тестовых данных...")
                await cur.execute(insert_test_data_sql)
                
                # Проверяем, что таблица создана
                await cur.execute("SELECT COUNT(*) FROM action_logs")
                count = await cur.fetchone()
                print(f"Таблица action_logs создана успешно. Записей: {count[0]}")
                
        print("Настройка логов завершена успешно!")
        
    except Exception as e:
        print(f"Ошибка при создании таблицы логов: {e}")
        raise
    finally:
        if 'pool' in locals():
            pool.close()
            await pool.wait_closed()


async def main():
    """Основная функция"""
    try:
        await setup_logs_table()
    except Exception as e:
        print(f"Ошибка: {e}")
        return 1
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
