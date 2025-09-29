// Конфигурация API
const getDefaultBaseURL = () => {
  try {
    // Prefer relative path so Vite proxy or same-origin backend can handle requests
    if (typeof window !== 'undefined') {
      return '/api'
    }
  } catch {}
  // Fallbacks for SSR/build tools: prefer common localhost ports
  return import.meta.env.VITE_PY_BACKEND_URL?.replace(/\/?$/, '/api')
    || 'http://localhost:8000/'
}

export const API_CONFIG = {
  // Базовый URL для API
  baseURL: import.meta.env.VITE_API_BASE_URL || getDefaultBaseURL(),
  
  // Таймаут для запросов (в миллисекундах)
  timeout: 1000,
  
  // Заголовки по умолчанию
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  },
  
  // Настройки для разных окружений
  environments: {
    development: {
      baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
      timeout: 10000,
      enableLogging: true
    },
  },
  
  // Endpoints для разных модулей
  endpoints: {
    stations: {
      list: '/stations',
      detail: '/stations/:id',
      search: '/stations/search',
      favorites: '/stations/favorites',
      takeBattery: '/stations/take-battery',
      returnBattery: '/stations/return-battery'
    },
    users: {
      list: '/users',
      detail: '/users/:id',
      create: '/users',
      update: '/users/:id',
      delete: '/users/:id'
    }
  },
  
  // Настройки аутентификации
  
  // Настройки обработки ошибок
  errorHandling: {
    retryAttempts: 3,
    retryDelay: 1000,
    showNotifications: true,
    logErrors: true
  }
}

// Получение текущей конфигурации в зависимости от окружения
export const getCurrentConfig = () => {
  const env = import.meta.env.MODE || 'development'
  return {
    ...API_CONFIG,
    ...API_CONFIG.environments[env]
  }
}

// Вспомогательные функции для работы с конфигурацией
export const getEndpoint = (module, action, params = {}) => {
  let endpoint = API_CONFIG.endpoints[module]?.[action]
  
  if (!endpoint) {
    throw new Error(`Endpoint not found: ${module}.${action}`)
  }
  
  // Заменяем параметры в URL
  Object.keys(params).forEach(key => {
    endpoint = endpoint.replace(`:${key}`, params[key])
  })
  
  return endpoint
}

// Экспорт по умолчанию
export default API_CONFIG

