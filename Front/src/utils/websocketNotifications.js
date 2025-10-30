// WebSocket сервис для получения уведомлений от сервера
import { API_CONFIG } from '../api/config'

class WebSocketNotificationService {
  constructor() {
    this.ws = null
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 3000
    this.isConnecting = false
    this.shouldReconnect = true
    this.pingInterval = null
    this.idleTimeout = null
    this.idleTimeoutDuration = 3600000 // 60 минут неактивности (временно увеличено для production)
    this.lastActivityTime = null
    this.token = null // Сохраняем токен для переподключения
    this.dataUpdateCallbacks = [] // Колбэки для обновления данных
    this.setupPageVisibilityHandling() // Обработка видимости страницы для мобильных
  }

  /**
   * Подключиться к WebSocket серверу
   * @param {string} token - JWT токен для авторизации
   */
  connect(token) {
    if (!token) {
      console.warn('WebSocket: Токен не предоставлен')
      return
    }
    
    // Сохраняем токен для переподключения
    this.token = token

    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      console.log('WebSocket: Уже подключен или подключается')
      return
    }

    if (this.isConnecting) {
      console.log('WebSocket: Подключение уже в процессе')
      return
    }

    this.isConnecting = true
    this.shouldReconnect = true

    try {
      // Получаем базовый URL и преобразуем в WebSocket URL
      const baseURL = API_CONFIG.baseURL || '/api'
      
      let wsURL
      if (baseURL.startsWith('http://') || baseURL.startsWith('https://')) {
        // Абсолютный URL - преобразуем протокол
        wsURL = baseURL
          .replace('http://', 'ws://')
          .replace('https://', 'wss://')
          .replace(/\/api\/?$/, '') // убираем /api из конца пути
      } else {
        // Относительный URL - используем текущий хост (для работы через Vite proxy)
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        const host = window.location.host
        wsURL = `${protocol}//${host}`
      }
      
      const url = `${wsURL}/api/ws/notifications?token=${token}`
      
      console.log('WebSocket: Подключаемся к', url)
      console.log('WebSocket: Базовый URL:', baseURL)
      console.log('WebSocket: Протокол:', window.location.protocol)
      console.log('WebSocket: Хост:', window.location.host)
      this.ws = new WebSocket(url)

      this.ws.onopen = () => {
        console.log('✅ WebSocket: Подключен')
        this.isConnecting = false
        this.reconnectAttempts = 0
        this.updateActivity()
          
        // Запускаем периодический ping
        this.startPing()
        
        // Запускаем отслеживание неактивности
        this.startIdleMonitoring()
      }

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          console.log('WebSocket: Получено сообщение', message)
          
          // Обновляем время последней активности
          this.updateActivity()
          
          this.handleMessage(message)
        } catch (error) {
          console.error('WebSocket: Ошибка парсинга сообщения', error)
        }
      }

      this.ws.onerror = (error) => {
        console.error('❌ WebSocket: Ошибка подключения', error)
        console.error('WebSocket: Попытка подключения к:', url)
        this.isConnecting = false
      }

      this.ws.onclose = (event) => {
        console.log(`❌ WebSocket: Отключен (код: ${event.code}, причина: ${event.reason || 'не указана'})`)
        this.isConnecting = false
        this.stopPing()
        this.stopIdleMonitoring()
        
        // Если закрытие по таймауту неактивности (код 1000 с нашей причиной)
        if (event.code === 1000 && event.reason === 'idle_timeout') {
          console.log('⏰ WebSocket: Закрыт по таймауту неактивности')
          // Не переподключаемся сразу, ждем следующего события
          return
        }
        
        // Код 1000 означает нормальное закрытие, но если это не запрошено нами, переподключаемся
        // Код 1001 - сервер ушел
        // Код 1006 - соединение разорвано аномально
        const shouldReconnectNow = this.shouldReconnect && (
          event.code === 1000 ||  // Нормальное закрытие (но не запрошенное нами)
          event.code === 1001 ||  // Going Away
          event.code === 1006 ||  // Abnormal Closure
          event.code === 1011     // Server Error
        )
        
        // Автоматическое переподключение
        if (shouldReconnectNow && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++
          console.log(`WebSocket: Переподключение через ${this.reconnectDelay / 1000}с (попытка ${this.reconnectAttempts}/${this.maxReconnectAttempts})`)
          
          setTimeout(() => {
            if (this.shouldReconnect && this.token) {
              this.connect(this.token)
            }
          }, this.reconnectDelay)
        } else if (this.reconnectAttempts >= this.maxReconnectAttempts) {
          console.error('WebSocket: Превышено максимальное количество попыток переподключения')
        }
      }
    } catch (error) {
      console.error('WebSocket: Ошибка создания подключения', error)
      this.isConnecting = false
    }
  }

  /**
   * Обработка входящих сообщений
   */
  handleMessage(message) {
    switch (message.type) {
      case 'connected':
        console.log('WebSocket: Успешное подключение подтверждено')
        break

      case 'powerbank_returned':
        this.handlePowerbankReturned(message.data)
        break

      case 'pong':
        // Ответ на ping
        break

      default:
        console.log('WebSocket: Неизвестный тип сообщения', message.type)
    }
  }

  /**
   * Обработка уведомления о возврате powerbank
   */
  handlePowerbankReturned(data) {
    console.log('🔋 Powerbank возвращен:', data)
    
    // Обновляем активность при получении важного уведомления
    this.updateActivity()
    
    // Показываем уведомление пользователю
    this.showNotification({
      title: data.title || 'Спасибо за возврат!',
      message: data.alert || 'Заказ успешно закрыт.',
      type: 'success',
      data: data
    })
    
    // КРИТИЧНО: Триггерим обновление данных во всех подписанных компонентах
    this.triggerDataUpdate({
      type: 'powerbank_returned',
      stationId: data.station_id,
      data: data
    })
  }

  /**
   * Показать уведомление пользователю
   */
  showNotification({ title, message, type, data }) {
    // Попытка использовать браузерные уведомления
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification(title, {
        body: message,
        icon: '/favicon.ico',
        tag: `powerbank-${data.order_id}`
      })
    }
    
    // Также показываем визуальное уведомление в UI
    this.showUINotification({ title, message, type, data })
  }

  /**
   * Показать визуальное уведомление в UI
   */
  showUINotification({ title, message, type, data }) {
    // Создаем простое уведомление
    const notification = document.createElement('div')
    notification.className = `ws-notification ws-notification-${type}`
    notification.innerHTML = `
      <div class="ws-notification-content">
        <div class="ws-notification-title">${title}</div>
        <div class="ws-notification-message">${message}</div>
        <div class="ws-notification-close" onclick="this.parentElement.parentElement.remove()">×</div>
      </div>
    `
    
    // Добавляем стили, если их еще нет
    if (!document.getElementById('ws-notification-styles')) {
      const style = document.createElement('style')
      style.id = 'ws-notification-styles'
      style.textContent = `
        .ws-notification {
          position: fixed;
          top: 20px;
          right: 20px;
          min-width: 300px;
          max-width: 400px;
          padding: 16px 20px;
          background: white;
          border-radius: 8px;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
          z-index: 10000;
          animation: slideInRight 0.3s ease-out;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        
        .ws-notification-success {
          border-left: 4px solid #28a745;
        }
        
        .ws-notification-content {
          position: relative;
        }
        
        .ws-notification-title {
          font-weight: 600;
          font-size: 16px;
          color: #28a745;
          margin-bottom: 8px;
        }
        
        .ws-notification-message {
          font-size: 14px;
          color: #333;
          line-height: 1.4;
        }
        
        .ws-notification-close {
          position: absolute;
          top: -8px;
          right: -8px;
          width: 24px;
          height: 24px;
          background: #f0f0f0;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          font-size: 18px;
          color: #666;
          user-select: none;
          transition: background 0.2s;
        }
        
        .ws-notification-close:hover {
          background: #e0e0e0;
        }
        
        @keyframes slideInRight {
          from {
            transform: translateX(400px);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }
      `
      document.head.appendChild(style)
    }
    
    document.body.appendChild(notification)
    
    // Автоматически убираем уведомление через 5 секунд
    setTimeout(() => {
      notification.style.animation = 'slideInRight 0.3s ease-out reverse'
      setTimeout(() => notification.remove(), 300)
    }, 5000)
  }

  /**
   * Обновить время последней активности
   */
  updateActivity() {
    this.lastActivityTime = Date.now()
  }

  /**
   * Запустить отслеживание неактивности
   */
  startIdleMonitoring() {
    this.stopIdleMonitoring()
    
    this.idleTimeout = setInterval(() => {
      if (!this.lastActivityTime) return
      
      const idleTime = Date.now() - this.lastActivityTime
      
      if (idleTime >= this.idleTimeoutDuration) {
        console.log(`⏰ WebSocket: Неактивность ${Math.round(idleTime / 1000)}с, закрываем соединение`)
        this.closeByIdleTimeout()
      }
    }, 10000) // проверяем каждые 10 секунд
  }

  /**
   * Остановить отслеживание неактивности
   */
  stopIdleMonitoring() {
    if (this.idleTimeout) {
      clearInterval(this.idleTimeout)
      this.idleTimeout = null
    }
  }

  /**
   * Закрыть соединение по таймауту неактивности
   */
  closeByIdleTimeout() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.shouldReconnect = false // Временно отключаем переподключение
      this.ws.close(1000, 'idle_timeout')
      this.shouldReconnect = true // Включаем обратно
      console.log('💤 WebSocket: Соединение закрыто из-за неактивности, будет переподключено при необходимости')
    }
  }

  /**
   * Переподключиться если не подключен
   */
  reconnectIfNeeded() {
    if (!this.ws || this.ws.readyState === WebSocket.CLOSED) {
      if (this.token) {
        console.log('🔄 WebSocket: Переподключение после неактивности')
        this.reconnectAttempts = 0 // Сбрасываем счетчик попыток
        this.connect(this.token)
      }
    }
  }

  /**
   * Запустить периодический ping
   */
  startPing() {
    this.stopPing()
    
    this.pingInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send('ping')
        this.updateActivity() // Ping тоже считается активностью
      }
    }, 30000) // каждые 30 секунд
  }

  /**
   * Остановить периодический ping
   */
  stopPing() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval)
      this.pingInterval = null
    }
  }

  /**
   * Отключиться от WebSocket
   */
  disconnect() {
    this.shouldReconnect = false
    this.stopPing()
    this.stopIdleMonitoring()
    
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    
    this.token = null
    console.log('WebSocket: Отключен вручную')
  }

  /**
   * Запросить разрешение на браузерные уведомления
   */
  async requestNotificationPermission() {
    if ('Notification' in window && Notification.permission === 'default') {
      const permission = await Notification.requestPermission()
      console.log('Разрешение на уведомления:', permission)
      return permission === 'granted'
    }
    return Notification.permission === 'granted'
  }

  /**
   * Зарегистрировать колбэк для обновления данных
   * @param {Function} callback - Функция, которая будет вызвана при обновлении данных
   * @returns {Function} Функция для отмены регистрации колбэка
   */
  onDataUpdate(callback) {
    if (typeof callback !== 'function') {
      console.warn('WebSocket: Колбэк должен быть функцией')
      return () => {}
    }
    
    this.dataUpdateCallbacks.push(callback)
    console.log(`WebSocket: Зарегистрирован колбэк обновления данных (всего: ${this.dataUpdateCallbacks.length})`)
    
    // Возвращаем функцию для отмены регистрации
    return () => {
      const index = this.dataUpdateCallbacks.indexOf(callback)
      if (index > -1) {
        this.dataUpdateCallbacks.splice(index, 1)
        console.log(`WebSocket: Колбэк удален (осталось: ${this.dataUpdateCallbacks.length})`)
      }
    }
  }

  /**
   * Триггерить обновление данных во всех подписанных компонентах
   * @param {Object} updateInfo - Информация об обновлении
   */
  triggerDataUpdate(updateInfo) {
    console.log('🔄 WebSocket: Триггерим обновление данных:', updateInfo)
    console.log(`🔄 WebSocket: Количество колбэков: ${this.dataUpdateCallbacks.length}`)
    
    this.dataUpdateCallbacks.forEach((callback, index) => {
      try {
        callback(updateInfo)
        console.log(`✅ WebSocket: Колбэк ${index + 1} выполнен успешно`)
      } catch (error) {
        console.error(`❌ WebSocket: Ошибка в колбэке ${index + 1}:`, error)
      }
    })
  }

  /**
   * Настройка обработки видимости страницы (Page Visibility API)
   * Особенно важно для мобильных устройств
   */
  setupPageVisibilityHandling() {
    if (typeof document === 'undefined') return

    // Обработка изменения видимости страницы
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        console.log('📱 Страница скрыта (пользователь переключился или свернул приложение)')
        // Страница скрыта - можно приостановить некоторые операции
      } else {
        console.log('📱 Страница видима (пользователь вернулся)')
        // Страница снова видима - переподключаемся если нужно и обновляем данные
        this.handlePageVisible()
      }
    })

    // Для iOS Safari - дополнительная обработка событий
    window.addEventListener('pageshow', (event) => {
      if (event.persisted) {
        console.log('📱 Страница восстановлена из bfcache (iOS)')
        this.handlePageVisible()
      }
    })

    // Обработка фокуса окна (дополнительная страховка)
    window.addEventListener('focus', () => {
      console.log('📱 Окно получило фокус')
      this.handlePageVisible()
    })

    // Обработка сетевых событий (особенно важно для мобильных)
    window.addEventListener('online', () => {
      console.log('📱 Сеть восстановлена')
      // Переподключаемся и обновляем данные
      setTimeout(() => {
        this.reconnectIfNeeded()
        this.triggerDataUpdate({
          type: 'network_restored',
          reason: 'connection_online'
        })
      }, 1000) // Небольшая задержка для стабилизации соединения
    })

    window.addEventListener('offline', () => {
      console.log('📱 Сеть потеряна')
    })

    console.log('📱 Page Visibility API и сетевые события настроены')
  }

  /**
   * Обработка возвращения пользователя на страницу
   */
  handlePageVisible() {
    // Обновляем активность
    this.updateActivity()

    // Переподключаемся к WebSocket если отключены
    this.reconnectIfNeeded()

    // Триггерим обновление данных во всех компонентах
    this.triggerDataUpdate({
      type: 'page_visible',
      reason: 'user_returned'
    })
  }
}

// Создаем singleton экземпляр
const websocketNotificationService = new WebSocketNotificationService()

export default websocketNotificationService

