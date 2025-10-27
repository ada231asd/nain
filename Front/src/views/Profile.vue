<template>
  <div class="profile-container">

    <div class="profile-content">
      <!-- Обработка ошибок -->
      <div v-if="error" class="error-message">
        <h3>Ошибка загрузки</h3>
        <p>{{ error }}</p>
        <button @click="loadUserProfile" class="btn-retry">Попробовать снова</button>
      </div>

      <!-- Индикатор загрузки -->
      <div v-if="isLoading" class="loading-indicator">
        <div class="spinner"></div>
        <p>Загрузка данных профиля...</p>
      </div>

      <!-- Основная информация о пользователе -->
      <div v-else class="user-info-card">
        <div class="card-header">
          <h2>Личная информация</h2>
          <div class="header-actions">
            <BaseButton @click="goToDashboard" variant="outline" size="small" class="btn-home" title="На главную">
              🏠
            </BaseButton>
            <BaseButton @click="toggleEditMode" variant="primary" size="small" :disabled="isLoading">
              {{ isEditing ? 'Сохранить' : 'Редактировать' }}
            </BaseButton>
          </div>
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
            Обновить
          </button>
        </div>

        <div class="history-list">
          <div v-if="filteredHistory.length === 0" class="empty-history">
            <p>История заказов пуста</p>
          </div>
          
          <div v-else class="history-items">
            <div 
              v-for="item in paginatedHistory" 
              :key="item.id || item.order_id"
              class="history-item"
              :class="[`history-${item.status}`, { 'expanded': isOrderExpanded(item.id || item.order_id) }]"
            >
              <div class="history-header" @click="toggleOrderDetails(item.id || item.order_id)">
                <h4>Заказ №{{ item.id || item.order_id }}</h4>
                <div class="header-right">
                  <span class="history-status" :class="`status-${item.status}`">
                    {{ getOrderStatusText(item.status) }}
                  </span>
                  <span class="accordion-icon" :class="{ 'rotated': isOrderExpanded(item.id || item.order_id) }">
                    ▼
                  </span>
                </div>
              </div>
              
              <transition name="accordion">
                <div v-show="isOrderExpanded(item.id || item.order_id)" class="history-details">
                  <p><strong>Повербанк:</strong> {{ item.powerbank_serial || 'Не указан' }}</p>
                  <p><strong>Станция:</strong> {{ item.station_box_id || 'Не указана' }}</p>
                  <p v-if="item.org_unit_name"><strong>Группа:</strong> {{ item.org_unit_name }}</p>
                  <p><strong>Дата создания:</strong> {{ formatDate(item.timestamp) }}</p>
                  <p v-if="item.completed_at"><strong>Завершен:</strong> {{ formatDate(item.completed_at) }}</p>
                </div>
              </transition>
              
            </div>
          </div>
          
          <!-- Кнопка "Показать ещё" -->
          <div v-if="hasMoreItems" class="load-more-section">
            <BaseButton @click="loadMoreItems" variant="primary" size="medium" :disabled="isLoading">
              Показать ещё
            </BaseButton>
          </div>
        </div>
      </div>

      <!-- Статистика -->
      <div class="stats-card">
        <h2>Статистика использования</h2>
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

      <!-- Кнопка выхода -->
      <div class="logout-section">
        <BaseButton @click="logout" variant="danger" size="medium">
          Выйти
        </BaseButton>
      </div>
    </div>


  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useStationsStore } from '../stores/stations'
import { useAdminStore } from '../stores/admin'
import { pythonAPI } from '../api/pythonApi'
import BaseButton from '../components/BaseButton.vue'

const router = useRouter()
const authStore = useAuthStore()
const stationsStore = useStationsStore()
const adminStore = useAdminStore()

// Состояние
const isLoading = ref(false)
const statusFilter = ref('all')
const error = ref(null)
const isEditing = ref(false)
const expandedOrders = ref(new Set())



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
const itemsPerPage = ref(5)
const currentPage = ref(1)

// Вычисляемые свойства
const filteredHistory = computed(() => {
  // Защита от undefined/null
  if (!Array.isArray(orderHistory.value)) return []
  if (statusFilter.value === 'all') return orderHistory.value
  return orderHistory.value.filter(item => item.status === statusFilter.value)
})

const paginatedHistory = computed(() => {
  const filtered = filteredHistory.value
  const startIndex = 0
  const endIndex = currentPage.value * itemsPerPage.value
  return filtered.slice(startIndex, endIndex)
})

const hasMoreItems = computed(() => {
  return paginatedHistory.value.length < filteredHistory.value.length
})

const totalOrders = computed(() => {
  if (!Array.isArray(orderHistory.value)) return 0
  return orderHistory.value.length
})
const activeOrders = computed(() => {
  if (!Array.isArray(orderHistory.value)) return 0
  return orderHistory.value.filter(item => item.status === 'borrow').length
})
const returnedOrders = computed(() => {
  if (!Array.isArray(orderHistory.value)) return 0
  return orderHistory.value.filter(item => item.status === 'return').length
})
const completedOrders = computed(() => {
  if (!Array.isArray(orderHistory.value)) return 0
  return orderHistory.value.filter(item => item.status === 'completed').length
})

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
    
    let response
    let orders = []
    
    // Используем разные API в зависимости от роли
    if (user.value.role === 'user') {
      // Обычные пользователи используют /api/user/orders
      response = await pythonAPI.getMyOrders()
      console.log('📋 Ответ API для пользователя:', response)
      
      // Извлекаем массив из ответа
      if (Array.isArray(response)) {
        orders = response
      } else if (response && Array.isArray(response.orders)) {
        orders = response.orders
      } else if (response && response.data && Array.isArray(response.data.orders)) {
        // API возвращает {success: true, data: {orders: [...]}}
        orders = response.data.orders
      } else if (response && Array.isArray(response.data)) {
        orders = response.data
      }
    } else {
      // Администраторы используют /api/orders с фильтром по телефону
      response = await pythonAPI.getOrders({ user_phone: user.value.phone_e164 })
      console.log('📋 Ответ API для администратора:', response)
      
      // Извлекаем массив из ответа
      if (Array.isArray(response)) {
        orders = response
      } else if (response && Array.isArray(response.data)) {
        orders = response.data
      }
    }
    
    // Гарантируем, что orderHistory всегда массив
    orderHistory.value = Array.isArray(orders) ? orders : []
    
    console.log('📋 Загруженные заказы (массив):', orderHistory.value)
    console.log('📋 Количество заказов:', orderHistory.value.length)
    
    // Автоматически раскрываем заказы со статусом "Взятый" (borrow)
    expandBorrowedOrders()
  } catch (err) {
    console.error('❌ Ошибка загрузки заказов:', err)
    orderHistory.value = []
  }
}

const refreshHistory = async () => {
  currentPage.value = 1
  await loadUserOrders()
}

const loadMoreItems = () => {
  currentPage.value += 1
}

// Сброс пагинации при изменении фильтра
watch(statusFilter, () => {
  currentPage.value = 1
})

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

// Централизованное обновление всех данных после возврата аккумулятора
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

// Функции для управления аккордеоном
const toggleOrderDetails = (orderId) => {
  if (expandedOrders.value.has(orderId)) {
    expandedOrders.value.delete(orderId)
  } else {
    expandedOrders.value.add(orderId)
  }
  // Принудительное обновление реактивности
  expandedOrders.value = new Set(expandedOrders.value)
}

const isOrderExpanded = (orderId) => {
  return expandedOrders.value.has(orderId)
}

// Автоматически раскрывает заказы со статусом "Взятый" (borrow)
const expandBorrowedOrders = () => {
  if (!Array.isArray(orderHistory.value)) return
  
  orderHistory.value.forEach(order => {
    if (order.status === 'borrow') {
      expandedOrders.value.add(order.id || order.order_id)
    }
  })
  
  // Принудительное обновление реактивности
  expandedOrders.value = new Set(expandedOrders.value)
}

onMounted(async () => {
  await loadUserProfile()
  
  // Не запускаем автоматическое обновление по таймеру
  // Обновление происходит только после действий
})

onUnmounted(() => {
  // Останавливаем автоматическое обновление
  stopAutoRefresh()
})
</script>

<style scoped>
.profile-container {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
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

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.btn-home {
  min-width: 44px !important;
  width: 44px !important;
  height: 44px !important;
  padding: 0 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  font-size: 18px !important;
}

.card-header h2 {
  color: #333;
  margin: 0;
  font-size: 1.8rem;
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
  padding: 12px 24px;
  background: #17a2b8;
  color: white;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 600;
  transition: all 0.3s ease;
}

.btn-refresh:hover:not(:disabled) {
  background: #138496;
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
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
  cursor: pointer;
  user-select: none;
  transition: all 0.3s ease;
}

.history-header:hover {
  opacity: 0.8;
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

.header-right {
  display: flex;
  align-items: center;
  gap: 15px;
}

.accordion-icon {
  font-size: 1rem;
  color: #667eea;
  transition: transform 0.3s ease;
  display: inline-block;
  font-weight: bold;
}

.accordion-icon.rotated {
  transform: rotate(180deg);
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

.history-details {
  overflow: hidden;
  padding-top: 15px;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
}

.history-details p {
  margin: 8px 0;
  color: #666;
}

/* Анимация аккордеона */
.accordion-enter-active,
.accordion-leave-active {
  transition: all 0.3s ease;
  max-height: 300px;
}

.accordion-enter-from,
.accordion-leave-to {
  opacity: 0;
  max-height: 0;
  padding-top: 0;
  border-top: none;
}

.history-item.expanded {
  box-shadow: 0 5px 15px rgba(102, 126, 234, 0.2);
}

.history-item.expanded .history-header {
  margin-bottom: 0;
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

/* Секция выхода */
.logout-section {
  background: white;
  padding: 30px;
  border-radius: 15px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
  text-align: center;
}

/* Кнопка "Показать ещё" */
.load-more-section {
  text-align: center;
  margin-top: 30px;
  padding: 20px;
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
  border-radius: 10px;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 600;
  transition: all 0.3s ease;
}

.btn-retry:hover {
  background: #c82333;
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
}

/* Мобильные стили */
@media (max-width: 768px) {
  .profile-container {
    padding: 15px;
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
  
  .header-right {
    width: 100%;
    justify-content: space-between;
  }
  
  .history-actions {
    flex-direction: column;
  }
  
  .header-actions {
    flex-direction: column;
    gap: 8px;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
}

</style>

