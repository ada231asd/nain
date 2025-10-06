<template>
  <div class="notifications-container">
    <!-- WebSocket статус -->
    <div class="websocket-status" :class="{ connected: isConnected, disconnected: !isConnected }">
      <span class="status-indicator"></span>
      {{ isConnected ? 'Подключено' : 'Отключено' }}
    </div>
    
    <!-- Уведомления -->
    <div class="notifications-list" v-if="notifications.length > 0">
      <div 
        v-for="notification in notifications" 
        :key="notification.id"
        class="notification"
        :class="getNotificationClass(notification)"
        @click="removeNotification(notification.id)"
      >
        <div class="notification-content">
          <div class="notification-title">
            {{ getNotificationTitle(notification) }}
          </div>
          <div class="notification-message">
            {{ getNotificationMessage(notification) }}
          </div>
          <div class="notification-time">
            {{ formatTime(notification.timestamp) }}
          </div>
        </div>
        <button class="close-btn" @click.stop="removeNotification(notification.id)">
          ×
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue'

export default {
  name: 'StationStatusNotifications',
  setup() {
    const isConnected = ref(false)
    const notifications = ref([])
    const ws = ref(null)
    const reconnectAttempts = ref(0)
    const maxReconnectAttempts = 5
    const reconnectDelay = 3000

    const connectWebSocket = () => {
      try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        const wsUrl = `${protocol}//${window.location.host}/ws/notifications`
        
        ws.value = new WebSocket(wsUrl)
        
        ws.value.onopen = () => {
          console.log('WebSocket подключен')
          isConnected.value = true
          reconnectAttempts.value = 0
        }
        
        ws.value.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            handleWebSocketMessage(data)
          } catch (error) {
            console.error('Ошибка парсинга WebSocket сообщения:', error)
          }
        }
        
        ws.value.onclose = () => {
          console.log('WebSocket отключен')
          isConnected.value = false
          
          // Попытка переподключения
          if (reconnectAttempts.value < maxReconnectAttempts) {
            reconnectAttempts.value++
            console.log(`Попытка переподключения ${reconnectAttempts.value}/${maxReconnectAttempts}`)
            setTimeout(connectWebSocket, reconnectDelay)
          }
        }
        
        ws.value.onerror = (error) => {
          console.error('WebSocket ошибка:', error)
        }
        
      } catch (error) {
        console.error('Ошибка создания WebSocket соединения:', error)
      }
    }

    const handleWebSocketMessage = (data) => {
      switch (data.type) {
        case 'station_status_change':
          handleStationStatusChange(data)
          break
        case 'station_online':
          handleStationOnline(data)
          break
        case 'station_offline':
          handleStationOffline(data)
          break
        case 'powerbank_status_change':
          handlePowerbankStatusChange(data)
          break
        case 'pong':
          // Ответ на ping
          break
        default:
          console.log('Неизвестный тип WebSocket сообщения:', data.type)
      }
    }

    const handleStationStatusChange = (data) => {
      const notification = {
        id: Date.now() + Math.random(),
        type: 'station_status_change',
        station_id: data.station_id,
        box_id: data.station_info?.box_id,
        old_status: data.old_status,
        new_status: data.new_status,
        timestamp: data.timestamp,
        station_info: data.station_info
      }
      
      addNotification(notification)
    }

    const handleStationOnline = (data) => {
      const notification = {
        id: Date.now() + Math.random(),
        type: 'station_online',
        station_id: data.station_id,
        box_id: data.station_info?.box_id,
        timestamp: data.timestamp,
        station_info: data.station_info
      }
      
      addNotification(notification)
    }

    const handleStationOffline = (data) => {
      const notification = {
        id: Date.now() + Math.random(),
        type: 'station_offline',
        station_id: data.station_id,
        box_id: data.station_info?.box_id,
        timestamp: data.timestamp,
        station_info: data.station_info
      }
      
      addNotification(notification)
    }

    const handlePowerbankStatusChange = (data) => {
      const notification = {
        id: Date.now() + Math.random(),
        type: 'powerbank_status_change',
        station_id: data.station_id,
        powerbank_id: data.powerbank_id,
        old_status: data.old_status,
        new_status: data.new_status,
        timestamp: data.timestamp
      }
      
      addNotification(notification)
    }

    const addNotification = (notification) => {
      notifications.value.unshift(notification)
      
      // Ограничиваем количество уведомлений
      if (notifications.value.length > 50) {
        notifications.value = notifications.value.slice(0, 50)
      }
      
      // Автоматически удаляем уведомление через 10 секунд
      setTimeout(() => {
        removeNotification(notification.id)
      }, 10000)
    }

    const removeNotification = (id) => {
      const index = notifications.value.findIndex(n => n.id === id)
      if (index !== -1) {
        notifications.value.splice(index, 1)
      }
    }

    const getNotificationClass = (notification) => {
      switch (notification.type) {
        case 'station_online':
          return 'notification-success'
        case 'station_offline':
          return 'notification-error'
        case 'station_status_change':
          return notification.new_status === 'active' ? 'notification-success' : 'notification-warning'
        case 'powerbank_status_change':
          return 'notification-info'
        default:
          return 'notification-info'
      }
    }

    const getNotificationTitle = (notification) => {
      switch (notification.type) {
        case 'station_status_change':
          return `Станция ${notification.box_id}`
        case 'station_online':
          return `Станция ${notification.box_id} онлайн`
        case 'station_offline':
          return `Станция ${notification.box_id} офлайн`
        case 'powerbank_status_change':
          return `Повербанк ${notification.powerbank_id}`
        default:
          return 'Уведомление'
      }
    }

    const getNotificationMessage = (notification) => {
      switch (notification.type) {
        case 'station_status_change':
          return `Статус изменен с "${getStatusText(notification.old_status)}" на "${getStatusText(notification.new_status)}"`
        case 'station_online':
          return 'Станция восстановила связь с сервером'
        case 'station_offline':
          return 'Станция потеряла связь с сервером'
        case 'powerbank_status_change':
          return `Статус изменен с "${getStatusText(notification.old_status)}" на "${getStatusText(notification.new_status)}"`
        default:
          return 'Новое уведомление'
      }
    }

    const getStatusText = (status) => {
      const statusMap = {
        'online': 'Онлайн',
        'offline': 'Офлайн',
        'active': 'Активна',
        'pending': 'Ожидает',
        'maintenance': 'Обслуживание',
        'blocked': 'Заблокирована',
        'unknown': 'Неизвестно'
      }
      return statusMap[status] || status
    }

    const formatTime = (timestamp) => {
      const date = new Date(timestamp * 1000)
      // Московское время (UTC+3)
      const moscowTime = new Date(date.getTime() + (3 * 60 * 60 * 1000))
      return moscowTime.toLocaleTimeString('ru-RU')
    }

    const sendPing = () => {
      if (ws.value && ws.value.readyState === WebSocket.OPEN) {
        ws.value.send(JSON.stringify({ type: 'ping' }))
      }
    }

    onMounted(() => {
      connectWebSocket()
      
      // Отправляем ping каждые 30 секунд
      const pingInterval = setInterval(sendPing, 30000)
      
      onUnmounted(() => {
        clearInterval(pingInterval)
        if (ws.value) {
          ws.value.close()
        }
      })
    })

    return {
      isConnected,
      notifications,
      getNotificationClass,
      getNotificationTitle,
      getNotificationMessage,
      formatTime,
      removeNotification
    }
  }
}
</script>

<style scoped>
.notifications-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 1000;
  max-width: 400px;
}

.websocket-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 10px;
}

.websocket-status.connected {
  background-color: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.websocket-status.disconnected {
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: currentColor;
}

.notifications-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.notification {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  cursor: pointer;
  transition: all 0.2s ease;
  background: white;
  border-left: 4px solid;
}

.notification:hover {
  transform: translateX(-4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.notification-success {
  border-left-color: #28a745;
}

.notification-warning {
  border-left-color: #ffc107;
}

.notification-error {
  border-left-color: #dc3545;
}

.notification-info {
  border-left-color: #17a2b8;
}

.notification-content {
  flex: 1;
}

.notification-title {
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 4px;
  color: #333;
}

.notification-message {
  font-size: 13px;
  color: #666;
  margin-bottom: 4px;
  line-height: 1.4;
}

.notification-time {
  font-size: 12px;
  color: #999;
}

.close-btn {
  background: none;
  border: none;
  font-size: 18px;
  color: #999;
  cursor: pointer;
  padding: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: all 0.2s ease;
}

.close-btn:hover {
  background-color: #f5f5f5;
  color: #666;
}
</style>
