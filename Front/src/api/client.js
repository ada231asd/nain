import axios from 'axios'
import { getCurrentConfig, getEndpoint } from './config'

// Получаем текущую конфигурацию
const config = getCurrentConfig()

// Создаем единый экземпляр axios с конфигурацией
const apiClient = axios.create({
  baseURL: config.baseURL,
  timeout: config.timeout,
  headers: config.headers
})

// Перехватчик запросов
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // Request logging disabled

    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Перехватчик ответов
apiClient.interceptors.response.use(
  (response) => {
    // Логирование успешных ответов (в DEV режиме или для авторизации)
    if (import.meta.env.DEV || response.config.url?.includes('/login') || response.config.url?.includes('/register')) {
      if (response.data) {
       
      }
    }
    return response.data
  },
  async (error) => {
    // Единообразная обработка ошибок
    let errorMessage = 'Произошла ошибка'
    let errorStatus = 500
    
    if (error.response) {
      // Сервер ответил с ошибкой
      errorStatus = error.response.status
      errorMessage = error.response.data?.error || error.response.data?.message || error.response.statusText
      
      // Обработка специфических HTTP статусов
      switch (errorStatus) {
        case 401:
          errorMessage = 'Неавторизован'
          break
          
        case 403:
          errorMessage = 'Доступ запрещен'
          break
          
        case 404:
          errorMessage = 'Ресурс не найден'
          break
          
        case 422:
          errorMessage = 'Некорректные данные'
          break
          
        case 429:
          errorMessage = 'Слишком много запросов. Попробуйте позже'
          break
          
        case 500:
          errorMessage = 'Внутренняя ошибка сервера'
          break
          
        case 502:
        case 503:
        case 504:
          errorMessage = 'Сервер временно недоступен'
          try {
            window.dispatchEvent(new CustomEvent('api:server-down', {
              detail: { message: 'Подождите, сервер отдыхает', status: errorStatus }
            }))
          } catch {}
          break
      }
    } else if (error.request) {
      // Запрос был отправлен, но ответ не получен
      errorMessage = 'Сервер не отвечает'
      errorStatus = 0
      try {
        window.dispatchEvent(new CustomEvent('api:server-down', {
          detail: { message: 'Подождите, сервер отдыхает', status: errorStatus }
        }))
      } catch {}
    } else {
      // Ошибка при настройке запроса
      errorMessage = 'Ошибка настройки запроса'
      errorStatus = 0
    }
    
    // Error logging disabled
    
    // Возвращаем стандартизированную ошибку
    return Promise.reject({
      message: errorMessage,
      status: errorStatus,
      code: error.code,
      originalError: error
    })
  }
)

// Добавляем вспомогательные методы к API клиенту
apiClient.getEndpoint = getEndpoint

// Экспортируем единый API клиент
export default apiClient

// Экспортируем также базовый URL для использования в других местах
export const API_BASE_URL = config.baseURL 
