<template>
  <div class="orders-table-container">
    <!-- Заголовок с поиском и действиями -->
    <div class="orders-table-header">
      <div class="orders-table-title">
        <h2>Заказы</h2>
      </div>
      <div class="orders-table-actions">
        <div class="search-container">
          <input 
            type="text" 
            v-model="searchQuery" 
            placeholder="Поиск по ID, пользователю, станции..." 
            class="search-input"
          />
          <span class="search-icon">🔍</span>
        </div>
        <FilterButton 
          filter-type="orders"
          :org-units="orgUnits"
          :show-org-unit-filter="false"
          :show-status-filter="true"
          :show-role-filter="false"
          @filter-change="handleFilterChange"
        />
        <button @click="$emit('refresh')" class="btn-refresh" :disabled="isLoading">
          {{ isLoading ? '🔄' : '↻' }} Обновить
        </button>
      </div>
    </div>

    <!-- Таблица заказов -->
    <div class="table-wrapper">
      <table class="orders-table">
        <thead>
           <tr>
             <th class="col-id">ID</th>
             <th class="col-user">Пользователь</th>
             <th class="col-phone">Телефон</th>
             <th class="col-station">Станция</th>
             <th class="col-action">Действие</th>
             <th class="col-status">Статус</th>
             <th class="col-created">Создан</th>
             <th class="col-completed">Завершен</th>
             <th class="col-powerbank">Повербанк</th>
             <th class="col-actions">Операции</th>
           </tr>
        </thead>
        <tbody>
          <tr 
            v-for="order in paginatedOrders" 
            :key="order.id || order.order_id"
            class="order-row"
            :class="getOrderRowClass(order.status)"
          >
            <!-- ID -->
            <td class="col-id">
              <span class="order-id-text">#{{ order.id || order.order_id }}</span>
            </td>

             <!-- Пользователь -->
             <td class="col-user">
               <div class="user-info">
                 <span class="user-name" :title="order.user_fio">
                   {{ truncateText(order.user_fio || 'N/A', 10) }}
                 </span>
               </div>
             </td>

             <!-- Телефон -->
             <td class="col-phone">
               <span class="phone-text">{{ order.user_phone || '—' }}</span>
             </td>

            <!-- Станция -->
            <td class="col-station">
              <span class="station-text" :title="getStationFullName(order)">
                {{ truncateText(getStationFullName(order), 30) }}
              </span>
            </td>

            <!-- Действие -->
            <td class="col-action">
              <span class="action-text">{{ getOrderActionText(order.status) }}</span>
            </td>

            <!-- Статус -->
            <td class="col-status">
              <span class="status-badge" :class="getOrderStatusClass(order.status)">
                {{ getOrderStatusText(order.status) }}
              </span>
            </td>

             <!-- Создан -->
             <td class="col-created">
               <div class="datetime-cell" v-if="order.timestamp">
                 <span class="time-text">{{ formatTimeOnly(order.timestamp) }}</span>
                 <span class="date-text">{{ formatDateOnly(order.timestamp) }}</span>
               </div>
               <span v-else>—</span>
             </td>

             <!-- Завершен -->
             <td class="col-completed">
               <div class="datetime-cell" v-if="order.completed_at">
                 <span class="time-text">{{ formatTimeOnly(order.completed_at) }}</span>
                 <span class="date-text">{{ formatDateOnly(order.completed_at) }}</span>
               </div>
               <span v-else>—</span>
             </td>

             <!-- Повербанк -->
             <td class="col-powerbank">
               <span class="powerbank-text" v-if="order.powerbank_serial || order.powerbank_id">
                 {{ truncateText(order.powerbank_serial || order.powerbank_id, 15) }}
               </span>
               <span v-else class="no-powerbank">—</span>
             </td>

             <!-- Операции -->
             <td class="col-actions">
               <div class="actions-container">
                 <!-- Показываем кнопку восстановления для удалённых -->
                 <button 
                   v-if="showDeletedOrders"
                   @click="handleRestore(order)"
                   class="btn-action btn-restore"
                   title="Восстановить заказ"
                 >
                   ↺
                 </button>
                 <!-- Показываем кнопку удаления -->
                 <button 
                   @click="handleDelete(order)"
                   class="btn-action btn-delete"
                   :class="{ 'btn-hard-delete': showDeletedOrders }"
                   :title="showDeletedOrders ? 'Удалить навсегда' : 'Удалить заказ'"
                 >
                   {{ showDeletedOrders ? '✕' : '🗑' }}
                 </button>
               </div>
             </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Пагинация -->
    <div v-if="totalPages > 1" class="pagination">
      <button 
        @click="currentPage = Math.max(1, currentPage - 1)"
        :disabled="currentPage === 1"
        class="pagination-btn pagination-prev"
      >
        ← Предыдущая
      </button>
      
      <div class="pagination-pages">
        <button 
          v-for="page in visiblePages" 
          :key="page"
          @click="currentPage = page"
          :class="['pagination-page', { active: page === currentPage }]"
        >
          {{ page }}
        </button>
      </div>
      
      <button 
        @click="currentPage = Math.min(totalPages, currentPage + 1)"
        :disabled="currentPage === totalPages"
        class="pagination-btn pagination-next"
      >
        Следующая →
      </button>
    </div>

    <!-- Пустое состояние -->
    <div v-if="filteredOrders.length === 0" class="empty-state">
      <div class="empty-icon">📋</div>
      <h3>Заказы не найдены</h3>
      <p v-if="searchQuery">Попробуйте изменить поисковый запрос</p>
      <p v-else-if="activeFilters.statuses.length > 0 || statusFilter">Попробуйте изменить фильтр или обновить данные</p>
      <p v-else>Заказов пока нет в системе</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { formatMoscowTime } from '../../utils/timeUtils'
import { pythonAPI } from '../../api/pythonApi'
import FilterButton from './FilterButton.vue'
import { showSuccess, showError, showConfirm } from '../../utils/notifications'

const props = defineProps({
  orders: {
    type: Array,
    default: () => []
  },
  orgUnits: {
    type: Array,
    default: () => []
  },
  isLoading: {
    type: Boolean,
    default: false
  },
  itemsPerPage: {
    type: Number,
    default: 50
  }
})

const emit = defineEmits(['refresh', 'order-deleted', 'order-restored'])

// Состояние компонента
const searchQuery = ref('')
const statusFilter = ref('')
const currentPage = ref(1)
const activeFilters = ref({
  orgUnits: [],
  statuses: [],
  roles: []
})

// Проверка, показываем ли удалённые заказы
const showDeletedOrders = computed(() => {
  return activeFilters.value.statuses.includes('deleted')
})

// Методы
const handleFilterChange = (filters) => {
  activeFilters.value = filters
  currentPage.value = 1 // Сбрасываем на первую страницу при изменении фильтров
}

// Удаление заказа (мягкое или жёсткое в зависимости от фильтра)
const handleDelete = async (order) => {
  const orderId = order.id || order.order_id
  
  if (showDeletedOrders.value) {
    // Жёсткое удаление для удалённых заказов
    const confirmMessage = `Вы уверены, что хотите НАВСЕГДА удалить заказ #${orderId}?\n\nЭто действие необратимо!`
    if (!await showConfirm(confirmMessage)) return
    
    try {
      await pythonAPI.hardDelete('order', orderId)
      showSuccess('Заказ удалён навсегда')
      emit('order-deleted', orderId)
      emit('refresh')
    } catch (error) {
      console.error('Ошибка при жёстком удалении заказа:', error)
      showError('Ошибка при удалении заказа: ' + (error.message || 'Неизвестная ошибка'))
    }
  } else {
    // Мягкое удаление для обычных заказов
    const confirmMessage = `Вы уверены, что хотите удалить заказ #${orderId}?`
    if (!await showConfirm(confirmMessage)) return
    
    try {
      await pythonAPI.softDelete('order', orderId)
      showSuccess('Заказ успешно удалён')
      emit('order-deleted', orderId)
      emit('refresh')
    } catch (error) {
      console.error('Ошибка при мягком удалении заказа:', error)
      showError('Ошибка при удалении заказа: ' + (error.message || 'Неизвестная ошибка'))
    }
  }
}

// Восстановление удалённого заказа
const handleRestore = async (order) => {
  const orderId = order.id || order.order_id
  
  const confirmMessage = `Вы уверены, что хотите восстановить заказ #${orderId}?`
  if (!await showConfirm(confirmMessage)) return
  
  try {
    await pythonAPI.restoreDeleted('order', orderId)
    showSuccess('Заказ успешно восстановлен')
    emit('order-restored', orderId)
    emit('refresh')
  } catch (error) {
    console.error('Ошибка при восстановлении заказа:', error)
    showError('Ошибка при восстановлении заказа: ' + (error.message || 'Неизвестная ошибка'))
  }
}

// Вычисляемые свойства
const filteredOrders = computed(() => {
  let filtered = [...props.orders]
  
  // ФИЛЬТРАЦИЯ ПО УДАЛЁННЫМ/НЕУДАЛЁННЫМ ЗАКАЗАМ
  if (showDeletedOrders.value) {
    // Показываем только удалённые заказы (is_deleted = 1)
    filtered = filtered.filter(order => order.is_deleted === 1 || order.is_deleted === true)
  } else {
    // По умолчанию показываем только НЕ удалённые заказы (is_deleted = 0 или null)
    filtered = filtered.filter(order => !order.is_deleted || order.is_deleted === 0)
  }
  
  // Фильтрация по статусу через FilterButton (кроме 'deleted')
  if (activeFilters.value.statuses.length > 0) {
    // Исключаем фильтр 'deleted' из обычной фильтрации статусов
    const statusesWithoutDeleted = activeFilters.value.statuses.filter(s => s !== 'deleted')
    
    if (statusesWithoutDeleted.length > 0) {
      filtered = filtered.filter(order => {
        const orderStatus = order.status
        return statusesWithoutDeleted.includes(orderStatus)
      })
    }
  }
  
  // Фильтрация по старому statusFilter (для обратной совместимости)
  if (statusFilter.value && statusFilter.value !== 'deleted') {
    filtered = filtered.filter(order => order.status === statusFilter.value)
  }
  
  // Фильтрация по поисковому запросу
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(order => {
      const orderId = String(order.id || order.order_id || '').toLowerCase()
      const userName = (order.user_fio || order.user_phone || '').toLowerCase()
      const stationName = (order.station_box_id || order.station_name || order.station_id || '').toLowerCase()
      const powerbankSerial = (order.powerbank_serial || order.powerbank_id || '').toLowerCase()
      
      return orderId.includes(query) || 
             userName.includes(query) || 
             stationName.includes(query) ||
             powerbankSerial.includes(query)
    })
  }
  
  // Сортировка по дате создания (новые сверху)
  filtered.sort((a, b) => {
    const dateA = new Date(a.timestamp || a.created_at)
    const dateB = new Date(b.timestamp || b.created_at)
    return dateB - dateA
  })
  
  return filtered
})

const totalPages = computed(() => {
  return Math.ceil(filteredOrders.value.length / props.itemsPerPage)
})

const paginatedOrders = computed(() => {
  const start = (currentPage.value - 1) * props.itemsPerPage
  const end = start + props.itemsPerPage
  return filteredOrders.value.slice(start, end)
})

const visiblePages = computed(() => {
  const pages = []
  const total = totalPages.value
  const current = currentPage.value
  
  if (total <= 7) {
    for (let i = 1; i <= total; i++) {
      pages.push(i)
    }
  } else {
    if (current <= 4) {
      for (let i = 1; i <= 5; i++) pages.push(i)
      pages.push('...')
      pages.push(total)
    } else if (current >= total - 3) {
      pages.push(1)
      pages.push('...')
      for (let i = total - 4; i <= total; i++) pages.push(i)
    } else {
      pages.push(1)
      pages.push('...')
      for (let i = current - 1; i <= current + 1; i++) pages.push(i)
      pages.push('...')
      pages.push(total)
    }
  }
  
  return pages
})

// Методы
const getOrderRowClass = (status) => {
  return `status-${status}`
}

const getOrderStatusClass = (status) => {
  switch (status) {
    case 'pending': return 'status-pending'
    case 'borrow': return 'status-active'
    case 'return': return 'status-success'
    case 'completed': return 'status-success'
    case 'cancelled': return 'status-error'
    default: return 'status-unknown'
  }
}

const getOrderStatusText = (status) => {
  switch (status) {
    case 'pending': return 'В ожидании'
    case 'borrow': return 'Взято'
    case 'return': return 'Возвращено'
    case 'completed': return 'Завершен'
    case 'cancelled': return 'Отменен'
    default: return status || 'Неизвестно'
  }
}

const getOrderActionText = (action) => {
  switch (action) {
    case 'take': return 'Получение'
    case 'return': return 'Возврат'
    case 'borrow': return 'Взятие'
    case 'eject': return 'Извлечение'
    default: return action || '—'
  }
}

const getStationFullName = (order) => {
  return order.station_box_id || order.station_name || order.station_id || 'N/A'
}

const truncateText = (text, maxLength) => {
  if (!text || text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

const formatTimeOnly = (timestamp) => {
  if (!timestamp) return '—'
  const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp
  if (isNaN(date.getTime())) return '—'
  
  return new Intl.DateTimeFormat('ru-RU', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'Europe/Moscow',
    hour12: false
  }).format(date)
}

const formatDateOnly = (timestamp) => {
  if (!timestamp) return '—'
  const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp
  if (isNaN(date.getTime())) return '—'
  
  return new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: '2-digit',
    timeZone: 'Europe/Moscow'
  }).format(date)
}

// Сброс страницы при изменении поиска
watch(searchQuery, () => {
  currentPage.value = 1
})

// Следим за изменением фильтра "Удалённые"
// Примечание: фильтрация происходит автоматически через computed filteredOrders,
// поэтому дополнительная загрузка не требуется
</script>

<style scoped>
.orders-table-container {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: calc(100vh - 120px);
  max-height: 900px;
}

.orders-table-header {
  padding: 20px 24px;
  border-bottom: 1px solid #e9ecef;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f8f9fa;
  flex-shrink: 0;
}

.orders-table-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.orders-table-title h2 {
  margin: 0;
  color: #333;
  font-size: 1.5rem;
  font-weight: 700;
}

.orders-table-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.search-container {
  position: relative;
  display: flex;
  align-items: center;
}

.search-input {
  padding: 10px 16px 10px 40px;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  width: 300px;
  font-size: 0.9rem;
  transition: border-color 0.3s ease;
}

.search-input:focus {
  outline: none;
  border-color: #667eea;
}

.search-icon {
  position: absolute;
  left: 12px;
  color: #666;
  font-size: 16px;
}

.btn-refresh {
  padding: 10px 20px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: background-color 0.3s ease;
}

.btn-refresh:hover:not(:disabled) {
  background: #5a6fd8;
}

.btn-refresh:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.table-wrapper {
  flex: 1;
  overflow: auto;
  min-height: 0;
  position: relative;
}

.orders-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
  table-layout: auto;
}

.orders-table th {
  background: #f8f9fa;
  padding: 16px 12px;
  text-align: left;
  font-weight: 600;
  color: #333;
  border-bottom: 2px solid #e9ecef;
  position: sticky;
  top: 0;
  z-index: 10;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.orders-table th.col-created {
  padding-left: 12px;
  padding-right: 2px;
}

.orders-table th.col-completed {
  padding-left: 2px;
  padding-right: 12px;
}

.orders-table td {
  padding: 16px 12px;
  border-bottom: 1px solid #e9ecef;
  vertical-align: middle;
  color: #333;
}

.orders-table td.col-created {
  padding-left: 12px;
  padding-right: 2px;
}

.orders-table td.col-completed {
  padding-left: 2px;
  padding-right: 12px;
}

.order-row {
  transition: background-color 0.2s ease;
}

.order-row:hover {
  background: #f8f9fa;
}

.order-row.status-pending {
  border-left: 4px solid #ffc107;
}

.order-row.status-borrow {
  border-left: 4px solid #17a2b8;
}

.order-row.status-return {
  border-left: 4px solid #28a745;
}

.order-row.status-completed {
  border-left: 4px solid #28a745;
}

.order-row.status-cancelled {
  border-left: 4px solid #dc3545;
}

/* Колонки */
.col-id {
  width: 7%;
  min-width: 70px;
  padding-right: 8px !important;
}

.col-user {
  width: 10%;
  min-width: 90px;
  padding-left: 8px !important;
}

.col-phone {
  width: 12%;
  min-width: 110px;
}

.col-station {
  width: 15%;
  min-width: 130px;
}

.col-action {
  width: 10%;
  min-width: 90px;
}

.col-status {
  width: 10%;
  min-width: 90px;
}

.col-created {
  width: 10%;
  min-width: 85px;
}

.col-completed {
  width: 10%;
  min-width: 85px;
}

.col-powerbank {
  width: 10%;
  min-width: 90px;
}

.col-actions {
  width: 10%;
  min-width: 100px;
}

/* Содержимое ячеек */
.order-id-text {
  font-weight: 600;
  color: #667eea;
  font-size: 0.9rem;
}

.user-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.user-name {
  font-size: 0.9rem;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
}

.phone-text {
  font-size: 0.85rem;
  color: #666;
}

.station-text {
  font-size: 0.9rem;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
}

.action-text {
  font-size: 0.9rem;
  color: #666;
}

.status-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.status-badge.status-pending {
  color: #856404;
}

.status-badge.status-active {
  color: #0c5460;
}

.status-badge.status-success {
  color: #155724;
}

.status-badge.status-error {
  color: #721c24;
}

.status-badge.status-unknown {
  color: #666;
}

.datetime-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.time-text {
  font-size: 0.9rem;
  color: #333;
  line-height: 1.2;
}

.date-text {
  font-size: 0.75rem;
  color: #999;
  line-height: 1.2;
}

.powerbank-text {
  font-size: 0.85rem;
  color: #333;
}

.no-powerbank {
  color: #999;
  font-size: 0.9rem;
}

/* Кнопки действий */
.actions-container {
  display: flex;
  gap: 8px;
  justify-content: center;
  align-items: center;
}

.btn-action {
  padding: 6px 12px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 600;
  transition: all 0.3s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 36px;
  height: 36px;
}

.btn-delete {
  background: #ffc107;
  color: #856404;
}

.btn-delete:hover {
  background: #ff9800;
  color: white;
}

.btn-hard-delete {
  background: #dc3545;
  color: white;
}

.btn-hard-delete:hover {
  background: #c82333;
}

.btn-restore {
  background: #28a745;
  color: white;
  font-size: 1.2rem;
}

.btn-restore:hover {
  background: #218838;
}

/* Пагинация */
.pagination {
  padding: 20px 24px;
  border-top: 1px solid #e9ecef;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f8f9fa;
  flex-shrink: 0;
}

.pagination-btn {
  padding: 8px 16px;
  background: white;
  border: 2px solid #e9ecef;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.3s ease;
}

.pagination-btn:hover:not(:disabled) {
  background: #667eea;
  color: white;
  border-color: #667eea;
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination-pages {
  display: flex;
  gap: 4px;
}

.pagination-page {
  padding: 8px 12px;
  background: white;
  border: 2px solid #e9ecef;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.3s ease;
  min-width: 40px;
}

.pagination-page:hover {
  background: #e9ecef;
}

.pagination-page.active {
  background: #667eea;
  color: white;
  border-color: #667eea;
}

/* Пустое состояние */
.empty-state {
  padding: 60px 20px;
  text-align: center;
  color: #666;
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 100%;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-state h3 {
  margin: 0 0 8px 0;
  color: #333;
  font-size: 18px;
}

.empty-state p {
  margin: 0;
  font-size: 14px;
}

/* Мобильные стили */
@media (max-width: 768px) {
  .orders-table-header {
    flex-direction: column;
    gap: 16px;
    align-items: stretch;
  }

  .orders-table-actions {
    flex-direction: column;
    gap: 12px;
  }

  .search-input {
    width: 100%;
  }

  .filter-select {
    width: 100%;
  }

  .pagination {
    flex-direction: column;
    gap: 16px;
  }

  .pagination-pages {
    order: -1;
  }

  .orders-table {
    font-size: 0.9rem;
  }

  .orders-table th,
  .orders-table td {
    padding: 12px 8px;
  }
}
</style>

