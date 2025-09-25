-- phpMyAdmin SQL Dump
-- version 5.2.0
-- https://www.phpmyadmin.net/
--
-- Хост: 127.0.0.1:3306
-- Время создания: Сен 25 2025 г., 00:08
-- Версия сервера: 5.7.39
-- Версия PHP: 8.1.9

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- База данных: `DB`
--
CREATE DATABASE IF NOT EXISTS `DB` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `DB`;

-- --------------------------------------------------------

--
-- Структура таблицы `action_logs`
--

CREATE TABLE `action_logs` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `user_id` bigint(20) UNSIGNED DEFAULT NULL,
  `action_type` enum('login','logout','user_approve','user_reject','user_create','user_update','user_delete','station_create','station_update','station_delete','powerbank_create','powerbank_update','powerbank_delete','group_create','group_update','group_delete','order_create','order_update','order_delete','system_error','api_call') COLLATE utf8mb4_unicode_ci NOT NULL,
  `entity_type` enum('user','station','powerbank','group','order','system') COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `entity_id` bigint(20) UNSIGNED DEFAULT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  `ip_address` varchar(45) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `user_agent` text COLLATE utf8mb4_unicode_ci,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Таблица логов действий пользователей и системы';

-- --------------------------------------------------------

--
-- Структура таблицы `app_user`
--

CREATE TABLE `app_user` (
  `user_id` bigint(20) UNSIGNED NOT NULL,
  `fio` varchar(250) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `password_hash` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `email` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `phone_e164` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` enum('pending','active','blocked') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `last_login_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Дамп данных таблицы `app_user`
--

INSERT INTO `app_user` (`user_id`, `fio`, `password_hash`, `email`, `phone_e164`, `status`, `created_at`, `last_login_at`) VALUES
(6, 'irin', '$2b$12$rbGO6a0DX9yc5TgOEO7P9e1aSRouHNZLc3ZhaBCVtGHFjM4obsHqu', 'Aleksey123@mail.ru', '121423123', 'active', '2025-09-17 17:23:21', '2025-09-17 23:33:45'),
(8, 'Обновленное имя', '$2b$12$DSlZoGn6cmLnqaTRRQJyLuepuRah1G0fK.TTLEvA2WnBNN3t4uYNm', 'updated@example.com', '+79001234567', 'active', '2025-09-18 13:12:16', '2025-09-24 18:57:20');

--
-- Триггеры `app_user`
--
DELIMITER $$
CREATE TRIGGER `log_user_changes` AFTER UPDATE ON `app_user` FOR EACH ROW BEGIN
    IF OLD.status != NEW.status THEN
        INSERT INTO `action_logs` (user_id, action_type, entity_type, entity_id, description)
        VALUES (NEW.user_id, 'user_update', 'user', NEW.user_id, 
                CONCAT('Изменение статуса с ', OLD.status, ' на ', NEW.status));
    END IF;
END
$$
DELIMITER ;

-- --------------------------------------------------------

--
-- Структура таблицы `orders`
--

CREATE TABLE `orders` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `station_id` bigint(20) UNSIGNED NOT NULL,
  `user_id` bigint(20) UNSIGNED NOT NULL,
  `powerbank_id` bigint(20) UNSIGNED DEFAULT NULL,
  `status` enum('borrow','return','force_eject') COLLATE utf8mb4_unicode_ci NOT NULL,
  `timestamp` timestamp NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Триггеры `orders`
--
DELIMITER $$
CREATE TRIGGER `log_order_creation` AFTER INSERT ON `orders` FOR EACH ROW BEGIN
    INSERT INTO `action_logs` (user_id, action_type, entity_type, entity_id, description)
    VALUES (NEW.user_id, 'order_create', 'order', NEW.id, 
            CONCAT('Создание заказа: ', NEW.status, ' повербанка #', IFNULL(NEW.powerbank_id, 'N/A')));
END
$$
DELIMITER ;

-- --------------------------------------------------------

--
-- Структура таблицы `org_unit`
--

CREATE TABLE `org_unit` (
  `org_unit_id` bigint(20) UNSIGNED NOT NULL,
  `parent_org_unit_id` bigint(20) UNSIGNED DEFAULT NULL,
  `unit_type` enum('group','subgroup') COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `adress` text COLLATE utf8mb4_unicode_ci,
  `logo_url` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Дамп данных таблицы `org_unit`
--

INSERT INTO `org_unit` (`org_unit_id`, `parent_org_unit_id`, `unit_type`, `name`, `adress`, `logo_url`, `created_at`) VALUES
(1, 1, 'group', 'Updated Test Organization', NULL, NULL, '2025-09-13 09:15:54'),
(2, 1, 'subgroup', 'NY Branch', NULL, NULL, '2025-09-13 09:15:54'),
(3, 1, 'subgroup', 'LA Branch', NULL, NULL, '2025-09-13 09:15:54');

-- --------------------------------------------------------

--
-- Структура таблицы `powerbank`
--

CREATE TABLE `powerbank` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `org_unit_id` bigint(20) UNSIGNED DEFAULT NULL,
  `serial_number` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `soh` int(11) DEFAULT NULL,
  `status` enum('active','user_reported_broken','system_error','written_off','unknown') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'unknown',
  `write_off_reason` enum('none','broken','lost','other') COLLATE utf8mb4_unicode_ci DEFAULT 'none',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Дамп данных таблицы `powerbank`
--

INSERT INTO `powerbank` (`id`, `org_unit_id`, `serial_number`, `soh`, `status`, `write_off_reason`, `created_at`) VALUES
(1, 1, 'DCHA54000016', 100, 'unknown', 'none', '2025-09-23 17:22:49'),
(2, 1, 'DCHA54000009', 100, 'unknown', 'none', '2025-09-23 17:22:49'),
(3, 1, 'DCHA54000019', 100, 'unknown', 'none', '2025-09-23 17:22:49');

-- --------------------------------------------------------

--
-- Структура таблицы `station`
--

CREATE TABLE `station` (
  `station_id` bigint(20) UNSIGNED NOT NULL,
  `org_unit_id` bigint(20) UNSIGNED DEFAULT NULL,
  `box_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `iccid` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `slots_declared` int(11) NOT NULL,
  `remain_num` int(11) NOT NULL DEFAULT '0',
  `last_seen` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `status` enum('active','inactive','pending') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Дамп данных таблицы `station`
--

INSERT INTO `station` (`station_id`, `org_unit_id`, `box_id`, `iccid`, `slots_declared`, `remain_num`, `last_seen`, `created_at`, `updated_at`, `status`) VALUES
(1, 1, 'DCHEY02504000018', NULL, 4, 1, '2025-09-24 20:58:46', '2025-09-22 20:12:45', '2025-09-24 20:59:00', 'inactive');

-- --------------------------------------------------------

--
-- Структура таблицы `station_powerbank`
--

CREATE TABLE `station_powerbank` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `station_id` bigint(20) UNSIGNED NOT NULL,
  `powerbank_id` bigint(20) UNSIGNED NOT NULL,
  `slot_number` int(11) NOT NULL,
  `level` int(11) DEFAULT NULL,
  `voltage` int(11) DEFAULT NULL,
  `temperature` int(11) DEFAULT NULL,
  `last_update` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Дамп данных таблицы `station_powerbank`
--

INSERT INTO `station_powerbank` (`id`, `station_id`, `powerbank_id`, `slot_number`, `level`, `voltage`, `temperature`, `last_update`) VALUES
(64, 1, 1, 1, 100, 4120, 32, '2025-09-24 20:37:15'),
(65, 1, 2, 2, 100, 4110, 31, '2025-09-24 20:37:15'),
(66, 1, 3, 3, 100, 4100, 31, '2025-09-24 20:37:15');

-- --------------------------------------------------------

--
-- Структура таблицы `station_secret_key`
--

CREATE TABLE `station_secret_key` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `station_id` bigint(20) UNSIGNED NOT NULL,
  `key_value` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Дамп данных таблицы `station_secret_key`
--

INSERT INTO `station_secret_key` (`id`, `station_id`, `key_value`) VALUES
(1, 1, 'wZ8nY2xE');

-- --------------------------------------------------------

--
-- Структура таблицы `user_favorites`
--

CREATE TABLE `user_favorites` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `user_id` bigint(20) UNSIGNED NOT NULL,
  `station_id` bigint(20) UNSIGNED NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Структура таблицы `user_role`
--

CREATE TABLE `user_role` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `user_id` bigint(20) UNSIGNED NOT NULL,
  `org_unit_id` bigint(20) UNSIGNED DEFAULT NULL,
  `role` enum('user','subgroup_admin','group_admin','service_admin') COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Дамп данных таблицы `user_role`
--

INSERT INTO `user_role` (`id`, `user_id`, `org_unit_id`, `role`, `created_at`) VALUES
(5, 8, NULL, 'service_admin', '2025-09-18 18:12:34'),
(6, 6, NULL, 'service_admin', '2025-09-22 11:12:52');

--
-- Индексы сохранённых таблиц
--

--
-- Индексы таблицы `action_logs`
--
ALTER TABLE `action_logs`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_user_id` (`user_id`),
  ADD KEY `idx_action_type` (`action_type`),
  ADD KEY `idx_entity_type` (`entity_type`),
  ADD KEY `idx_entity_id` (`entity_id`),
  ADD KEY `idx_created_at` (`created_at`),
  ADD KEY `idx_logs_composite` (`action_type`,`entity_type`,`created_at`),
  ADD KEY `idx_logs_user_actions` (`user_id`,`action_type`,`created_at`);
ALTER TABLE `action_logs` ADD FULLTEXT KEY `description` (`description`);

--
-- Индексы таблицы `app_user`
--
ALTER TABLE `app_user`
  ADD PRIMARY KEY (`user_id`),
  ADD UNIQUE KEY `phone_e164` (`phone_e164`);

--
-- Индексы таблицы `orders`
--
ALTER TABLE `orders`
  ADD PRIMARY KEY (`id`),
  ADD KEY `fk_orders_station` (`station_id`),
  ADD KEY `fk_orders_user` (`user_id`),
  ADD KEY `fk_orders_powerbank` (`powerbank_id`);

--
-- Индексы таблицы `org_unit`
--
ALTER TABLE `org_unit`
  ADD PRIMARY KEY (`org_unit_id`),
  ADD KEY `fk_org_parent` (`parent_org_unit_id`);

--
-- Индексы таблицы `powerbank`
--
ALTER TABLE `powerbank`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uq_serial` (`serial_number`),
  ADD KEY `fk_powerbank_org` (`org_unit_id`);

--
-- Индексы таблицы `station`
--
ALTER TABLE `station`
  ADD PRIMARY KEY (`station_id`),
  ADD UNIQUE KEY `box_id` (`box_id`),
  ADD KEY `fk_station_org` (`org_unit_id`);

--
-- Индексы таблицы `station_powerbank`
--
ALTER TABLE `station_powerbank`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uq_station_slot` (`station_id`,`slot_number`),
  ADD UNIQUE KEY `uq_station_powerbank` (`station_id`,`powerbank_id`),
  ADD KEY `fk_sp_powerbank` (`powerbank_id`);

--
-- Индексы таблицы `station_secret_key`
--
ALTER TABLE `station_secret_key`
  ADD PRIMARY KEY (`id`),
  ADD KEY `station_id` (`station_id`);

--
-- Индексы таблицы `user_favorites`
--
ALTER TABLE `user_favorites`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uq_user_fav` (`user_id`,`station_id`),
  ADD KEY `fk_fav_station` (`station_id`);

--
-- Индексы таблицы `user_role`
--
ALTER TABLE `user_role`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uq_user_role` (`user_id`,`org_unit_id`,`role`),
  ADD KEY `fk_user_role_org` (`org_unit_id`);

--
-- AUTO_INCREMENT для сохранённых таблиц
--

--
-- AUTO_INCREMENT для таблицы `action_logs`
--
ALTER TABLE `action_logs`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT для таблицы `app_user`
--
ALTER TABLE `app_user`
  MODIFY `user_id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=9;

--
-- AUTO_INCREMENT для таблицы `orders`
--
ALTER TABLE `orders`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT для таблицы `org_unit`
--
ALTER TABLE `org_unit`
  MODIFY `org_unit_id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT для таблицы `powerbank`
--
ALTER TABLE `powerbank`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT для таблицы `station`
--
ALTER TABLE `station`
  MODIFY `station_id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT для таблицы `station_powerbank`
--
ALTER TABLE `station_powerbank`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=67;

--
-- AUTO_INCREMENT для таблицы `station_secret_key`
--
ALTER TABLE `station_secret_key`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT для таблицы `user_favorites`
--
ALTER TABLE `user_favorites`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT для таблицы `user_role`
--
ALTER TABLE `user_role`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;

--
-- Ограничения внешнего ключа сохраненных таблиц
--

--
-- Ограничения внешнего ключа таблицы `action_logs`
--
ALTER TABLE `action_logs`
  ADD CONSTRAINT `fk_logs_user` FOREIGN KEY (`user_id`) REFERENCES `app_user` (`user_id`) ON DELETE SET NULL ON UPDATE CASCADE;

--
-- Ограничения внешнего ключа таблицы `orders`
--
ALTER TABLE `orders`
  ADD CONSTRAINT `fk_orders_powerbank` FOREIGN KEY (`powerbank_id`) REFERENCES `powerbank` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_orders_station` FOREIGN KEY (`station_id`) REFERENCES `station` (`station_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_orders_user` FOREIGN KEY (`user_id`) REFERENCES `app_user` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Ограничения внешнего ключа таблицы `org_unit`
--
ALTER TABLE `org_unit`
  ADD CONSTRAINT `fk_org_parent` FOREIGN KEY (`parent_org_unit_id`) REFERENCES `org_unit` (`org_unit_id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Ограничения внешнего ключа таблицы `powerbank`
--
ALTER TABLE `powerbank`
  ADD CONSTRAINT `fk_powerbank_org` FOREIGN KEY (`org_unit_id`) REFERENCES `org_unit` (`org_unit_id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Ограничения внешнего ключа таблицы `station`
--
ALTER TABLE `station`
  ADD CONSTRAINT `fk_station_org` FOREIGN KEY (`org_unit_id`) REFERENCES `org_unit` (`org_unit_id`) ON UPDATE CASCADE;

--
-- Ограничения внешнего ключа таблицы `station_powerbank`
--
ALTER TABLE `station_powerbank`
  ADD CONSTRAINT `fk_sp_powerbank` FOREIGN KEY (`powerbank_id`) REFERENCES `powerbank` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_sp_station` FOREIGN KEY (`station_id`) REFERENCES `station` (`station_id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Ограничения внешнего ключа таблицы `station_secret_key`
--
ALTER TABLE `station_secret_key`
  ADD CONSTRAINT `station_secret_key_ibfk_1` FOREIGN KEY (`station_id`) REFERENCES `station` (`station_id`);

--
-- Ограничения внешнего ключа таблицы `user_favorites`
--
ALTER TABLE `user_favorites`
  ADD CONSTRAINT `fk_fav_station` FOREIGN KEY (`station_id`) REFERENCES `station` (`station_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_fav_user` FOREIGN KEY (`user_id`) REFERENCES `app_user` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Ограничения внешнего ключа таблицы `user_role`
--
ALTER TABLE `user_role`
  ADD CONSTRAINT `fk_user_role_org` FOREIGN KEY (`org_unit_id`) REFERENCES `org_unit` (`org_unit_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_user_role_user` FOREIGN KEY (`user_id`) REFERENCES `app_user` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
