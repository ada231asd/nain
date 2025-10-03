<template>
  <div class="profile-container">
    <div class="profile-header">
      <button @click="goBack" class="btn-back">
        ← Назад
      </button>
      <h1>👤 Профиль пользователя</h1>
    </div>

    <div class="profile-content">
      <!-- Обработка ошибок -->
      <div v-if="error" class="error-message">
        <h3>❌ Ошибка загрузки</h3>
        <p>{{ error }}</p>
        <button @click="loadUserProfile" class="btn-retry">🔄 Попробовать снова</button>
      </div>

      <!-- Индикатор загрузки -->
      <div v-if="isLoading" class="loading-indicator">
        <div class="spinner"></div>
        <p>Загрузка данных профиля...</p>
      </div>

      <!-- Основная информация о пользователе -->
      <div v-else class="user-info-card">
        <div class="card-header">
          <h2>📋 Личная информация</h2>
          <button @click="toggleEditMode" class="btn-edit" :disabled="isLoading">
            {{ isEditing ? '💾 Сохранить' : '✏️ Редактировать' }}
          </button>
        </div>
        <div class="info-grid">
          <div class="info-item">
            <strong>Телефон:</strong>
            <input 
              v-if="isEditing" 
              v-model="user.phone_e164" 
              type="tel" 
              class="edit-input"
              placeholder="+7 (999) 123-45-67"
            />
            <span v-else>{{ user.phone_e164 || 'Не указан' }}</span>
          </div>
          <div class="info-item">
            <strong>Email:</strong>
            <input 
              v-if="isEditing" 
              v-model="user.email" 
              type="email" 
              class="edit-input"
              placeholder="user@example.com"
            />
            <span v-else>{{ user.email || 'Не указан' }}</span>
          </div>
          <div class="info-item">
            <strong>ФИО:</strong>
            <input 
              v-if="isEditing" 
              v-model="user.fio" 
              type="text" 
              class="edit-input"
              placeholder="Иванов Иван Иванович"
            />
            <span v-else>{{ user.fio || 'Не указано' }}</span>
          </div>
        </div>
      </div>

      <!-- История аккумуляторов -->
      <div class="battery-history-card">
        <h2>История аккумуляторов</h2>
        <div class="history-filters">
          <select v-model="statusFilter" class="filter-select">
            <option value="all">Все статусы</option>
            <option value="borrow">Взятые</option>
            <option value="return">Возвращенные</option>
            <option value="completed">Завершенные</option>
          </select>
          
          <button @click="refreshHistory" class="btn-refresh" :disabled="isLoading">
            🔄 Обновить
          </button>
        </div>

        <div class="history-list">
          <div v-if="filteredHistory.length === 0" class="empty-history">
            <p>История заказов пуста</p>
          </div>
          
          <div v-else class="history-items">
            <div 
              v-for="item in filteredHistory" 
              :key="item.id || item.order_id"
              class="history-item"
              :class="`history-${item.status}`"
            >
              <div class="history-header">
                <h4>Заказ №{{ item.id || item.order_id }}</h4>
                <span class="history-status" :class="`status-${item.status}`">
                  {{ getOrderStatusText(item.status) }}
                </span>
              </div>
              
              <div class="history-details">
                <p><strong>Повербанк:</strong> {{ item.powerbank_serial || item.powerbank_id || 'Не указан' }}</p>
                <p><strong>Станция:</strong> {{ item.station_box_id || item.station_id || 'Не указана' }}</p>
                <p><strong>Дата создания:</strong> {{ formatDate(item.timestamp) }}</p>
                <p v-if="item.completed_at"><strong>Завершен:</strong> {{ formatDate(item.completed_at) }}</p>
              </div>
              
              <div class="history-actions">
                <button 
                  v-if="item.status === 'borrow'"
                  @click="returnPowerbank(item)"
                  class="btn-action btn-return"
                  :disabled="isLoading"
                >
                  🔌 Вернуть
                </button>
                <button 
                  v-if="item.status === 'borrow'"
                  @click="reportError(item)"
                  class="btn-action btn-error"
                  :disabled="isLoading"
                >
                  🚨 Сообщить об ошибке
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Статистика -->
      <div class="stats-card">
        <h2>📊 Статистика использования</h2>
        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-number">{{ totalOrders }}</span>
            <span class="stat-label">Всего заказов</span>
          </div>
          <div class="stat-item">
            <span class="stat-number">{{ activeOrders }}</span>
            <span class="stat-label">Активных</span>
          </div>
          <div class="stat-item">
            <span class="stat-number">{{ returnedOrders }}</span>
            <span class="stat-label">Возвращенных</span>
          </div>
          <div class="stat-item">
            <span class="stat-number">{{ completedOrders }}</span>
            <span class="stat-label">Завершенных</span>
          </div>
        </div>
      </div>

      <!-- Быстрые действия -->
      <div class="quick-actions">
        <h2>⚡ Быстрые действия</h2>
        <div class="action-buttons">
          <button @click="goToDashboard" class="btn-action btn-primary">
            🏠 На главную
          </button>
          <button @click="goToQRScanner" class="btn-action btn-secondary">
            📱 Сканировать QR
          </button>
          <button @click="logout" class="btn-action btn-logout">
            🚪 Выйти
          </button>
        </div>
      </div>
    </div>

    <!-- Модальное окно для сообщения об ошибке -->
    <ErrorReportModal 
      :isVisible="showErrorModal"
      :order="selectedOrder"
      @close="closeErrorModal"
      @submit="handleErrorReport"
    />

    <!-- Таймер возврата -->
    <div v-if="returnTimer > 0" class="return-timer-overlay">
      <div class="return-timer">
        <div class="timer-content">
          <h3 v-if="returnType === 'normal'">⏰ Возврат через {{ returnTimer }}с</h3>
          <h3 v-else>🚨 Возврат с ошибкой через {{ returnTimer }}с</h3>
          <p v-if="returnType === 'normal'">Подготовьте повербанк к возврату</p>
          <p v-else>Подготовьте повербанк к возврату с отчетом об ошибке</p>
          <div class="timer-progress">
            <div class="timer-bar" :style="{ width: `${(returnTimer / 10) * 100}%` }"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useStationsStore } from '../stores/stations'
import { useAdminStore } from '../stores/admin'
import { pythonAPI } from '../api/pythonApi'
import { refreshAllDataAfterReturn } from '../utils/dataSync'
import ErrorReportModal from '../components/ErrorReportModal.vue'

const router = useRouter()
const authStore = useAuthStore()
const stationsStore = useStationsStore()
const adminStore = useAdminStore()

// Состояние
const isLoading = ref(false)
const statusFilter = ref('all')
const error = ref(null)
const isEditing = ref(false)

// Модальное окно ошибки
const showErrorModal = ref(false)
const selectedOrder = ref(null)

// Таймер возврата
const returnTimer = ref(0)
const returnTimerInterval = ref(null)
const returnType = ref('normal') // 'normal' или 'error'

// Автоматическое обновление данных
const autoRefreshInterval = ref(null)
const autoRefreshEnabled = ref(false) // Отключаем автоматическое обновление по таймеру
const refreshInterval = 30000 // 30 секунд

// Данные пользователя
const user = ref({
  user_id: null,
  phone_e164: '',
  email: '',
  fio: '',
  role: 'user',
  status: 'active',
  created_at: null,
  last_login_at: null
})

// История заказов (повербанков)
const orderHistory = ref([])

// Вычисляемые свойства
const filteredHistory = computed(() => {
  if (statusFilter.value === 'all') return orderHistory.value
  return orderHistory.value.filter(item => item.status === statusFilter.value)
})

const totalOrders = computed(() => orderHistory.value.length)
const activeOrders = computed(() => orderHistory.value.filter(item => item.status === 'borrow').length)
const returnedOrders = computed(() => orderHistory.value.filter(item => item.status === 'return').length)
const completedOrders = computed(() => orderHistory.value.filter(item => item.status === 'completed').length)

// Методы
const goBack = () => {
  router.go(-1)
}

const goToDashboard = () => {
  router.push('/dashboard')
}

const goToQRScanner = () => {
  router.push('/qr-scanner')
}

const logout = async () => {
  await authStore.logout()
  router.push('/login')
}

// Переключение режима редактирования
const toggleEditMode = async () => {
  if (isEditing.value) {
    // Сохраняем изменения
    await saveProfile()
  } else {
    // Включаем режим редактирования
    isEditing.value = true
  }
}

// Сохранение профиля
const saveProfile = async () => {
  try {
    isLoading.value = true
    
    // Обновляем профиль через API
    await pythonAPI.updateProfile({
      phone_e164: user.value.phone_e164,
      email: user.value.email,
      fio: user.value.fio
    })
    
    // Обновляем данные в store
    await authStore.fetchProfile()
    
    isEditing.value = false
    alert('✅ Профиль успешно обновлен!')
    
  } catch (err) {
    alert('❌ Ошибка при сохранении профиля')
  } finally {
    isLoading.value = false
  }
}

// Загрузка данных профиля
const loadUserProfile = async () => {
  try {
    isLoading.value = true
    error.value = null
    
    // Получаем данные пользователя из store или API
    if (authStore.user) {
      user.value = { ...authStore.user }
    } else {
      await authStore.fetchProfile()
      user.value = { ...authStore.user }
    }
    
    // Загружаем историю заказов пользователя
    if (user.value.user_id) {
      await loadUserOrders()
    }
    
  } catch (err) {
    error.value = err.message || 'Ошибка загрузки профиля'
  } finally {
    isLoading.value = false
  }
}

// Загрузка заказов пользователя
const loadUserOrders = async () => {
  try {
    console.log('📋 Загружаем заказы для пользователя:', user.value.user_id)
    const response = await pythonAPI.getOrders({ user_id: user.value.user_id })
    console.log('📋 Ответ API заказов:', response)
    orderHistory.value = response.data || response || []
    console.log('📋 Загруженные заказы:', orderHistory.value)
  } catch (err) {
    console.error('❌ Ошибка загрузки заказов:', err)
    orderHistory.value = []
  }
}

const refreshHistory = async () => {
  await loadUserOrders()
}

// Функции автоматического обновления данных
const startAutoRefresh = () => {
  if (autoRefreshInterval.value) {
    clearInterval(autoRefreshInterval.value)
  }
  
  if (autoRefreshEnabled.value) {
    autoRefreshInterval.value = setInterval(async () => {
      try {
        await loadUserOrders()
      } catch (error) {
        console.warn('Ошибка при автоматическом обновлении истории заказов:', error)
      }
    }, refreshInterval)
  }
}

const stopAutoRefresh = () => {
  if (autoRefreshInterval.value) {
    clearInterval(autoRefreshInterval.value)
    autoRefreshInterval.value = null
  }
}

// Централизованное обновление всех данных после возврата павербанка
const refreshAllDataAfterReturnLocal = async (orderData) => {
  await refreshAllDataAfterReturn(orderData, user.value, loadUserOrders)
}

// Обновление данных после действий (упрощенная версия)
const refreshAfterAction = async () => {
  try {
    await loadUserOrders()
    // Обновление конкретных станций происходит в самих функциях действий
    // Здесь обновляем только историю заказов пользователя
  } catch (error) {
    console.warn('Ошибка при обновлении данных после действия:', error)
  }
}

const returnPowerbank = async (order) => {
  if (confirm(`Вернуть повербанк из заказа #${order.order_id}?`)) {
    startReturnTimer(order)
  }
}

const reportError = (order) => {
  selectedOrder.value = order
  showErrorModal.value = true
}

const closeErrorModal = () => {
  showErrorModal.value = false
  selectedOrder.value = null
}

const handleErrorReport = async (errorReport) => {
  try {
    // Закрываем модальное окно
    closeErrorModal()
    
    // Запускаем таймер для возврата с ошибкой
    startReturnTimerWithError(errorReport)
    
  } catch (err) {
    alert('❌ Ошибка при обработке отчета об ошибке')
  }
}

// Таймер возврата
const startReturnTimer = (order) => {
  returnTimer.value = 10
  returnType.value = 'normal'
  
  returnTimerInterval.value = setInterval(() => {
    returnTimer.value--
    
    if (returnTimer.value <= 0) {
      clearInterval(returnTimerInterval.value)
      returnTimerInterval.value = null
      executeReturn(order)
    }
  }, 1000)
}

// Таймер возврата с ошибкой
const startReturnTimerWithError = (errorReport) => {
  returnTimer.value = 10
  returnType.value = 'error'
  
  returnTimerInterval.value = setInterval(() => {
    returnTimer.value--
    
    if (returnTimer.value <= 0) {
      clearInterval(returnTimerInterval.value)
      returnTimerInterval.value = null
      executeReturnWithError(errorReport)
    }
  }, 1000)
}

const executeReturn = async (order) => {
  try {
    isLoading.value = true
    
    // Логируем данные для отладки
    console.log('🔄 Данные заказа для возврата:', order)
    console.log('👤 Данные пользователя:', user.value)
    
    const returnData = {
      station_id: order.station_id,
      user_id: user.value.user_id,
      powerbank_id: order.powerbank_id
    }
    
    console.log('📤 Отправляемые данные:', returnData)
    
    // Проверяем наличие всех обязательных полей
    if (!returnData.station_id) {
      throw new Error('Отсутствует station_id')
    }
    if (!returnData.user_id) {
      throw new Error('Отсутствует user_id')
    }
    if (!returnData.powerbank_id) {
      throw new Error('Отсутствует powerbank_id')
    }
    
    // Возвращаем павербанк через API
    await pythonAPI.returnPowerbank(returnData)
    
    // Централизованное обновление всех данных после возврата
    await refreshAllDataAfterReturnLocal(order)
    
    alert('✅ Повербанк возвращен!')
    
  } catch (err) {
    console.error('❌ Ошибка при возврате повербанка:', err)
    alert('❌ Ошибка при возврате повербанка: ' + (err.message || 'Неизвестная ошибка'))
  } finally {
    isLoading.value = false
  }
}

const executeReturnWithError = async (errorReport) => {
  try {
    isLoading.value = true
    
    // Сначала отправляем отчет об ошибке
    await pythonAPI.reportPowerbankError(errorReport)
    
    // Затем возвращаем павербанк
    await pythonAPI.returnPowerbank({
      station_id: errorReport.station_id,
      user_id: errorReport.user_id,
      powerbank_id: errorReport.powerbank_id
    })
    
    // Централизованное обновление всех данных после возврата с ошибкой
    await refreshAllDataAfterReturnLocal({
      station_id: errorReport.station_id,
      user_id: errorReport.user_id,
      powerbank_id: errorReport.powerbank_id
    })
    
    alert('✅ Повербанк возвращен с отчетом об ошибке!')
    
  } catch (err) {
    alert('❌ Ошибка при возврате повербанка с отчетом об ошибке')
  } finally {
    isLoading.value = false
  }
}

const getRoleText = (role) => {
  const roleMap = {
    'user': 'Пользователь',
    'subgroup_admin': 'Администратор подгруппы',
    'group_admin': 'Администратор группы',
    'service_admin': 'Сервис-администратор'
  }
  return roleMap[role] || role
}

const getStatusText = (status) => {
  const statusMap = {
    'pending': 'Ожидает подтверждения',
    'active': 'Активен',
    'blocked': 'Заблокирован'
  }
  return statusMap[status] || status
}

const getOrderStatusText = (status) => {
  const statusMap = {
    'borrow': 'Взятый',
    'return': 'Возвращенный',
    'completed': 'Завершенный',
    'pending': 'Ожидает'
  }
  return statusMap[status] || status
}

const formatDate = (date) => {
  return new Date(date).toLocaleString('ru-RU')
}

onMounted(async () => {
  await loadUserProfile()
  
  // Не запускаем автоматическое обновление по таймеру
  // Обновление происходит только после действий
})

onUnmounted(() => {
  // Останавливаем автоматическое обновление
  stopAutoRefresh()
  
  // Очищаем таймер возврата
  if (returnTimerInterval.value) {
    clearInterval(returnTimerInterval.value)
    returnTimerInterval.value = null
  }
})
</script>

<style scoped>
.profile-container {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.profile-header {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 30px;
  padding: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 20px;
  color: white;
}

.btn-back {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: none;
  padding: 10px 15px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1rem;
  transition: background-color 0.3s ease;
}

.btn-back:hover {
  background: rgba(255, 255, 255, 0.3);
}

.profile-header h1 {
  flex: 1;
  margin: 0;
  font-size: 2.5rem;
  color: white;
}

.profile-content {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

/* Карточка информации о пользователе */
.user-info-card {
  background: white;
  padding: 30px;
  border-radius: 15px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 25px;
}

.card-header h2 {
  color: #333;
  margin: 0;
  font-size: 1.8rem;
}

.btn-edit {
  background: #667eea;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  transition: background-color 0.3s ease;
}

.btn-edit:hover:not(:disabled) {
  background: #5a6fd8;
}

.btn-edit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  background: #f8f9fa;
  border-radius: 10px;
  border-left: 4px solid #667eea;
}

.info-item strong {
  color: #333;
  font-weight: 600;
}

.info-item span {
  color: #666;
}

.edit-input {
  width: 100%;
  padding: 8px 12px;
  border: 2px solid #e9ecef;
  border-radius: 6px;
  font-size: 1rem;
  transition: border-color 0.3s ease;
}

.edit-input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.role-badge,
.status-badge {
  padding: 6px 12px;
  border-radius: 15px;
  font-size: 0.8rem;
  font-weight: 500;
}

.role-user {
  background: #d4edda;
  color: #155724;
}

.role-subgroup_admin {
  background: #fff3cd;
  color: #856404;
}

.role-group_admin {
  background: #cce7ff;
  color: #004085;
}

.role-service_admin {
  background: #f8d7da;
  color: #721c24;
}

.status-pending {
  background: #fff3cd;
  color: #856404;
}

.status-active {
  background: #d4edda;
  color: #155724;
}

.status-blocked {
  background: #f8d7da;
  color: #721c24;
}

/* История аккумуляторов */
.battery-history-card {
  background: white;
  padding: 30px;
  border-radius: 15px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
}

.battery-history-card h2 {
  color: #333;
  margin-bottom: 25px;
  text-align: center;
  font-size: 1.8rem;
}

.history-filters {
  display: flex;
  gap: 15px;
  margin-bottom: 25px;
  align-items: center;
}

.filter-select {
  padding: 10px 15px;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  font-size: 1rem;
  min-width: 200px;
}

.btn-refresh {
  padding: 10px 20px;
  background: #17a2b8;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1rem;
  transition: background-color 0.3s ease;
}

.btn-refresh:hover:not(:disabled) {
  background: #138496;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.empty-history {
  text-align: center;
  padding: 40px;
  color: #666;
}

.history-items {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.history-item {
  border: 2px solid #e9ecef;
  border-radius: 12px;
  padding: 20px;
  transition: all 0.3s ease;
}

.history-borrow {
  border-color: #ffc107;
  background: #fffdf8;
}

.history-return {
  border-color: #28a745;
  background: #f8fff9;
}

.history-completed {
  border-color: #17a2b8;
  background: #f8f9ff;
}

.history-pending {
  border-color: #6c757d;
  background: #f8f9fa;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.history-header h4 {
  color: #333;
  margin: 0;
  font-size: 1.2rem;
  font-weight: 600;
}

.history-header h4::before {
  content: "🔢 ";
  margin-right: 5px;
}

.history-status {
  padding: 6px 12px;
  border-radius: 15px;
  font-size: 0.8rem;
  font-weight: 500;
}

.history-status.status-borrow {
  background: #fff3cd;
  color: #856404;
}

.history-status.status-return {
  background: #d4edda;
  color: #155724;
}

.history-status.status-completed {
  background: #cce7ff;
  color: #004085;
}

.history-status.status-pending {
  background: #e2e3e5;
  color: #383d41;
}

.history-details p {
  margin: 8px 0;
  color: #666;
}

.order-number {
  background: #667eea;
  color: white;
  padding: 4px 8px;
  border-radius: 6px;
  font-weight: 600;
  font-size: 0.9rem;
}

.history-actions {
  margin-top: 20px;
  display: flex;
  gap: 10px;
}

.btn-action {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.3s ease;
}

.btn-action:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-return {
  background: #17a2b8;
  color: white;
}

.btn-return:hover:not(:disabled) {
  background: #138496;
}

.btn-faulty {
  background: #dc3545;
  color: white;
}

.btn-faulty:hover:not(:disabled) {
  background: #c82333;
}

.btn-error {
  background: #dc3545;
  color: white;
}

.btn-error:hover:not(:disabled) {
  background: #c82333;
}

/* Статистика */
.stats-card {
  background: white;
  padding: 30px;
  border-radius: 15px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
}

.stats-card h2 {
  color: #333;
  margin-bottom: 25px;
  text-align: center;
  font-size: 1.8rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
}

.stat-item {
  text-align: center;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 10px;
}

.stat-number {
  display: block;
  font-size: 2rem;
  font-weight: bold;
  color: #667eea;
  margin-bottom: 5px;
}

.stat-label {
  color: #666;
  font-size: 0.9rem;
}

/* Быстрые действия */
.quick-actions {
  background: white;
  padding: 30px;
  border-radius: 15px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
}

.quick-actions h2 {
  color: #333;
  margin-bottom: 25px;
  text-align: center;
  font-size: 1.8rem;
}

.action-buttons {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 15px;
}

.btn-primary {
  background: #667eea;
  color: white;
}

.btn-primary:hover {
  background: #5a6fd8;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover {
  background: #5a6268;
}

.btn-info {
  background: #17a2b8;
  color: white;
}

.btn-info:hover {
  background: #138496;
}

.btn-logout {
  background: #dc3545;
  color: white;
}

.btn-logout:hover {
  background: #c82333;
}

/* Индикатор загрузки */
.loading-indicator {
  text-align: center;
  padding: 60px 20px;
  background: white;
  border-radius: 15px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
}

.spinner {
  width: 50px;
  height: 50px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-indicator p {
  color: #666;
  font-size: 1.1rem;
  margin: 0;
}

/* Обработка ошибок */
.error-message {
  background: #f8d7da;
  color: #721c24;
  padding: 30px;
  border-radius: 15px;
  text-align: center;
  margin-bottom: 30px;
  border: 2px solid #f5c6cb;
}

.error-message h3 {
  margin: 0 0 15px 0;
  font-size: 1.5rem;
}

.error-message p {
  margin: 0 0 20px 0;
  font-size: 1.1rem;
}

.btn-retry {
  background: #dc3545;
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 500;
  transition: background-color 0.3s ease;
}

.btn-retry:hover {
  background: #c82333;
}

/* Мобильные стили */
@media (max-width: 768px) {
  .profile-container {
    padding: 15px;
  }
  
  .profile-header {
    flex-direction: column;
    text-align: center;
    gap: 15px;
  }
  
  .profile-header h1 {
    font-size: 2rem;
  }
  
  .info-grid {
    grid-template-columns: 1fr;
  }
  
  .history-filters {
    flex-direction: column;
    align-items: stretch;
  }
  
  .filter-select {
    min-width: auto;
  }
  
  .history-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  
  .history-actions {
    flex-direction: column;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .action-buttons {
    grid-template-columns: 1fr;
  }
}

/* Таймер возврата */
.return-timer-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.return-timer {
  background: white;
  border-radius: 20px;
  padding: 40px;
  text-align: center;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
  animation: slideUp 0.3s ease-out;
  max-width: 400px;
  width: 90%;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(50px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.timer-content h3 {
  color: #333;
  margin: 0 0 15px 0;
  font-size: 2rem;
  font-weight: 600;
}

.timer-content p {
  color: #666;
  margin: 0 0 25px 0;
  font-size: 1.1rem;
}

.timer-progress {
  width: 100%;
  height: 8px;
  background: #e9ecef;
  border-radius: 4px;
  overflow: hidden;
}

.timer-bar {
  height: 100%;
  background: linear-gradient(90deg, #dc3545 0%, #ffc107 50%, #28a745 100%);
  border-radius: 4px;
  transition: width 1s linear;
  animation: pulse 1s infinite alternate;
}

@keyframes pulse {
  from { opacity: 0.8; }
  to { opacity: 1; }
}
</style>

