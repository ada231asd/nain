import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import { useAuthStore } from './stores/auth'
import websocketNotificationService from './utils/websocketNotifications'
import { registerSW } from 'virtual:pwa-register'
import { initPWAInstall } from './utils/pwa-install'
import './assets/variables.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

// Регистрация Service Worker для PWA
if ('serviceWorker' in navigator) {
  const updateSW = registerSW({
    immediate: true,
    onRegistered(registration) {
      console.log('✅ Service Worker зарегистрирован:', registration)
    },
    onRegisterError(error) {
      console.error('❌ Ошибка регистрации Service Worker:', error)
    },
    onNeedRefresh() {
      console.log('🔄 Доступно обновление Service Worker')
    },
    onOfflineReady() {
      console.log('📱 PWA готово к работе офлайн')
    }
  })
}

// Инициализация обработчика установки PWA
initPWAInstall()

// Инициализируем авторизацию при загрузке приложения и ждем завершения
const authStore = useAuthStore()
authStore.initializeAuth().then(() => {
  // Подключаемся к WebSocket если пользователь авторизован
  if (authStore.token) {
    console.log('🔌 [MAIN] Пользователь авторизован, подключаемся к WebSocket')
    console.log('🔑 [MAIN] Токен найден:', authStore.token.substring(0, 20) + '...')
    websocketNotificationService.connect(authStore.token)
    
    // Запрашиваем разрешение на браузерные уведомления
    websocketNotificationService.requestNotificationPermission()
  } else {
    console.log('❌ [MAIN] Токен не найден, WebSocket не подключается')
  }
  
  // Монтируем приложение после инициализации авторизации
  app.mount('#app')
}).catch((error) => {
  console.error('❌ [MAIN] Ошибка инициализации:', error)
  // Даже при ошибке монтируем приложение
  app.mount('#app')
})

// Глобально доступный сервис уведомлений
app.config.globalProperties.$wsNotifications = websocketNotificationService