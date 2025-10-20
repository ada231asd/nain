-- phpMyAdmin SQL Dump
-- version 5.0.4
-- https://www.phpmyadmin.net/
--
-- Хост: 127.0.0.1:3306
-- Время создания: Окт 18 2025 г., 17:45
-- Версия сервера: 5.7.29-log
-- Версия PHP: 8.0.1

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- База данных: `zaryd`
--

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

--
-- Дамп данных таблицы `action_logs`
--

INSERT INTO `action_logs` (`id`, `user_id`, `action_type`, `entity_type`, `entity_id`, `description`, `ip_address`, `user_agent`, `created_at`) VALUES
(16, NULL, 'user_update', 'user', 9, 'Изменение статуса с pending на active', NULL, NULL, '2025-09-22 11:11:39'),
(17, NULL, 'order_create', 'order', 1, 'Создание заказа: borrow повербанка #13', NULL, NULL, '2025-09-22 11:18:31'),
(18, NULL, 'order_create', 'order', 2, 'Создание заказа: force_eject повербанка #11', NULL, NULL, '2025-09-22 11:19:01'),
(19, NULL, 'order_create', 'order', 3, 'Создание заказа: borrow повербанка #10', NULL, NULL, '2025-09-22 11:19:15'),
(20, NULL, 'order_create', 'order', 4, 'Создание заказа: borrow повербанка #10', NULL, NULL, '2025-09-22 11:26:50'),
(21, NULL, 'order_create', 'order', 5, 'Создание заказа: borrow повербанка #11', NULL, NULL, '2025-09-22 11:40:01'),
(22, NULL, 'order_create', 'order', 6, 'Создание заказа: borrow повербанка #11', NULL, NULL, '2025-09-22 11:45:38'),
(23, NULL, 'order_create', 'order', 7, 'Создание заказа: borrow повербанка #11', NULL, NULL, '2025-09-22 11:45:49'),
(24, NULL, 'order_create', 'order', 8, 'Создание заказа: borrow повербанка #12', NULL, NULL, '2025-09-22 11:45:59'),
(25, NULL, 'order_create', 'order', 9, 'Создание заказа: borrow повербанка #13', NULL, NULL, '2025-09-22 11:46:03'),
(26, NULL, 'order_create', 'order', 10, 'Создание заказа: borrow повербанка #10', NULL, NULL, '2025-09-22 11:46:07'),
(27, NULL, 'order_create', 'order', 11, 'Создание заказа: borrow повербанка #11', NULL, NULL, '2025-09-22 11:53:57'),
(28, NULL, 'order_create', 'order', 12, 'Создание заказа: borrow повербанка #12', NULL, NULL, '2025-09-22 11:54:01'),
(29, NULL, 'order_create', 'order', 13, 'Создание заказа: borrow повербанка #11', NULL, NULL, '2025-09-22 11:54:16'),
(30, NULL, 'order_create', 'order', 14, 'Создание заказа: borrow повербанка #11', NULL, NULL, '2025-09-22 11:57:06'),
(31, NULL, 'order_create', 'order', 15, 'Создание заказа: borrow повербанка #12', NULL, NULL, '2025-09-22 11:57:08'),
(32, NULL, 'order_create', 'order', 16, 'Создание заказа: borrow повербанка #10', NULL, NULL, '2025-09-22 11:57:16'),
(33, NULL, 'order_create', 'order', 17, 'Создание заказа: borrow повербанка #13', NULL, NULL, '2025-09-22 11:58:26'),
(34, NULL, 'order_create', 'order', 18, 'Создание заказа: force_eject повербанка #11', NULL, NULL, '2025-09-22 12:00:33'),
(35, NULL, 'order_create', 'order', 20, 'Создание заказа: borrow повербанка #11', NULL, NULL, '2025-09-22 12:07:09'),
(36, NULL, 'order_create', 'order', 21, 'Создание заказа: borrow повербанка #12', NULL, NULL, '2025-09-22 12:07:15'),
(37, NULL, 'order_create', 'order', 22, 'Создание заказа: borrow повербанка #11', NULL, NULL, '2025-09-22 12:07:19'),
(38, NULL, 'order_create', 'order', 23, 'Создание заказа: borrow повербанка #13', NULL, NULL, '2025-09-22 12:07:25'),
(39, NULL, 'order_create', 'order', 27, 'Создание заказа: force_eject повербанка #10', NULL, NULL, '2025-09-22 12:25:58'),
(40, NULL, 'order_create', 'order', 28, 'Создание заказа: force_eject повербанка #11', NULL, NULL, '2025-09-22 12:26:01'),
(41, NULL, 'order_create', 'order', 29, 'Создание заказа: borrow повербанка #13', NULL, NULL, '2025-09-22 12:26:14'),
(42, NULL, 'order_create', 'order', 31, 'Создание заказа: force_eject повербанка #12', NULL, NULL, '2025-09-22 12:28:57'),
(43, NULL, 'order_create', 'order', 33, 'Создание заказа: borrow повербанка #10', NULL, NULL, '2025-09-22 12:29:32'),
(44, NULL, 'order_create', 'order', 34, 'Создание заказа: force_eject повербанка #13', NULL, NULL, '2025-09-22 12:29:42'),
(45, NULL, 'order_create', 'order', 35, 'Создание заказа: force_eject повербанка #12', NULL, NULL, '2025-09-22 12:29:55'),
(46, NULL, 'order_create', 'order', 38, 'Создание заказа: borrow повербанка #12', NULL, NULL, '2025-09-22 12:31:28'),
(47, NULL, 'order_create', 'order', 39, 'Создание заказа: force_eject повербанка #10', NULL, NULL, '2025-09-22 12:32:01'),
(48, NULL, 'order_create', 'order', 40, 'Создание заказа: force_eject повербанка #11', NULL, NULL, '2025-09-22 12:32:04'),
(49, NULL, 'order_create', 'order', 41, 'Создание заказа: force_eject повербанка #13', NULL, NULL, '2025-09-22 12:32:10'),
(50, NULL, 'order_create', 'order', 42, 'Создание заказа: force_eject повербанка #12', NULL, NULL, '2025-09-22 12:32:12'),
(51, NULL, 'order_create', 'order', 43, 'Создание заказа: force_eject повербанка #10', NULL, NULL, '2025-09-22 12:35:18'),
(52, NULL, 'order_create', 'order', 44, 'Создание заказа: borrow повербанка #10', NULL, NULL, '2025-09-22 12:42:39'),
(53, NULL, 'order_create', 'order', 45, 'Создание заказа: borrow повербанка #10', NULL, NULL, '2025-09-22 12:48:46'),
(54, NULL, 'order_create', 'order', 46, 'Создание заказа: force_eject повербанка #16', NULL, NULL, '2025-09-22 12:53:10'),
(55, NULL, 'order_create', 'order', 47, 'Создание заказа: force_eject повербанка #15', NULL, NULL, '2025-09-22 13:36:47'),
(56, NULL, 'order_create', 'order', 48, 'Создание заказа: force_eject повербанка #14', NULL, NULL, '2025-09-22 13:36:49'),
(57, NULL, 'order_create', 'order', 49, 'Создание заказа: force_eject повербанка #17', NULL, NULL, '2025-09-22 13:36:50'),
(58, NULL, 'order_create', 'order', 50, 'Создание заказа: force_eject повербанка #16', NULL, NULL, '2025-09-22 13:36:57'),
(59, NULL, 'order_create', 'order', 51, 'Создание заказа: force_eject повербанка #16', NULL, NULL, '2025-09-22 13:37:30'),
(60, NULL, 'order_create', 'order', 52, 'Создание заказа: force_eject повербанка #17', NULL, NULL, '2025-09-22 13:37:32'),
(61, NULL, 'order_create', 'order', 55, 'Создание заказа: force_eject повербанка #14', NULL, NULL, '2025-09-22 13:38:09'),
(62, NULL, 'order_create', 'order', 57, 'Создание заказа: force_eject повербанка #16', NULL, NULL, '2025-09-22 13:38:13'),
(63, NULL, 'order_create', 'order', 58, 'Создание заказа: force_eject повербанка #14', NULL, NULL, '2025-09-22 13:38:24'),
(64, NULL, 'order_create', 'order', 60, 'Создание заказа: force_eject повербанка #14', NULL, NULL, '2025-09-22 13:39:10'),
(65, NULL, 'order_create', 'order', 62, 'Создание заказа: force_eject повербанка #17', NULL, NULL, '2025-09-22 13:40:01'),
(66, NULL, 'order_create', 'order', 63, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-22 13:42:58'),
(67, NULL, 'order_create', 'order', 64, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-22 13:43:57'),
(68, NULL, 'order_create', 'order', 65, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-22 13:44:03'),
(69, NULL, 'order_create', 'order', 68, 'Создание заказа: borrow повербанка #17', NULL, NULL, '2025-09-22 14:02:49'),
(70, NULL, 'order_create', 'order', 69, 'Создание заказа: borrow повербанка #14', NULL, NULL, '2025-09-22 14:02:56'),
(71, NULL, 'order_create', 'order', 70, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-22 14:03:01'),
(72, NULL, 'order_create', 'order', 71, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-22 14:03:05'),
(73, NULL, 'order_create', 'order', 72, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-22 14:03:06'),
(74, NULL, 'order_create', 'order', 73, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-22 14:03:06'),
(75, NULL, 'order_create', 'order', 74, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-22 14:03:11'),
(76, NULL, 'order_create', 'order', 76, 'Создание заказа: borrow повербанка #17', NULL, NULL, '2025-09-22 14:05:38'),
(77, NULL, 'order_create', 'order', 77, 'Создание заказа: borrow повербанка #14', NULL, NULL, '2025-09-22 14:05:47'),
(78, NULL, 'order_create', 'order', 78, 'Создание заказа: force_eject повербанка #15', NULL, NULL, '2025-09-22 14:05:56'),
(79, NULL, 'order_create', 'order', 79, 'Создание заказа: force_eject повербанка #17', NULL, NULL, '2025-09-22 14:24:32'),
(80, NULL, 'order_create', 'order', 82, 'Создание заказа: force_eject повербанка #17', NULL, NULL, '2025-09-23 10:35:47'),
(81, NULL, 'order_create', 'order', 83, 'Создание заказа: borrow повербанка #14', NULL, NULL, '2025-09-23 10:35:55'),
(82, NULL, 'order_create', 'order', 84, 'Создание заказа: force_eject повербанка #14', NULL, NULL, '2025-09-23 10:35:58'),
(83, NULL, 'order_create', 'order', 85, 'Создание заказа: force_eject повербанка #15', NULL, NULL, '2025-09-23 10:36:03'),
(84, NULL, 'order_create', 'order', 86, 'Создание заказа: force_eject повербанка #17', NULL, NULL, '2025-09-23 10:44:13'),
(85, NULL, 'order_create', 'order', 87, 'Создание заказа: force_eject повербанка #14', NULL, NULL, '2025-09-23 10:44:23'),
(86, NULL, 'order_create', 'order', 88, 'Создание заказа: force_eject повербанка #15', NULL, NULL, '2025-09-23 10:44:25'),
(87, NULL, 'order_create', 'order', 89, 'Создание заказа: force_eject повербанка #17', NULL, NULL, '2025-09-23 10:57:40'),
(88, NULL, 'order_create', 'order', 90, 'Создание заказа: force_eject повербанка #14', NULL, NULL, '2025-09-23 10:57:50'),
(89, NULL, 'order_create', 'order', 91, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-23 10:57:53'),
(90, NULL, 'order_create', 'order', 92, 'Создание заказа: force_eject повербанка #15', NULL, NULL, '2025-09-23 11:02:18'),
(91, NULL, 'order_create', 'order', 94, 'Создание заказа: force_eject повербанка #14', NULL, NULL, '2025-09-23 11:03:52'),
(92, NULL, 'order_create', 'order', 96, 'Создание заказа: borrow повербанка #14', NULL, NULL, '2025-09-23 11:04:13'),
(93, NULL, 'order_create', 'order', 98, 'Создание заказа: force_eject повербанка #15', NULL, NULL, '2025-09-23 11:04:33'),
(94, NULL, 'order_create', 'order', 99, 'Создание заказа: force_eject повербанка #14', NULL, NULL, '2025-09-23 11:04:37'),
(95, NULL, 'order_create', 'order', 103, 'Создание заказа: borrow повербанка #17', NULL, NULL, '2025-09-23 11:15:55'),
(96, NULL, 'order_create', 'order', 104, 'Создание заказа: borrow повербанка #17', NULL, NULL, '2025-09-23 11:16:09'),
(97, NULL, 'order_create', 'order', 105, 'Создание заказа: borrow повербанка #17', NULL, NULL, '2025-09-23 11:17:16'),
(98, NULL, 'order_create', 'order', 106, 'Создание заказа: force_eject повербанка #17', NULL, NULL, '2025-09-23 11:22:14'),
(99, NULL, 'order_create', 'order', 107, 'Создание заказа: force_eject повербанка #14', NULL, NULL, '2025-09-23 11:22:23'),
(100, NULL, 'order_create', 'order', 108, 'Создание заказа: force_eject повербанка #15', NULL, NULL, '2025-09-23 11:22:29'),
(101, NULL, 'order_create', 'order', 111, 'Создание заказа: borrow повербанка #16', NULL, NULL, '2025-09-23 11:23:00'),
(102, NULL, 'order_create', 'order', 112, 'Создание заказа: force_eject повербанка #17', NULL, NULL, '2025-09-23 11:42:41'),
(103, NULL, 'order_create', 'order', 113, 'Создание заказа: force_eject повербанка #15', NULL, NULL, '2025-09-23 12:21:11'),
(104, NULL, 'order_create', 'order', 114, 'Создание заказа: borrow повербанка #17', NULL, NULL, '2025-09-23 12:39:23'),
(105, NULL, 'order_create', 'order', 115, 'Создание заказа: borrow повербанка #14', NULL, NULL, '2025-09-23 13:39:32'),
(106, NULL, 'order_create', 'order', 116, 'Создание заказа: force_eject повербанка #17', NULL, NULL, '2025-09-24 10:41:26'),
(107, NULL, 'order_create', 'order', 117, 'Создание заказа: force_eject повербанка #15', NULL, NULL, '2025-09-24 10:42:14'),
(108, NULL, 'order_create', 'order', 118, 'Создание заказа: force_eject повербанка #14', NULL, NULL, '2025-09-24 10:44:13'),
(109, NULL, 'order_create', 'order', 119, 'Создание заказа: borrow повербанка #17', NULL, NULL, '2025-09-24 10:45:01'),
(110, NULL, 'order_create', 'order', 120, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-24 10:49:37'),
(111, NULL, 'order_create', 'order', 121, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-24 10:50:00'),
(112, NULL, 'order_create', 'order', 122, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-24 10:53:54'),
(113, NULL, 'order_create', 'order', 123, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-24 10:54:20'),
(114, NULL, 'order_create', 'order', 124, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-24 10:54:23'),
(115, NULL, 'order_create', 'order', 125, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-24 10:54:25'),
(116, NULL, 'order_create', 'order', 126, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-24 10:54:25'),
(117, NULL, 'order_create', 'order', 127, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-24 10:54:26'),
(118, NULL, 'order_create', 'order', 128, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-24 10:54:26'),
(119, NULL, 'order_create', 'order', 129, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-24 10:54:26'),
(120, NULL, 'order_create', 'order', 130, 'Создание заказа: borrow повербанка #14', NULL, NULL, '2025-09-24 11:02:08'),
(121, NULL, 'order_create', 'order', 131, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-24 11:02:20'),
(122, NULL, 'order_create', 'order', 132, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-24 11:05:25'),
(123, NULL, 'order_create', 'order', 133, 'Создание заказа: borrow повербанка #17', NULL, NULL, '2025-09-24 11:17:06'),
(124, NULL, 'order_create', 'order', 134, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-24 11:17:40'),
(125, NULL, 'order_create', 'order', 135, 'Создание заказа: force_eject повербанка #14', NULL, NULL, '2025-09-24 11:17:52'),
(126, NULL, 'order_create', 'order', 136, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-24 11:17:56'),
(127, NULL, 'order_create', 'order', 137, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-24 11:18:15'),
(128, NULL, 'order_create', 'order', 138, 'Создание заказа: borrow повербанка #17', NULL, NULL, '2025-09-24 11:18:26'),
(129, NULL, 'user_update', 'user', 10, 'Изменение статуса с pending на active', NULL, NULL, '2025-09-24 11:23:26'),
(130, NULL, 'order_create', 'order', 139, 'Создание заказа: force_eject повербанка #15', NULL, NULL, '2025-09-24 11:57:56'),
(131, NULL, 'order_create', 'order', 140, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-24 12:14:45'),
(132, NULL, 'order_create', 'order', 141, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-24 12:28:04'),
(133, NULL, 'order_create', 'order', 142, 'Создание заказа: borrow повербанка #14', NULL, NULL, '2025-09-24 13:10:50'),
(134, NULL, 'user_update', 'user', 10, 'Изменение статуса с active на pending', NULL, NULL, '2025-09-24 13:25:06'),
(135, NULL, 'user_update', 'user', 10, 'Изменение статуса с pending на active', NULL, NULL, '2025-09-24 13:26:08'),
(136, NULL, 'order_create', 'order', 143, 'Создание заказа: borrow повербанка #17', NULL, NULL, '2025-09-24 13:26:16'),
(137, NULL, 'order_create', 'order', 144, 'Создание заказа: borrow повербанка #17', NULL, NULL, '2025-09-24 13:28:20'),
(138, NULL, 'order_create', 'order', 145, 'Создание заказа: force_eject повербанка #17', NULL, NULL, '2025-09-24 13:29:35'),
(139, NULL, 'order_create', 'order', 146, 'Создание заказа: force_eject повербанка #15', NULL, NULL, '2025-09-24 13:37:28'),
(140, NULL, 'order_create', 'order', 147, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-24 13:38:17'),
(141, NULL, 'order_create', 'order', 148, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-24 13:38:45'),
(142, NULL, 'order_create', 'order', 149, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-24 13:38:46'),
(143, NULL, 'order_create', 'order', 150, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-24 13:38:48'),
(144, NULL, 'order_create', 'order', 151, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-24 13:38:49'),
(145, NULL, 'order_create', 'order', 152, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-24 13:38:49'),
(146, NULL, 'order_create', 'order', 153, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-24 13:38:49'),
(147, NULL, 'order_create', 'order', 154, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-24 13:38:50'),
(148, NULL, 'order_create', 'order', 155, 'Создание заказа: borrow повербанка #14', NULL, NULL, '2025-09-24 13:39:18'),
(149, NULL, 'order_create', 'order', 156, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-24 13:58:21'),
(150, NULL, 'order_create', 'order', 157, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-24 14:20:48'),
(151, NULL, 'order_create', 'order', 158, 'Создание заказа: borrow повербанка #14', NULL, NULL, '2025-09-24 14:20:54'),
(152, NULL, 'order_create', 'order', 159, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-24 14:21:17'),
(153, NULL, 'order_create', 'order', 160, 'Создание заказа: borrow повербанка #14', NULL, NULL, '2025-09-24 14:48:15'),
(154, NULL, 'order_create', 'order', 161, 'Создание заказа: force_eject повербанка #16', NULL, NULL, '2025-09-25 10:24:36'),
(155, NULL, 'order_create', 'order', 162, 'Создание заказа: force_eject повербанка #16', NULL, NULL, '2025-09-25 10:36:42'),
(156, NULL, 'order_create', 'order', 163, 'Создание заказа: force_eject повербанка #16', NULL, NULL, '2025-09-25 10:55:59'),
(157, NULL, 'order_create', 'order', 164, 'Создание заказа: force_eject повербанка #17', NULL, NULL, '2025-09-25 11:09:55'),
(158, NULL, 'order_create', 'order', 165, 'Создание заказа: force_eject повербанка #14', NULL, NULL, '2025-09-25 11:10:30'),
(159, NULL, 'order_create', 'order', 166, 'Создание заказа: force_eject повербанка #14', NULL, NULL, '2025-09-25 12:47:26'),
(160, NULL, 'order_create', 'order', 167, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-25 13:02:02'),
(161, NULL, 'order_create', 'order', 168, 'Создание заказа: force_eject повербанка #15', NULL, NULL, '2025-09-25 13:04:20'),
(162, NULL, 'order_create', 'order', 169, 'Создание заказа: borrow повербанка #17', NULL, NULL, '2025-09-25 13:52:43'),
(163, NULL, 'order_create', 'order', 170, 'Создание заказа: borrow повербанка #17', NULL, NULL, '2025-09-25 13:53:19'),
(164, NULL, 'order_create', 'order', 171, 'Создание заказа: borrow повербанка #14', NULL, NULL, '2025-09-25 13:54:00'),
(165, NULL, 'order_create', 'order', 172, 'Создание заказа: force_eject повербанка #14', NULL, NULL, '2025-09-25 14:05:49'),
(166, NULL, 'order_create', 'order', 173, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-26 09:38:03'),
(167, NULL, 'order_create', 'order', 176, 'Создание заказа: borrow повербанка #14', NULL, NULL, '2025-09-26 09:42:32'),
(168, NULL, 'order_create', 'order', 177, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-26 09:54:49'),
(169, NULL, 'order_create', 'order', 178, 'Создание заказа: borrow повербанка #14', NULL, NULL, '2025-09-26 10:11:24'),
(170, NULL, 'order_create', 'order', 179, 'Создание заказа: force_eject повербанка #16', NULL, NULL, '2025-09-26 10:12:58'),
(171, NULL, 'order_create', 'order', 180, 'Создание заказа: borrow повербанка #16', NULL, NULL, '2025-09-26 10:13:31'),
(172, NULL, 'order_create', 'order', 181, 'Создание заказа: borrow повербанка #16', NULL, NULL, '2025-09-26 10:15:26'),
(173, NULL, 'order_create', 'order', 182, 'Создание заказа: borrow повербанка #17', NULL, NULL, '2025-09-26 10:15:41'),
(174, NULL, 'order_create', 'order', 183, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-26 10:16:47'),
(175, NULL, 'order_create', 'order', 184, 'Создание заказа: borrow повербанка #16', NULL, NULL, '2025-09-26 10:17:41'),
(176, NULL, 'order_create', 'order', 185, 'Создание заказа: borrow повербанка #17', NULL, NULL, '2025-09-26 10:32:01'),
(177, NULL, 'order_create', 'order', 186, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-26 10:32:36'),
(178, NULL, 'order_create', 'order', 187, 'Создание заказа: borrow повербанка #16', NULL, NULL, '2025-09-26 10:39:54'),
(179, NULL, 'order_create', 'order', 188, 'Создание заказа: borrow повербанка #14', NULL, NULL, '2025-09-26 10:57:51'),
(180, NULL, 'order_create', 'order', 190, 'Создание заказа: borrow повербанка #16', NULL, NULL, '2025-09-26 10:58:06'),
(181, NULL, 'order_create', 'order', 192, 'Создание заказа: borrow повербанка #14', NULL, NULL, '2025-09-26 10:58:12'),
(182, NULL, 'order_create', 'order', 194, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-26 10:58:16'),
(183, NULL, 'order_create', 'order', 196, 'Создание заказа: borrow повербанка #17', NULL, NULL, '2025-09-26 11:44:59'),
(184, NULL, 'order_create', 'order', 198, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-26 11:45:01'),
(185, NULL, 'order_create', 'order', 200, 'Создание заказа: borrow повербанка #16', NULL, NULL, '2025-09-26 11:50:13'),
(186, NULL, 'order_create', 'order', 202, 'Создание заказа: borrow повербанка #16', NULL, NULL, '2025-09-26 12:23:08'),
(187, NULL, 'order_create', 'order', 204, 'Создание заказа: borrow повербанка #17', NULL, NULL, '2025-09-26 12:24:13'),
(188, NULL, 'order_create', 'order', 206, 'Создание заказа: borrow повербанка #14', NULL, NULL, '2025-09-26 12:24:42'),
(189, NULL, 'order_create', 'order', 208, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-26 12:25:05'),
(190, NULL, 'user_update', 'user', 11, 'Изменение статуса с pending на active', NULL, NULL, '2025-09-26 12:35:25'),
(191, NULL, 'user_update', 'user', 12, 'Изменение статуса с pending на active', NULL, NULL, '2025-09-26 12:38:19'),
(192, NULL, 'order_create', 'order', 210, 'Создание заказа: force_eject повербанка #15', NULL, NULL, '2025-09-26 12:41:13'),
(193, NULL, 'order_create', 'order', 211, 'Создание заказа: borrow повербанка #17', NULL, NULL, '2025-09-26 12:41:15'),
(194, NULL, 'order_create', 'order', 212, 'Создание заказа: borrow повербанка #16', NULL, NULL, '2025-09-26 12:41:35'),
(195, NULL, 'order_create', 'order', 214, 'Создание заказа: borrow повербанка #17', NULL, NULL, '2025-09-26 12:41:56'),
(196, NULL, 'order_create', 'order', 215, 'Создание заказа: borrow повербанка #14', NULL, NULL, '2025-09-26 12:41:57'),
(197, NULL, 'order_create', 'order', 218, 'Создание заказа: borrow повербанка #14', NULL, NULL, '2025-09-26 12:42:12'),
(198, NULL, 'order_create', 'order', 220, 'Создание заказа: return повербанка #14', NULL, NULL, '2025-09-26 12:42:29'),
(199, NULL, 'order_create', 'order', 221, 'Создание заказа: return повербанка #14', NULL, NULL, '2025-09-26 12:42:45'),
(200, NULL, 'order_create', 'order', 222, 'Создание заказа: borrow повербанка #17', NULL, NULL, '2025-09-26 13:07:12'),
(201, NULL, 'order_create', 'order', 224, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-26 13:07:38'),
(202, NULL, 'order_create', 'order', 226, 'Создание заказа: borrow повербанка #15', NULL, NULL, '2025-09-26 14:25:42'),
(203, NULL, 'order_create', 'order', 228, 'Создание заказа: borrow повербанка #16', NULL, NULL, '2025-09-26 14:25:46'),
(204, NULL, 'order_create', 'order', 229, 'Создание заказа: borrow повербанка #14', NULL, NULL, '2025-09-26 14:25:51'),
(205, NULL, 'order_create', 'order', 230, 'Создание заказа: borrow повербанка #16', NULL, NULL, '2025-09-26 14:26:50'),
(206, NULL, 'order_create', 'order', 232, 'Создание заказа: borrow повербанка #17', NULL, NULL, '2025-09-26 14:27:29'),
(207, NULL, 'order_create', 'order', 234, 'Создание заказа: borrow повербанка #14', NULL, NULL, '2025-09-26 14:29:13'),
(208, NULL, 'order_create', 'order', 236, 'Создание заказа: borrow повербанка #17', NULL, NULL, '2025-09-26 14:29:36'),
(209, NULL, 'order_create', 'order', 1, 'Создание заказа: borrow повербанка #17', NULL, NULL, '2025-09-29 10:54:17'),
(210, NULL, 'user_update', 'user', 13, 'Изменение статуса с pending на active', NULL, NULL, '2025-09-29 10:57:46'),
(211, NULL, 'order_create', 'order', 3, 'Создание заказа: borrow повербанка #17', NULL, NULL, '2025-09-29 11:03:18'),
(212, NULL, 'order_create', 'order', 5, 'Создание заказа: borrow повербанка #17', NULL, NULL, '2025-09-29 11:34:58'),
(213, NULL, 'order_create', 'order', 7, 'Создание заказа: borrow повербанка #17', NULL, NULL, '2025-09-29 11:58:10'),
(214, NULL, 'order_create', 'order', 9, 'Создание заказа: borrow повербанка #17', NULL, NULL, '2025-09-29 12:20:15'),
(215, NULL, 'order_create', 'order', 10, 'Создание заказа: force_eject повербанка #17', NULL, NULL, '2025-09-29 12:20:18'),
(216, NULL, 'order_create', 'order', 11, 'Создание заказа: borrow повербанка #17', NULL, NULL, '2025-09-29 12:21:42'),
(217, NULL, 'order_create', 'order', 12, 'Создание заказа: borrow повербанка #17', NULL, NULL, '2025-09-29 12:21:52'),
(218, NULL, 'order_create', 'order', 13, 'Создание заказа: borrow повербанка #17', NULL, NULL, '2025-09-29 12:21:54'),
(219, NULL, 'order_create', 'order', 14, 'Создание заказа: force_eject повербанка #17', NULL, NULL, '2025-09-29 12:21:56'),
(220, NULL, 'user_update', 'user', 14, 'Изменение статуса с pending на active', NULL, NULL, '2025-09-29 12:27:46'),
(221, NULL, 'order_create', 'order', 15, 'Создание заказа: borrow повербанка #17', NULL, NULL, '2025-09-29 12:27:59'),
(222, NULL, 'order_create', 'order', 17, 'Создание заказа: borrow повербанка #17', NULL, NULL, '2025-09-29 12:28:46'),
(223, NULL, 'order_create', 'order', 19, 'Создание заказа: borrow повербанка #33', NULL, NULL, '2025-09-29 13:24:46'),
(224, NULL, 'order_create', 'order', 21, 'Создание заказа: borrow повербанка #33', NULL, NULL, '2025-09-29 13:25:23'),
(225, NULL, 'order_create', 'order', 23, 'Создание заказа: borrow повербанка #35', NULL, NULL, '2025-09-29 13:39:36'),
(226, NULL, 'order_create', 'order', 24, 'Создание заказа: borrow повербанка #35', NULL, NULL, '2025-09-29 13:40:47'),
(227, NULL, 'order_create', 'order', 25, 'Создание заказа: borrow повербанка #35', NULL, NULL, '2025-09-29 13:53:24'),
(228, NULL, 'order_create', 'order', 26, 'Создание заказа: force_eject повербанка #36', NULL, NULL, '2025-09-29 13:54:57'),
(229, NULL, 'order_create', 'order', 27, 'Создание заказа: force_eject повербанка #36', NULL, NULL, '2025-09-29 13:55:08'),
(230, NULL, 'order_create', 'order', 28, 'Создание заказа: borrow повербанка #35', NULL, NULL, '2025-09-29 13:56:24'),
(231, NULL, 'order_create', 'order', 29, 'Создание заказа: borrow повербанка #35', NULL, NULL, '2025-09-29 13:56:31'),
(232, NULL, 'order_create', 'order', 30, 'Создание заказа: borrow повербанка #35', NULL, NULL, '2025-09-29 13:57:22'),
(233, NULL, 'order_create', 'order', 31, 'Создание заказа: borrow повербанка #40', NULL, NULL, '2025-09-29 14:07:53'),
(234, NULL, 'order_create', 'order', 32, 'Создание заказа: borrow повербанка #43', NULL, NULL, '2025-09-29 14:08:25'),
(235, NULL, 'order_create', 'order', 33, 'Создание заказа: borrow повербанка #43', NULL, NULL, '2025-09-29 14:09:40'),
(236, NULL, 'order_create', 'order', 34, 'Создание заказа: borrow повербанка #43', NULL, NULL, '2025-09-29 14:12:12'),
(237, NULL, 'order_create', 'order', 1, 'Создание заказа: force_eject повербанка #43', NULL, NULL, '2025-10-01 10:20:36'),
(238, NULL, 'order_create', 'order', 2, 'Создание заказа: force_eject повербанка #42', NULL, NULL, '2025-10-01 10:20:38'),
(239, NULL, 'order_create', 'order', 3, 'Создание заказа: borrow повербанка #43', NULL, NULL, '2025-10-01 10:28:36'),
(240, NULL, 'order_create', 'order', 4, 'Создание заказа: borrow повербанка #43', NULL, NULL, '2025-10-01 10:34:03'),
(241, NULL, 'order_create', 'order', 5, 'Создание заказа: borrow повербанка #42', NULL, NULL, '2025-10-01 10:34:14'),
(242, NULL, 'order_create', 'order', 6, 'Создание заказа: borrow повербанка #46', NULL, NULL, '2025-10-01 10:36:07'),
(243, NULL, 'order_create', 'order', 7, 'Создание заказа: borrow повербанка #43', NULL, NULL, '2025-10-01 10:40:50'),
(244, NULL, 'order_create', 'order', 8, 'Создание заказа: borrow повербанка #42', NULL, NULL, '2025-10-01 10:44:12'),
(245, NULL, 'order_create', 'order', 9, 'Создание заказа: borrow повербанка #42', NULL, NULL, '2025-10-01 10:48:48'),
(246, NULL, 'order_create', 'order', 10, 'Создание заказа: borrow повербанка #43', NULL, NULL, '2025-10-01 10:52:06'),
(247, NULL, 'order_create', 'order', 11, 'Создание заказа: borrow повербанка #42', NULL, NULL, '2025-10-01 10:53:50'),
(248, NULL, 'user_update', 'user', 15, 'Изменение статуса с pending на active', NULL, NULL, '2025-10-01 11:03:12'),
(249, NULL, 'order_create', 'order', 12, 'Создание заказа: borrow повербанка #42', NULL, NULL, '2025-10-01 11:03:32'),
(250, NULL, 'order_create', 'order', 13, 'Создание заказа: borrow повербанка #43', NULL, NULL, '2025-10-01 11:03:35'),
(251, NULL, 'order_create', 'order', 14, 'Создание заказа: borrow повербанка #43', NULL, NULL, '2025-10-01 11:04:53'),
(252, NULL, 'order_create', 'order', 15, 'Создание заказа: force_eject повербанка #43', NULL, NULL, '2025-10-01 11:06:00'),
(253, NULL, 'user_update', 'user', 16, 'Изменение статуса с pending на active', NULL, NULL, '2025-10-01 11:32:43'),
(254, 18, 'user_update', 'user', 18, 'Изменение статуса с pending на active', NULL, NULL, '2025-10-01 11:53:43'),
(255, 17, 'user_update', 'user', 17, 'Изменение статуса с pending на active', NULL, NULL, '2025-10-01 11:53:46'),
(256, 18, 'order_create', 'order', 16, 'Создание заказа: borrow повербанка #43', NULL, NULL, '2025-10-01 11:55:16'),
(257, 18, 'order_create', 'order', 17, 'Создание заказа: borrow повербанка #42', NULL, NULL, '2025-10-01 11:55:31'),
(258, 18, 'order_create', 'order', 18, 'Создание заказа: borrow повербанка #46', NULL, NULL, '2025-10-01 12:10:27'),
(259, 18, 'order_create', 'order', 19, 'Создание заказа: borrow повербанка #47', NULL, NULL, '2025-10-01 12:12:44'),
(260, 18, 'order_create', 'order', 20, 'Создание заказа: borrow повербанка #43', NULL, NULL, '2025-10-01 12:42:41'),
(261, NULL, 'order_create', 'order', 21, 'Создание заказа: borrow повербанка #48', NULL, NULL, '2025-10-01 14:08:04'),
(262, NULL, 'order_create', 'order', 22, 'Создание заказа: borrow повербанка #48', NULL, NULL, '2025-10-01 14:08:06'),
(263, NULL, 'order_create', 'order', 23, 'Создание заказа: borrow повербанка #48', NULL, NULL, '2025-10-01 14:08:10'),
(264, NULL, 'order_create', 'order', 24, 'Создание заказа: borrow повербанка #48', NULL, NULL, '2025-10-01 14:08:21'),
(265, NULL, 'order_create', 'order', 25, 'Создание заказа: borrow повербанка #48', NULL, NULL, '2025-10-01 14:08:23'),
(266, NULL, 'order_create', 'order', 26, 'Создание заказа: borrow повербанка #48', NULL, NULL, '2025-10-01 14:08:24'),
(267, NULL, 'order_create', 'order', 27, 'Создание заказа: force_eject повербанка #48', NULL, NULL, '2025-10-01 14:08:31'),
(268, NULL, 'order_create', 'order', 28, 'Создание заказа: borrow повербанка #48', NULL, NULL, '2025-10-01 14:10:41'),
(269, NULL, 'order_create', 'order', 29, 'Создание заказа: borrow повербанка #48', NULL, NULL, '2025-10-01 14:11:22'),
(270, NULL, 'order_create', 'order', 30, 'Создание заказа: borrow повербанка #48', NULL, NULL, '2025-10-01 14:25:16'),
(271, NULL, 'order_create', 'order', 31, 'Создание заказа: borrow повербанка #51', NULL, NULL, '2025-10-01 14:43:02'),
(272, NULL, 'order_create', 'order', 32, 'Создание заказа: borrow повербанка #49', NULL, NULL, '2025-10-01 14:48:20'),
(273, NULL, 'order_create', 'order', 33, 'Создание заказа: borrow повербанка #48', NULL, NULL, '2025-10-01 14:48:27'),
(274, NULL, 'order_create', 'order', 34, 'Создание заказа: borrow повербанка #51', NULL, NULL, '2025-10-01 14:48:29'),
(275, NULL, 'order_create', 'order', 35, 'Создание заказа: borrow повербанка #48', NULL, NULL, '2025-10-01 14:48:39'),
(276, NULL, 'order_create', 'order', 36, 'Создание заказа: borrow повербанка #51', NULL, NULL, '2025-10-01 14:48:44'),
(277, NULL, 'order_create', 'order', 37, 'Создание заказа: borrow повербанка #49', NULL, NULL, '2025-10-01 14:50:24'),
(278, NULL, 'order_create', 'order', 38, 'Создание заказа: borrow повербанка #48', NULL, NULL, '2025-10-02 07:34:28'),
(279, NULL, 'user_update', 'user', 22, 'Изменение статуса с pending на active', NULL, NULL, '2025-10-02 14:10:40'),
(280, NULL, 'user_update', 'user', 23, 'Изменение статуса с pending на active', NULL, NULL, '2025-10-02 17:08:45'),
(281, 18, 'order_create', 'order', 39, 'Создание заказа: borrow повербанка #51', NULL, NULL, '2025-10-02 17:33:55'),
(282, NULL, 'order_create', 'order', 40, 'Создание заказа: borrow повербанка #51', NULL, NULL, '2025-10-03 12:09:54'),
(283, NULL, 'user_update', 'user', 27, 'Изменение статуса с pending на active', NULL, NULL, '2025-10-03 12:19:47'),
(284, NULL, 'order_create', 'order', 41, 'Создание заказа: borrow повербанка #48', NULL, NULL, '2025-10-03 12:58:52'),
(285, NULL, 'order_create', 'order', 42, 'Создание заказа: force_eject повербанка #48', NULL, NULL, '2025-10-03 12:59:11'),
(286, NULL, 'order_create', 'order', 43, 'Создание заказа: force_eject повербанка #48', NULL, NULL, '2025-10-03 12:59:59'),
(287, NULL, 'order_create', 'order', 44, 'Создание заказа: borrow повербанка #48', NULL, NULL, '2025-10-03 13:00:20'),
(288, NULL, 'order_create', 'order', 45, 'Создание заказа: borrow повербанка #48', NULL, NULL, '2025-10-03 13:00:37'),
(289, NULL, 'order_create', 'order', 46, 'Создание заказа: borrow повербанка #48', NULL, NULL, '2025-10-03 13:00:54'),
(290, NULL, 'user_update', 'user', 31, 'Изменение статуса с pending на active', NULL, NULL, '2025-10-03 13:02:01'),
(291, 32, 'user_update', 'user', 32, 'Изменение статуса с pending на active', NULL, NULL, '2025-10-03 13:09:55'),
(292, 33, 'user_update', 'user', 33, 'Изменение статуса с pending на active', NULL, NULL, '2025-10-03 13:14:45'),
(293, 32, 'order_create', 'order', 47, 'Создание заказа: borrow повербанка #48', NULL, NULL, '2025-10-03 13:17:20'),
(294, 32, 'order_create', 'order', 48, 'Создание заказа: borrow повербанка #49', NULL, NULL, '2025-10-03 13:17:23'),
(295, 32, 'order_create', 'order', 49, 'Создание заказа: borrow повербанка #49', NULL, NULL, '2025-10-03 13:19:12'),
(296, 32, 'order_create', 'order', 50, 'Создание заказа: borrow повербанка #48', NULL, NULL, '2025-10-03 13:19:15'),
(297, 32, 'order_create', 'order', 51, 'Создание заказа: borrow повербанка #51', NULL, NULL, '2025-10-03 13:19:59'),
(298, 32, 'order_create', 'order', 52, 'Создание заказа: borrow повербанка #50', NULL, NULL, '2025-10-03 13:20:03'),
(299, 32, 'order_create', 'order', 53, 'Создание заказа: borrow повербанка #51', NULL, NULL, '2025-10-03 13:35:37'),
(300, 32, 'order_create', 'order', 54, 'Создание заказа: borrow повербанка #48', NULL, NULL, '2025-10-03 13:37:23'),
(301, 32, 'order_create', 'order', 55, 'Создание заказа: borrow повербанка #50', NULL, NULL, '2025-10-03 13:50:55'),
(302, 32, 'order_create', 'order', 56, 'Создание заказа: borrow повербанка #50', NULL, NULL, '2025-10-03 13:51:40'),
(303, 32, 'order_create', 'order', 1, 'Создание заказа: borrow повербанка #50', NULL, NULL, '2025-10-03 14:02:07'),
(304, 32, 'order_create', 'order', 2, 'Создание заказа: borrow повербанка #50', NULL, NULL, '2025-10-03 14:07:53'),
(305, 32, 'order_create', 'order', 3, 'Создание заказа: borrow повербанка #50', NULL, NULL, '2025-10-03 14:08:52'),
(306, 32, 'order_create', 'order', 4, 'Создание заказа: borrow повербанка #49', NULL, NULL, '2025-10-03 14:22:32'),
(307, 32, 'order_create', 'order', 5, 'Создание заказа: borrow повербанка #49', NULL, NULL, '2025-10-03 14:22:54'),
(308, 32, 'order_create', 'order', 6, 'Создание заказа: borrow повербанка #49', NULL, NULL, '2025-10-03 14:29:51'),
(309, 32, 'order_create', 'order', 7, 'Создание заказа: borrow повербанка #48', NULL, NULL, '2025-10-03 14:39:26'),
(310, 32, 'order_create', 'order', 8, 'Создание заказа: borrow повербанка #49', NULL, NULL, '2025-10-03 14:39:48'),
(311, 34, 'user_update', 'user', 34, 'Изменение статуса с pending на active', NULL, NULL, '2025-10-03 14:41:33'),
(312, 32, 'order_create', 'order', 9, 'Создание заказа: borrow повербанка #48', NULL, NULL, '2025-10-03 14:43:38'),
(313, 32, 'order_create', 'order', 10, 'Создание заказа: borrow повербанка #50', NULL, NULL, '2025-10-03 14:44:06'),
(314, 32, 'order_create', 'order', 11, 'Создание заказа: borrow повербанка #48', NULL, NULL, '2025-10-03 14:44:08'),
(315, 32, 'order_create', 'order', 12, 'Создание заказа: borrow повербанка #50', NULL, NULL, '2025-10-03 14:49:50'),
(316, 32, 'order_create', 'order', 13, 'Создание заказа: borrow повербанка #50', NULL, NULL, '2025-10-03 14:50:13'),
(317, 32, 'order_create', 'order', 14, 'Создание заказа: borrow повербанка #49', NULL, NULL, '2025-10-03 14:51:24'),
(318, 32, 'order_create', 'order', 15, 'Создание заказа: borrow повербанка #50', NULL, NULL, '2025-10-03 14:55:40'),
(319, 32, 'order_create', 'order', 16, 'Создание заказа: borrow повербанка #48', NULL, NULL, '2025-10-03 14:55:57'),
(320, NULL, 'user_update', 'user', 35, 'Изменение статуса с pending на active', NULL, NULL, '2025-10-05 23:01:17'),
(321, 32, 'order_create', 'order', 17, 'Создание заказа: borrow повербанка #48', NULL, NULL, '2025-10-06 07:05:49'),
(322, 32, 'order_create', 'order', 18, 'Создание заказа: borrow повербанка #50', NULL, NULL, '2025-10-06 07:06:02'),
(323, 32, 'order_create', 'order', 19, 'Создание заказа: borrow повербанка #51', NULL, NULL, '2025-10-06 07:06:12'),
(324, 32, 'order_create', 'order', 20, 'Создание заказа: borrow повербанка #49', NULL, NULL, '2025-10-06 07:26:56'),
(325, 32, 'order_create', 'order', 21, 'Создание заказа: borrow повербанка #48', NULL, NULL, '2025-10-06 07:51:50'),
(326, 32, 'order_create', 'order', 22, 'Создание заказа: borrow повербанка #52', NULL, NULL, '2025-10-06 08:07:19'),
(327, 32, 'order_create', 'order', 23, 'Создание заказа: borrow повербанка #52', NULL, NULL, '2025-10-06 08:34:29'),
(328, 32, 'order_create', 'order', 24, 'Создание заказа: borrow повербанка #53', NULL, NULL, '2025-10-06 08:35:03'),
(329, 32, 'order_create', 'order', 25, 'Создание заказа: borrow повербанка #54', NULL, NULL, '2025-10-06 08:35:43'),
(330, 32, 'order_create', 'order', 26, 'Создание заказа: borrow повербанка #55', NULL, NULL, '2025-10-06 08:36:05'),
(331, 32, 'order_create', 'order', 27, 'Создание заказа: borrow повербанка #54', NULL, NULL, '2025-10-06 08:48:53'),
(332, 32, 'order_create', 'order', 28, 'Создание заказа: borrow повербанка #52', NULL, NULL, '2025-10-06 09:21:46'),
(333, 18, 'order_create', 'order', 29, 'Создание заказа: borrow повербанка #53', NULL, NULL, '2025-10-06 09:43:35'),
(334, 18, 'order_create', 'order', 30, 'Создание заказа: borrow повербанка #52', NULL, NULL, '2025-10-06 09:43:45'),
(335, 18, 'order_create', 'order', 31, 'Создание заказа: borrow повербанка #55', NULL, NULL, '2025-10-06 09:46:53'),
(336, 18, 'order_create', 'order', 32, 'Создание заказа: borrow повербанка #54', NULL, NULL, '2025-10-06 09:47:40'),
(337, 37, 'user_update', 'user', 37, 'Изменение статуса с pending на active', NULL, NULL, '2025-10-06 09:50:06'),
(338, 37, 'order_create', 'order', 33, 'Создание заказа: borrow повербанка #55', NULL, NULL, '2025-10-06 09:51:12'),
(339, 37, 'order_create', 'order', 34, 'Создание заказа: borrow повербанка #54', NULL, NULL, '2025-10-06 09:54:26'),
(340, 18, 'order_create', 'order', 35, 'Создание заказа: borrow повербанка #55', NULL, NULL, '2025-10-06 09:58:35'),
(341, 32, 'order_create', 'order', 36, 'Создание заказа: borrow повербанка #54', NULL, NULL, '2025-10-06 10:05:18'),
(342, 32, 'order_create', 'order', 37, 'Создание заказа: borrow повербанка #53', NULL, NULL, '2025-10-06 10:06:36'),
(343, 38, 'user_update', 'user', 38, 'Изменение статуса с pending на active', NULL, NULL, '2025-10-06 10:10:42'),
(344, 38, 'order_create', 'order', 38, 'Создание заказа: borrow повербанка #52', NULL, NULL, '2025-10-06 10:12:31'),
(345, 37, 'order_create', 'order', 39, 'Создание заказа: borrow повербанка #55', NULL, NULL, '2025-10-06 10:14:11'),
(346, 32, 'order_create', 'order', 40, 'Создание заказа: borrow повербанка #54', NULL, NULL, '2025-10-06 12:46:33'),
(347, 32, 'order_create', 'order', 41, 'Создание заказа: borrow повербанка #53', NULL, NULL, '2025-10-06 12:57:00'),
(348, 32, 'order_create', 'order', 42, 'Создание заказа: borrow повербанка #55', NULL, NULL, '2025-10-06 12:57:04'),
(349, 32, 'order_create', 'order', 43, 'Создание заказа: borrow повербанка #52', NULL, NULL, '2025-10-06 12:57:07'),
(350, 32, 'order_create', 'order', 44, 'Создание заказа: borrow повербанка #54', NULL, NULL, '2025-10-06 12:59:35'),
(351, 32, 'order_create', 'order', 45, 'Создание заказа: borrow повербанка #53', NULL, NULL, '2025-10-06 13:04:36'),
(352, 32, 'order_create', 'order', 46, 'Создание заказа: borrow повербанка #55', NULL, NULL, '2025-10-06 13:04:37'),
(353, 32, 'order_create', 'order', 47, 'Создание заказа: borrow повербанка #52', NULL, NULL, '2025-10-06 13:04:39'),
(354, 32, 'order_create', 'order', 48, 'Создание заказа: borrow повербанка #54', NULL, NULL, '2025-10-06 13:04:52'),
(355, 32, 'order_create', 'order', 49, 'Создание заказа: borrow повербанка #55', NULL, NULL, '2025-10-06 13:08:58'),
(356, 32, 'order_create', 'order', 50, 'Создание заказа: borrow повербанка #54', NULL, NULL, '2025-10-06 13:22:49'),
(357, 32, 'order_create', 'order', 51, 'Создание заказа: borrow повербанка #54', NULL, NULL, '2025-10-06 13:23:05'),
(358, 18, 'order_create', 'order', 52, 'Создание заказа: borrow повербанка #54', NULL, NULL, '2025-10-07 07:04:38'),
(359, 18, 'order_create', 'order', 53, 'Создание заказа: borrow повербанка #52', NULL, NULL, '2025-10-08 19:31:19'),
(360, 18, 'order_create', 'order', 54, 'Создание заказа: borrow повербанка #55', NULL, NULL, '2025-10-08 19:31:30'),
(361, 18, 'order_create', 'order', 55, 'Создание заказа: borrow повербанка #53', NULL, NULL, '2025-10-09 07:49:45'),
(362, 18, 'order_create', 'order', 56, 'Создание заказа: borrow повербанка #54', NULL, NULL, '2025-10-09 14:30:17'),
(363, 33, 'order_create', 'order', 57, 'Создание заказа: borrow повербанка #53', NULL, NULL, '2025-10-09 19:54:00'),
(364, 32, 'order_create', 'order', 58, 'Создание заказа: borrow повербанка #52', NULL, NULL, '2025-10-13 11:07:01'),
(365, 32, 'order_create', 'order', 59, 'Создание заказа: borrow повербанка #54', NULL, NULL, '2025-10-13 11:07:06'),
(366, 33, 'order_create', 'order', 60, 'Создание заказа: borrow повербанка #54', NULL, NULL, '2025-10-13 11:49:04'),
(367, 32, 'order_create', 'order', 61, 'Создание заказа: borrow повербанка #52', NULL, NULL, '2025-10-13 11:50:09'),
(368, 33, 'order_create', 'order', 62, 'Создание заказа: borrow повербанка #55', NULL, NULL, '2025-10-13 11:57:19'),
(369, 33, 'order_create', 'order', 63, 'Создание заказа: borrow повербанка #54', NULL, NULL, '2025-10-13 12:03:08'),
(370, 32, 'user_update', 'user', 32, 'Изменение статуса с active на blocked', NULL, NULL, '2025-10-13 12:09:06'),
(371, 32, 'user_update', 'user', 32, 'Изменение статуса с blocked на active', NULL, NULL, '2025-10-13 12:09:54'),
(372, 33, 'order_create', 'order', 64, 'Создание заказа: borrow повербанка #53', NULL, NULL, '2025-10-13 12:12:58'),
(373, 32, 'order_create', 'order', 65, 'Создание заказа: borrow повербанка #54', NULL, NULL, '2025-10-13 12:22:23'),
(374, 18, 'order_create', 'order', 66, 'Создание заказа: borrow повербанка #55', NULL, NULL, '2025-10-14 07:42:45'),
(375, 18, 'order_create', 'order', 67, 'Создание заказа: borrow повербанка #53', NULL, NULL, '2025-10-14 07:42:59'),
(376, 18, 'order_create', 'order', 68, 'Создание заказа: borrow повербанка #55', NULL, NULL, '2025-10-14 10:15:21'),
(377, 33, 'order_create', 'order', 69, 'Создание заказа: borrow повербанка #52', NULL, NULL, '2025-10-14 10:29:27'),
(378, 33, 'order_create', 'order', 70, 'Создание заказа: borrow повербанка #54', NULL, NULL, '2025-10-14 11:11:50'),
(379, 33, 'order_create', 'order', 71, 'Создание заказа: borrow повербанка #55', NULL, NULL, '2025-10-14 12:48:49'),
(380, 33, 'order_create', 'order', 72, 'Создание заказа: borrow повербанка #53', NULL, NULL, '2025-10-14 12:49:43'),
(381, 32, 'order_create', 'order', 73, 'Создание заказа: borrow повербанка #55', NULL, NULL, '2025-10-14 13:06:08'),
(382, 32, 'order_create', 'order', 74, 'Создание заказа: borrow повербанка #54', NULL, NULL, '2025-10-14 13:32:11'),
(383, 32, 'order_create', 'order', 75, 'Создание заказа: borrow повербанка #55', NULL, NULL, '2025-10-14 13:36:32'),
(384, 32, 'order_create', 'order', 76, 'Создание заказа: borrow повербанка #54', NULL, NULL, '2025-10-14 13:50:44'),
(385, 33, 'order_create', 'order', 77, 'Создание заказа: borrow повербанка #55', NULL, NULL, '2025-10-14 13:57:53'),
(386, 32, 'order_create', 'order', 78, 'Создание заказа: borrow повербанка #53', NULL, NULL, '2025-10-14 13:59:06'),
(387, 32, 'order_create', 'order', 79, 'Создание заказа: borrow повербанка #54', NULL, NULL, '2025-10-14 13:59:34'),
(388, 32, 'order_create', 'order', 80, 'Создание заказа: borrow повербанка #53', NULL, NULL, '2025-10-14 14:14:49'),
(389, 32, 'order_create', 'order', 81, 'Создание заказа: borrow повербанка #52', NULL, NULL, '2025-10-14 14:15:16'),
(390, 18, 'order_create', 'order', 82, 'Создание заказа: borrow повербанка #53', NULL, NULL, '2025-10-14 17:56:34'),
(391, 32, 'order_create', 'order', 83, 'Создание заказа: borrow повербанка #54', NULL, NULL, '2025-10-16 13:00:16'),
(392, 32, 'order_create', 'order', 84, 'Создание заказа: borrow повербанка #55', NULL, NULL, '2025-10-16 13:24:53'),
(393, 33, 'order_create', 'order', 85, 'Создание заказа: borrow повербанка #52', NULL, NULL, '2025-10-16 13:36:01'),
(394, 32, 'order_create', 'order', 86, 'Создание заказа: borrow повербанка #54', NULL, NULL, '2025-10-16 13:39:17'),
(395, 32, 'order_create', 'order', 87, 'Создание заказа: borrow повербанка #55', NULL, NULL, '2025-10-16 13:43:05'),
(396, 32, 'order_create', 'order', 88, 'Создание заказа: borrow повербанка #53', NULL, NULL, '2025-10-16 13:52:57'),
(397, 32, 'order_create', 'order', 89, 'Создание заказа: borrow повербанка #54', NULL, NULL, '2025-10-16 14:08:17'),
(398, 33, 'order_create', 'order', 90, 'Создание заказа: borrow повербанка #54', NULL, NULL, '2025-10-16 14:43:10'),
(399, 33, 'order_create', 'order', 91, 'Создание заказа: borrow повербанка #55', NULL, NULL, '2025-10-16 14:48:22'),
(400, 33, 'order_create', 'order', 92, 'Создание заказа: borrow повербанка #53', NULL, NULL, '2025-10-17 07:59:21'),
(401, 32, 'order_create', 'order', 93, 'Создание заказа: borrow повербанка #54', NULL, NULL, '2025-10-17 08:02:09'),
(402, 33, 'order_create', 'order', 94, 'Создание заказа: borrow повербанка #53', NULL, NULL, '2025-10-17 08:44:25'),
(403, 33, 'order_create', 'order', 95, 'Создание заказа: borrow повербанка #54', NULL, NULL, '2025-10-17 08:47:34'),
(404, 33, 'order_create', 'order', 96, 'Создание заказа: borrow повербанка #55', NULL, NULL, '2025-10-17 08:50:58'),
(405, 33, 'order_create', 'order', 97, 'Создание заказа: borrow повербанка #53', NULL, NULL, '2025-10-17 08:55:45'),
(406, 33, 'order_create', 'order', 98, 'Создание заказа: borrow повербанка #53', NULL, NULL, '2025-10-17 09:01:00'),
(407, 32, 'order_create', 'order', 99, 'Создание заказа: borrow повербанка #54', NULL, NULL, '2025-10-17 09:49:50'),
(408, 32, 'order_create', 'order', 100, 'Создание заказа: borrow повербанка #53', NULL, NULL, '2025-10-17 09:50:01'),
(409, 32, 'order_create', 'order', 101, 'Создание заказа: borrow повербанка #55', NULL, NULL, '2025-10-17 11:47:33');

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
  `last_login_at` timestamp NULL DEFAULT NULL,
  `powerbank_limit` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Дамп данных таблицы `app_user`
--

INSERT INTO `app_user` (`user_id`, `fio`, `password_hash`, `email`, `phone_e164`, `status`, `created_at`, `last_login_at`, `powerbank_limit`) VALUES
(17, 'Andrew', '$2b$12$alFfaDYelprhzxjI69yb1eKFOPXrAdq8SPcZhVpPojMeZhAkLMuMO', 'leshkevich_a@mail.ru', '+79032564698', 'active', '2025-10-01 11:33:12', NULL, NULL),
(18, 'ааааа ааа а аа', '$2b$12$PQFslhuu4dSAOzAzIJcL4.LaXwo1e1IfskW/DiDpp1MMKCCMbk7VG', 'alex@kova.info', '+79255072534', 'active', '2025-10-01 11:52:53', '2025-10-16 13:19:23', NULL),
(32, 'CARD HOLDER', '$2b$12$P2zARO5iuvx2BWU63vROQ.ULl7KOhNxB8K/Rgk/O1tU4ac6O09sxO', 'kruglovm108@gmail.com', '+79776651226', 'active', '2025-10-03 13:03:32', '2025-10-17 14:47:01', NULL),
(33, 'Вадим Вадимвич Базаров', '$2b$12$wqwaeqnFZxNqsx4LWCHuRe6hOA64tVxwo4xEVPrH54puXoa5aDaeq', 'v.bazarov85@mail.ru', '+79013344076', 'active', '2025-10-03 13:13:40', '2025-10-18 14:35:43', 3),
(34, 'Вадим Вадимвич Базаров2', '$2b$12$RZKhpAnZBJHyKM0a8Tpd1uUzOgvKmFR2N26vWYydp48AGdpUvPvDy', 'v.bazarov142@mail.ru', '+79013344075', 'active', '2025-10-03 14:41:17', NULL, NULL),
(37, 'Алексей Ерохин', '$2b$12$rooyUBBpAdByXN5PMyWaNunv1A5Nb1A6/e3EGODHdhlY0VfZccH7a', 'geyc4all@yandex.ru', '+79099200480', 'active', '2025-10-06 09:49:26', '2025-10-07 17:25:12', NULL),
(38, 'Константин Матвеев', '$2b$12$UxwOf0SAOC/mJXX8N54OdeiJ3Lqrpf97LpZLTF4Fb8HyogBQrDin.', 'k9057695500@yandex.ru', '+79057695500', 'active', '2025-10-06 10:09:47', '2025-10-06 13:10:57', NULL);

-- --------------------------------------------------------

--
-- Структура таблицы `orders`
--

CREATE TABLE `orders` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `station_id` bigint(20) UNSIGNED NOT NULL,
  `user_id` bigint(20) UNSIGNED NOT NULL,
  `powerbank_id` bigint(20) UNSIGNED DEFAULT NULL,
  `org_unit_id` bigint(20) UNSIGNED DEFAULT NULL,
  `status` enum('borrow','return','force_eject') COLLATE utf8mb4_unicode_ci NOT NULL,
  `timestamp` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `completed_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Дамп данных таблицы `orders`
--

INSERT INTO `orders` (`id`, `station_id`, `user_id`, `powerbank_id`, `org_unit_id`, `status`, `timestamp`, `completed_at`) VALUES
(102, 16, 33, 55, 1, 'borrow', '2025-10-18 11:30:18', NULL);

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
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `default_powerbank_limit` int(11) DEFAULT '1' COMMENT 'Лимит по умолчанию для пользователей группы',
  `reminder_hours` int(11) DEFAULT '24' COMMENT 'Через сколько часов отправлять напоминание о возврате повербанка'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Дамп данных таблицы `org_unit`
--

INSERT INTO `org_unit` (`org_unit_id`, `parent_org_unit_id`, `unit_type`, `name`, `adress`, `logo_url`, `created_at`, `default_powerbank_limit`, `reminder_hours`) VALUES
(1, 1, 'group', 'Updated Test Organization', 'qweeq', NULL, '2025-09-13 09:15:54', 1, 24),
(2, 1, 'subgroup', 'NY Branch', NULL, NULL, '2025-09-13 09:15:54', 1, 24),
(3, 1, 'subgroup', 'LA Branch', NULL, NULL, '2025-09-13 09:15:54', 1, 24),
(4, NULL, 'group', 'Тралалейло тралала', 'ААААААА', 'https://avatars.mds.yandex.net/i?id=4cd8944abb77b19be26b975722925a6c2f5b62d2-4569287-images-thumbs&n=13', '2025-09-22 11:44:11', 1, 24),
(5, 4, 'subgroup', 'NY Br', 'ААААААА', NULL, '2025-09-22 11:58:51', 1, 24);

-- --------------------------------------------------------

--
-- Структура таблицы `powerbank`
--

CREATE TABLE `powerbank` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `org_unit_id` bigint(20) UNSIGNED DEFAULT NULL,
  `serial_number` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `soh` int(11) DEFAULT NULL,
  `status` enum('active','system_error','written_off','unknown') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'unknown',
  `power_er` int(11) DEFAULT NULL,
  `write_off_reason` enum('none','broken','lost','other') COLLATE utf8mb4_unicode_ci DEFAULT 'none',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Дамп данных таблицы `powerbank`
--

INSERT INTO `powerbank` (`id`, `org_unit_id`, `serial_number`, `soh`, `status`, `power_er`, `write_off_reason`, `created_at`) VALUES
(52, 1, 'DCHA54000009', 100, 'system_error', NULL, 'none', '2025-10-06 10:56:23'),
(53, 1, 'DCHA54000019', 100, 'active', NULL, 'none', '2025-10-06 10:56:23'),
(54, 1, 'DCHA54000015', 100, 'active', NULL, 'none', '2025-10-06 11:17:05'),
(55, 1, 'DCHA54000016', 100, 'active', NULL, 'none', '2025-10-06 11:17:05');

-- --------------------------------------------------------

--
-- Структура таблицы `powerbank_error`
--

CREATE TABLE `powerbank_error` (
  `id_er` int(11) NOT NULL,
  `type_error` varchar(250) COLLATE utf8mb4_unicode_ci NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Дамп данных таблицы `powerbank_error`
--

INSERT INTO `powerbank_error` (`id_er`, `type_error`) VALUES
(1, 'Аккумулятор не заряжает'),
(2, 'Сломан Type C'),
(3, 'Сломан Micro usb'),
(4, 'Сломан liting');

-- --------------------------------------------------------

--
-- Структура таблицы `slot_abnormal_reports`
--

CREATE TABLE `slot_abnormal_reports` (
  `report_id` bigint(20) UNSIGNED NOT NULL,
  `station_id` bigint(20) UNSIGNED NOT NULL,
  `slot_number` int(11) NOT NULL,
  `terminal_id` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `event_type` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `reported_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Отчеты об аномалиях слотов станций';

--
-- Дамп данных таблицы `slot_abnormal_reports`
--

INSERT INTO `slot_abnormal_reports` (`report_id`, `station_id`, `slot_number`, `terminal_id`, `event_type`, `reported_at`, `created_at`) VALUES
(49, 13, 3, '4443484154000009', '1', '2025-10-15 16:04:16', '2025-10-15 16:04:16'),
(50, 13, 3, '4443484154000009', '1', '2025-10-15 21:10:39', '2025-10-15 18:10:39'),
(51, 13, 2, '4443484154000016', '1', '2025-10-15 21:17:55', '2025-10-15 18:17:55'),
(52, 13, 3, '4443484154000009', '1', '2025-10-16 01:13:15', '2025-10-15 22:13:15'),
(53, 13, 4, '4443484154000015', '1', '2025-10-16 02:58:34', '2025-10-15 23:58:34'),
(54, 13, 4, '4443484154000015', '1', '2025-10-16 01:26:55', '2025-10-16 01:26:55'),
(55, 13, 4, '4443484154000015', '1', '2025-10-16 02:55:58', '2025-10-16 02:55:58'),
(56, 13, 2, '4443484154000016', '1', '2025-10-16 09:58:31', '2025-10-16 06:58:31'),
(57, 13, 4, '4443484154000015', '1', '2025-10-16 10:53:58', '2025-10-16 10:53:58'),
(58, 13, 3, '4443484154000009', '1', '2025-10-16 14:14:02', '2025-10-16 11:14:02'),
(59, 13, 0, 'DCHA54000015', '2', '2025-10-16 13:23:36', '2025-10-16 13:23:36'),
(60, 13, 0, 'DCHA54000009', '1', '2025-10-16 13:36:07', '2025-10-16 13:36:07'),
(67, 13, 1, '4443484154000019', '1', '2025-10-17 11:37:06', '2025-10-17 08:37:06'),
(68, 13, 4, '4443484154000015', '1', '2025-10-17 12:26:01', '2025-10-17 12:26:01'),
(69, 13, 4, '4443484154000015', '1', '2025-10-17 13:22:46', '2025-10-17 13:22:46');

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
(13, 1, 'DCHEY02504000019', '89852240400009714602\0', 8, 3, '2025-10-17 16:30:31', '2025-09-22 12:24:28', '2025-10-17 14:09:47', 'inactive'),
(16, 1, 'DCHEY02504000018', '897010260115993765FF', 4, 0, '2025-10-17 16:30:28', '2025-10-09 20:30:53', '2025-10-18 11:32:17', 'inactive');

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
(6842, 13, 53, 1, 100, 4110, 32, '2025-10-17 14:47:34'),
(6843, 13, 52, 3, 100, 4110, 33, '2025-10-17 14:47:34'),
(6844, 13, 54, 4, 100, 4110, 32, '2025-10-17 14:47:34');

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
(10, 13, 'kG7mX5zK'),
(13, 16, 'wZ8nY2xE');

-- --------------------------------------------------------

--
-- Дублирующая структура для представления `user_active_powerbanks`
-- (См. Ниже фактическое представление)
--
CREATE TABLE `user_active_powerbanks` (
`user_id` bigint(20) unsigned
,`full_name` varchar(250)
,`active_powerbanks` bigint(21)
);

-- --------------------------------------------------------

--
-- Структура таблицы `user_favorites`
--

CREATE TABLE `user_favorites` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `user_id` bigint(20) UNSIGNED NOT NULL,
  `station_id` bigint(20) UNSIGNED NOT NULL,
  `nik` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Дамп данных таблицы `user_favorites`
--

INSERT INTO `user_favorites` (`id`, `user_id`, `station_id`, `nik`, `created_at`) VALUES
(26, 37, 13, NULL, '2025-10-06 09:52:54'),
(29, 18, 13, NULL, '2025-10-08 19:31:13'),
(35, 33, 13, 'nj', '2025-10-17 08:44:22');

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
(10, 18, 1, 'service_admin', '2025-10-01 12:57:20'),
(11, 33, 1, 'group_admin', '2025-10-03 13:25:05'),
(12, 32, 1, 'service_admin', '2025-10-03 14:39:22'),
(13, 34, 1, 'user', '2025-10-03 14:48:06'),
(14, 37, NULL, 'service_admin', '2025-10-06 09:50:06'),
(15, 38, 1, 'service_admin', '2025-10-06 10:10:42'),
(16, 17, NULL, 'user', '2025-10-07 19:49:20');

-- --------------------------------------------------------

--
-- Дублирующая структура для представления `v_orders_extended`
-- (См. Ниже фактическое представление)
--
CREATE TABLE `v_orders_extended` (
`id` bigint(20) unsigned
,`powerbank_serial` varchar(64)
,`status` enum('borrow','return','force_eject')
,`timestamp` timestamp
,`completed_at` timestamp
,`station_display_name` varchar(100)
,`org_unit_name` varchar(255)
,`org_unit_address` text
,`user_fio` varchar(250)
,`user_phone` varchar(32)
,`user_id` bigint(20) unsigned
,`station_id` bigint(20) unsigned
,`org_unit_id` bigint(20) unsigned
,`powerbank_id` bigint(20) unsigned
);

-- --------------------------------------------------------

--
-- Дублирующая структура для представления `v_powerbank_status`
-- (См. Ниже фактическое представление)
--
CREATE TABLE `v_powerbank_status` (
`powerbank_id` bigint(20) unsigned
,`serial_number` varchar(64)
,`status` varchar(12)
,`station_id` bigint(20) unsigned
,`user_id` bigint(20) unsigned
,`borrow_time` timestamp
,`completed_at` timestamp
);

-- --------------------------------------------------------

--
-- Структура для представления `user_active_powerbanks`
--
DROP TABLE IF EXISTS `user_active_powerbanks`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `user_active_powerbanks`  AS SELECT `u`.`user_id` AS `user_id`, `u`.`fio` AS `full_name`, coalesce(count(`o`.`id`),0) AS `active_powerbanks` FROM (`app_user` `u` left join `orders` `o` on(((`o`.`user_id` = `u`.`user_id`) and (`o`.`status` = 'borrow') and isnull(`o`.`completed_at`)))) GROUP BY `u`.`user_id`, `u`.`fio` ;

-- --------------------------------------------------------

--
-- Структура для представления `v_orders_extended`
--
DROP TABLE IF EXISTS `v_orders_extended`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `v_orders_extended`  AS SELECT `o`.`id` AS `id`, `pb`.`serial_number` AS `powerbank_serial`, `o`.`status` AS `status`, `o`.`timestamp` AS `timestamp`, `o`.`completed_at` AS `completed_at`, coalesce(`uf`.`nik`,`s`.`box_id`) AS `station_display_name`, `ou`.`name` AS `org_unit_name`, `ou`.`adress` AS `org_unit_address`, `u`.`fio` AS `user_fio`, `u`.`phone_e164` AS `user_phone`, `o`.`user_id` AS `user_id`, `o`.`station_id` AS `station_id`, `o`.`org_unit_id` AS `org_unit_id`, `o`.`powerbank_id` AS `powerbank_id` FROM (((((`orders` `o` left join `station` `s` on((`o`.`station_id` = `s`.`station_id`))) left join `org_unit` `ou` on((`o`.`org_unit_id` = `ou`.`org_unit_id`))) left join `app_user` `u` on((`o`.`user_id` = `u`.`user_id`))) left join `powerbank` `pb` on((`o`.`powerbank_id` = `pb`.`id`))) left join `user_favorites` `uf` on(((`o`.`user_id` = `uf`.`user_id`) and (`o`.`station_id` = `uf`.`station_id`)))) ;

-- --------------------------------------------------------

--
-- Структура для представления `v_powerbank_status`
--
DROP TABLE IF EXISTS `v_powerbank_status`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `v_powerbank_status`  AS SELECT `pb`.`id` AS `powerbank_id`, `pb`.`serial_number` AS `serial_number`, (case when (`sp`.`station_id` is not null) then 'in_station' when ((`o`.`id` is not null) and (timestampdiff(HOUR,`o`.`timestamp`,now()) > coalesce(`ou`.`reminder_hours`,24))) then 'not_returned' when (`o`.`id` is not null) then 'in_use' else 'in_station' end) AS `status`, `sp`.`station_id` AS `station_id`, `o`.`user_id` AS `user_id`, `o`.`timestamp` AS `borrow_time`, `o`.`completed_at` AS `completed_at` FROM (((`powerbank` `pb` left join `station_powerbank` `sp` on((`sp`.`powerbank_id` = `pb`.`id`))) left join `orders` `o` on(((`o`.`powerbank_id` = `pb`.`id`) and (`o`.`status` = 'borrow') and isnull(`o`.`completed_at`)))) left join `org_unit` `ou` on((`ou`.`org_unit_id` = `pb`.`org_unit_id`))) ;

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
  ADD KEY `fk_orders_powerbank` (`powerbank_id`),
  ADD KEY `fk_orders_org_unit` (`org_unit_id`);

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
  ADD KEY `fk_powerbank_org` (`org_unit_id`),
  ADD KEY `power_er` (`power_er`);

--
-- Индексы таблицы `powerbank_error`
--
ALTER TABLE `powerbank_error`
  ADD PRIMARY KEY (`id_er`);

--
-- Индексы таблицы `slot_abnormal_reports`
--
ALTER TABLE `slot_abnormal_reports`
  ADD PRIMARY KEY (`report_id`),
  ADD KEY `idx_station_id` (`station_id`),
  ADD KEY `idx_reported_at` (`reported_at`),
  ADD KEY `idx_event_type` (`event_type`);

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
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=410;

--
-- AUTO_INCREMENT для таблицы `app_user`
--
ALTER TABLE `app_user`
  MODIFY `user_id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=39;

--
-- AUTO_INCREMENT для таблицы `orders`
--
ALTER TABLE `orders`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=103;

--
-- AUTO_INCREMENT для таблицы `org_unit`
--
ALTER TABLE `org_unit`
  MODIFY `org_unit_id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;

--
-- AUTO_INCREMENT для таблицы `powerbank`
--
ALTER TABLE `powerbank`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=56;

--
-- AUTO_INCREMENT для таблицы `powerbank_error`
--
ALTER TABLE `powerbank_error`
  MODIFY `id_er` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT для таблицы `slot_abnormal_reports`
--
ALTER TABLE `slot_abnormal_reports`
  MODIFY `report_id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=70;

--
-- AUTO_INCREMENT для таблицы `station`
--
ALTER TABLE `station`
  MODIFY `station_id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=17;

--
-- AUTO_INCREMENT для таблицы `station_powerbank`
--
ALTER TABLE `station_powerbank`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6845;

--
-- AUTO_INCREMENT для таблицы `station_secret_key`
--
ALTER TABLE `station_secret_key`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=14;

--
-- AUTO_INCREMENT для таблицы `user_favorites`
--
ALTER TABLE `user_favorites`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=36;

--
-- AUTO_INCREMENT для таблицы `user_role`
--
ALTER TABLE `user_role`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=17;

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
  ADD CONSTRAINT `fk_orders_org_unit` FOREIGN KEY (`org_unit_id`) REFERENCES `org_unit` (`org_unit_id`) ON DELETE SET NULL ON UPDATE CASCADE,
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
  ADD CONSTRAINT `fk_powerbank_org` FOREIGN KEY (`org_unit_id`) REFERENCES `org_unit` (`org_unit_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `powerbank_ibfk_1` FOREIGN KEY (`power_er`) REFERENCES `powerbank_error` (`id_er`);

--
-- Ограничения внешнего ключа таблицы `slot_abnormal_reports`
--
ALTER TABLE `slot_abnormal_reports`
  ADD CONSTRAINT `fk_slot_abnormal_reports_station` FOREIGN KEY (`station_id`) REFERENCES `station` (`station_id`) ON DELETE CASCADE;

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
