/**
 * Утилиты для работы с временем в московском часовом поясе
 */

/**
 * Форматирует дату в московском времени
 * @param {string|Date} dateString - Дата в ISO формате или объект Date
 * @param {Object} options - Опции форматирования
 * @returns {string} Отформатированная дата
 */
export function formatMoscowTime(dateString, options = {}) {
  if (!dateString) return '—'
  
  const date = typeof dateString === 'string' ? new Date(dateString) : dateString
  
  // Проверяем, что дата валидна
  if (isNaN(date.getTime())) return '—'
  
  const defaultOptions = {
    day: '2-digit',
    month: '2-digit',
    year: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    timeZone: 'Europe/Moscow',
    hour12: false
  }
  
  const formatOptions = { ...defaultOptions, ...options }
  
  // Используем встроенное форматирование по таймзоне Москвы
  return new Intl.DateTimeFormat('ru-RU', formatOptions).format(date)
}

/**
 * Форматирует только время в московском часовом поясе
 * @param {string|Date} dateString - Дата в ISO формате или объект Date
 * @returns {string} Отформатированное время
 */
export function formatMoscowTimeOnly(dateString) {
  return formatMoscowTime(dateString, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

/**
 * Форматирует только дату в московском часовом поясе
 * @param {string|Date} dateString - Дата в ISO формате или объект Date
 * @returns {string} Отформатированная дата
 */
export function formatMoscowDateOnly(dateString) {
  return formatMoscowTime(dateString, {
    day: '2-digit',
    month: '2-digit',
    year: '2-digit'
  })
}

/**
 * Получает относительное время (например, "5 минут назад")
 * @param {string|Date} dateString - Дата в ISO формате или объект Date
 * @returns {string} Относительное время
 */
export function getRelativeTime(dateString) {
  if (!dateString) return ''
  
  const date = typeof dateString === 'string' ? new Date(dateString) : dateString
  const now = new Date()
  
  // Разницу считаем в UTC, чтобы не зависеть от локали
  const diffMs = now.getTime() - date.getTime()
  const diffMinutes = Math.floor(diffMs / (1000 * 60))
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  
  if (diffMinutes < 1) return 'только что'
  if (diffMinutes < 60) return `${diffMinutes} мин назад`
  if (diffHours < 24) return `${diffHours} ч назад`
  if (diffDays < 7) return `${diffDays} дн назад`
  return 'давно'
}

/**
 * Получает полное относительное время с датой
 * @param {string|Date} dateString - Дата в ISO формате или объект Date
 * @returns {Object} Объект с полным временем и относительным временем
 */
export function getFullRelativeTime(dateString) {
  return {
    fullTime: formatMoscowTime(dateString),
    relativeTime: getRelativeTime(dateString)
  }
}

/**
 * Проверяет, является ли дата сегодняшней в московском времени
 * @param {string|Date} dateString - Дата в ISO формате или объект Date
 * @returns {boolean} true если дата сегодняшняя
 */
export function isToday(dateString) {
  if (!dateString) return false
  
  const date = typeof dateString === 'string' ? new Date(dateString) : dateString
  const now = new Date()
  
  // Московское время
  const moscowNow = new Date(now.getTime() + (3 * 60 * 60 * 1000))
  const moscowDate = new Date(date.getTime() + (3 * 60 * 60 * 1000))
  
  return moscowNow.toDateString() === moscowDate.toDateString()
}

/**
 * Получает текущее московское время
 * @returns {Date} Текущее время в московском часовом поясе
 */
export function getCurrentMoscowTime() {
  const now = new Date()
  return new Date(now.getTime() + (3 * 60 * 60 * 1000))
}
