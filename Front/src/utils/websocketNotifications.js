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
      const baseURL = API_CONFIG.baseURL || 'http://localhost:8000/api'
      
      let wsURL
      if (baseURL.startsWith('http://') || baseURL.startsWith('https://')) {
        // Абсолютный URL - преобразуем протокол
        wsURL = baseURL
          .replace('http://', 'ws://')
          .replace('https://', 'wss://')
          .replace('/api', '') // убираем /api из пути
      } else {
        // Относительный URL - используем текущий хост
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        const host = window.location.host
        wsURL = `${protocol}//${host}`
      }
      
      const url = `${wsURL}/api/ws/notifications?token=${token}`
      
      console.log('WebSocket: Подключаемся к', url)
      this.ws = new WebSocket(url)

      this.ws.onopen = () => {
        console.log('✅ WebSocket: Подключен')
        this.isConnecting = false
        this.reconnectAttempts = 0
        
        // Запускаем периодический ping
        this.startPing()
      }

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          console.log('WebSocket: Получено сообщение', message)
          
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
        
        // Автоматическое переподключение
        if (this.shouldReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++
          console.log(`WebSocket: Переподключение через ${this.reconnectDelay / 1000}с (попытка ${this.reconnectAttempts}/${this.maxReconnectAttempts})`)
          
          setTimeout(() => {
            if (this.shouldReconnect) {
              this.connect(token)
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
    
    // Показываем уведомление пользователю
    this.showNotification({
      title: data.title || 'Спасибо за возврат!',
      message: data.alert || 'Заказ успешно закрыт.',
      type: 'success',
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
   * Запустить периодический ping
   */
  startPing() {
    this.stopPing()
    
    this.pingInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send('ping')
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
    
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    
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
}

// Создаем singleton экземпляр
const websocketNotificationService = new WebSocketNotificationService()

export default websocketNotificationService

