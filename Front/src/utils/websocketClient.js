// WebSocket клиент для real-time уведомлений
class WebSocketClient {
  constructor() {
    this.ws = null
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 1000
    this.listeners = new Map()
    this.isConnected = false
    this.isConnecting = false
    this.shouldReconnect = true
  }

  connect(url) {
    // Определяем URL по умолчанию динамически, чтобы избегать mixed content
    let resolvedUrl = url
    if (!resolvedUrl) {
      try {
        // Проверяем переменную окружения для WebSocket URL
        const envWsUrl = import.meta.env.VITE_WS_URL
        if (envWsUrl) {
          resolvedUrl = envWsUrl
        } else {
          // В dev режиме используем прокси на том же хосте что и API
        
          const isHttps = typeof window !== 'undefined' && window.location.protocol === 'https:'
          const protocol = isHttps ? 'wss:' : 'ws:'
          
          // Используем адрес API сервера для WebSocket (порт 8001)
          // В dev режиме это будет текущий хост
     
          if (import.meta.env.DEV) {
        
            resolvedUrl = 'ws://192.168.10.38:8001/ws'
          } else {
       
            const host = typeof window !== 'undefined' ? window.location.host : 'localhost:8001'
            resolvedUrl = `${protocol}//${host}/ws`
          }
        }
      } catch (e) {
        // Fallback на localhost если что-то пошло не так
        resolvedUrl = 'ws://192.168.10.38:8001/ws'
      }
    }
    // Предотвращаем множественные соединения
    if (this.isConnected || this.isConnecting) {
      console.log('WebSocket уже подключен или подключается')
      return
    }

    try {
      this.isConnecting = true
      this.ws = new WebSocket(resolvedUrl)
      
      this.ws.onopen = (event) => {
        console.log('WebSocket соединение установлено')
        this.isConnected = true
        this.isConnecting = false
        this.reconnectAttempts = 0
        this.emit('connected', event)
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          this.emit('message', data)
          
          // Обрабатываем специфичные типы сообщений
          if (data.type === 'new_slot_abnormal_report') {
            this.emit('new_abnormal_report', data.data)
          } else if (data.type === 'recent_abnormal_reports') {
            this.emit('recent_reports', data.data)
          } else if (data.type === 'borrow_success') {
            this.emit('borrow_success', data)
          } else if (data.type === 'borrow_failure') {
            this.emit('borrow_failure', data)
          } else if (data.event === 'powerbank_borrow_result') {
            // Обрабатываем уведомления о результате выдачи повербанка
            if (data.type === 'borrow_success') {
              this.emit('borrow_success', data)
            } else if (data.type === 'borrow_failure') {
              this.emit('borrow_failure', data)
            }
          } else if (data.type === 'error') {
            this.emit('error', data.message)
          }
        } catch (error) {
          console.error('Ошибка парсинга WebSocket сообщения:', error)
          this.emit('error', 'Ошибка парсинга сообщения')
        }
      }

      this.ws.onclose = (event) => {
        console.log('WebSocket соединение закрыто')
        this.isConnected = false
        this.isConnecting = false
        this.emit('disconnected', event)
        
        // Попытка переподключения только если это не было принудительное отключение
        if (this.shouldReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++
          console.log(`Попытка переподключения ${this.reconnectAttempts}/${this.maxReconnectAttempts}`)
          setTimeout(() => {
            this.connect(resolvedUrl)
          }, this.reconnectDelay * this.reconnectAttempts)
        } else if (this.reconnectAttempts >= this.maxReconnectAttempts) {
          console.error('Превышено максимальное количество попыток переподключения')
          this.emit('reconnect_failed')
        }
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket ошибка:', error)
        this.emit('error', error)
      }

    } catch (error) {
      console.error('Ошибка создания WebSocket соединения:', error)
      this.emit('error', error)
    }
  }

  disconnect() {
    this.shouldReconnect = false
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.isConnected = false
    this.isConnecting = false
    console.log('WebSocket отключен')
  }

  send(data) {
    if (this.ws && this.isConnected) {
      try {
        this.ws.send(JSON.stringify(data))
      } catch (error) {
        console.error('Ошибка отправки WebSocket сообщения:', error)
        this.emit('error', error)
      }
    } else {
      console.warn('WebSocket не подключен')
    }
  }

  // Подписка на события
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, [])
    }
    this.listeners.get(event).push(callback)
  }

  // Отписка от событий
  off(event, callback) {
    if (this.listeners.has(event)) {
      const callbacks = this.listeners.get(event)
      const index = callbacks.indexOf(callback)
      if (index > -1) {
        callbacks.splice(index, 1)
      }
    }
  }

  // Эмиссия событий
  emit(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(callback => {
        try {
          callback(data)
        } catch (error) {
          console.error(`Ошибка в обработчике события ${event}:`, error)
        }
      })
    }
  }

  // Запрос последних аномалий
  getRecentReports(limit = 10) {
    if (this.isConnected) {
      this.send({
        type: 'get_recent',
        limit: limit
      })
    } else {
      // Если не подключены, ждем подключения и повторяем запрос
      this.on('connected', () => {
        this.send({
          type: 'get_recent',
          limit: limit
        })
      })
    }
  }

  // Ping для проверки соединения
  ping() {
    this.send({
      type: 'ping'
    })
  }

  // Ожидание подключения
  waitForConnection(timeout = 10000) {
    return new Promise((resolve, reject) => {
      if (this.isConnected) {
        resolve()
        return
      }

      // Если уже подключаемся, ждем завершения
      if (this.isConnecting) {
        const checkConnection = () => {
          if (this.isConnected) {
            resolve()
          } else if (!this.isConnecting) {
            reject(new Error('WebSocket connection failed'))
          } else {
            setTimeout(checkConnection, 100)
          }
        }
        checkConnection()
        return
      }

      const timeoutId = setTimeout(() => {
        reject(new Error('WebSocket connection timeout'))
      }, timeout)

      this.on('connected', () => {
        clearTimeout(timeoutId)
        resolve()
      })

      this.on('error', (error) => {
        clearTimeout(timeoutId)
        reject(error)
      })
    })
  }

  // Проверка, нужно ли подключаться
  shouldConnect() {
    return !this.isConnected && !this.isConnecting && this.shouldReconnect
  }
}

// Создаем глобальный экземпляр
const websocketClient = new WebSocketClient()

export default websocketClient