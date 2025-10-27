import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import { useAuthStore } from './stores/auth'
import './assets/variables.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

// Инициализируем авторизацию при загрузке приложения и ждем завершения
const authStore = useAuthStore()
authStore.initializeAuth().then(() => {
  // Монтируем приложение после инициализации авторизации
  app.mount('#app')
}).catch(() => {
  // Даже при ошибке монтируем приложение
  app.mount('#app')
})