<template>
  <div class="stations-table-container">
    <!-- Заголовок с поиском и действиями -->
    <div class="stations-table-header">
      <div class="stations-table-title">
        <h2>Станции</h2>
      </div>
      <div class="stations-table-actions">
        <div class="search-container">
          <input 
            type="text" 
            v-model="searchQuery" 
            placeholder="Поиск по box_id, группе, статусу..." 
            class="search-input"
          />
          <span class="search-icon">🔍</span>
        </div>
        <button @click="$emit('filter-stations')" class="btn-filter-stations">
          🔍 Фильтр
        </button>
      </div>
    </div>

    <!-- Таблица станций -->
    <div class="table-wrapper">
      <table class="stations-table">
        <thead>
          <tr>
            <th class="col-box-id">
              <div class="th-content">
                <span>Box ID</span>
              </div>
            </th>
            <th class="col-org-unit">
              <div class="th-content">
                <span>Группа</span>
              </div>
            </th>
            <th class="col-status">
              <div class="th-content">
                <span>Состояние</span>
              </div>
            </th>
            <th class="col-last-seen">
              <div class="th-content">
                <span>Последний сигнал</span>
              </div>
            </th>
            <th class="col-slots">
              <div class="th-content">
                <span>Слоты</span>
              </div>
            </th>
            <th class="col-actions">
              <div class="th-content">
                <span>Действия</span>
              </div>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr 
            v-for="station in paginatedStations" 
            :key="station.station_id || station.id"
            class="station-row"
            :class="getStationRowClass(station.status)"
            @click="openStationModal(station)"
          >
            <!-- Box ID -->
            <td class="col-box-id">
              <div class="station-box-id">
                <span class="box-id-text">{{ station.box_id || 'N/A' }}</span>
                <span v-if="station.iccid" class="iccid-text">{{ station.iccid }}</span>
              </div>
            </td>

            <!-- Группа -->
            <td class="col-org-unit">
              <div class="org-unit-info">
                <span class="org-unit-name">{{ station.org_unit_name || 'Без группы' }}</span>
                <span v-if="station.address" class="station-address">{{ station.address }}</span>
              </div>
            </td>

            <!-- Состояние -->
            <td class="col-status">
              <div class="status-container">
                <span class="status-indicator" :class="`status-${station.status}`"></span>
                <span class="status-text">{{ getStationStatusText(station.status) }}</span>
              </div>
            </td>

            <!-- Последний сигнал -->
            <td class="col-last-seen">
              <div class="last-seen-info">
                <span class="last-seen-time">{{ formatTime(station.last_seen) }}</span>
                <span v-if="station.last_seen" class="last-seen-relative">{{ getRelativeTime(station.last_seen) }}</span>
              </div>
            </td>

            <!-- Слоты -->
            <td class="col-slots">
              <div class="slots-info">
                <div class="slots-summary">
                  <span class="slots-used">{{ station.occupiedPorts || ((station.slots_declared || 0) - (station.remain_num || 0)) }}</span>
                  <span class="slots-separator">/</span>
                  <span class="slots-total">{{ station.slots_declared || station.totalPorts || 0 }}</span>
                </div>
                <div class="slots-bar">
                  <div 
                    class="slots-progress" 
                    :style="{ width: getSlotsPercentage(station) + '%' }"
                  ></div>
                </div>
              </div>
            </td>

            <!-- Действия -->
            <td class="col-actions">
              <div class="actions-container">
                <button 
                  @click="$emit('view-powerbanks', station)" 
                  class="action-btn action-powerbanks"
                  title="Просмотр павербанков"
                >
                  🔋
                </button>
                <button 
                  @click="$emit('edit-station', station)" 
                  class="action-btn action-edit"
                  title="Редактировать"
                >
                  ✏️
                </button>
                <button 
                  @click="$emit('restart-station', station)" 
                  class="action-btn action-restart"
                  title="Перезагрузить"
                >
                  🔄
                </button>
                <button 
                  @click="$emit('delete-station', station)" 
                  class="action-btn action-delete"
                  title="Удалить"
                >
                  🗑️
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
    <div v-if="filteredStations.length === 0" class="empty-state">
      <div class="empty-icon">🏢</div>
      <h3>Станции не найдены</h3>
      <p v-if="searchQuery">Попробуйте изменить поисковый запрос</p>
      <p v-else>Добавьте первую станцию</p>
    </div>

    <!-- Модальное окно с детальной информацией о станции -->
    <div v-if="isModalOpen" class="modal-overlay" @click="closeStationModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>Детальная информация о станции</h3>
          <button @click="closeStationModal" class="modal-close-btn">×</button>
        </div>
        
        <div class="modal-body" v-if="selectedStation">
          <div class="station-details">
            <!-- Основная информация -->
            <div class="detail-section">
              <h4>Основная информация</h4>
              <div class="detail-grid">
                <div class="detail-item">
                  <label>Box ID:</label>
                  <span>{{ selectedStation.box_id || 'N/A' }}</span>
                </div>
                <div class="detail-item">
                  <label>ICCID:</label>
                  <span>{{ selectedStation.iccid || 'N/A' }}</span>
                </div>
                <div class="detail-item">
                  <label>Статус:</label>
                  <span class="status-badge" :class="`status-${selectedStation.status}`">
                    {{ getStationStatusText(selectedStation.status) }}
                  </span>
                </div>
                <div class="detail-item">
                  <label>Последний сигнал:</label>
                  <span>{{ formatTime(selectedStation.last_seen) }}</span>
                </div>
              </div>
            </div>

            <!-- Информация о группе -->
            <div class="detail-section">
              <h4>Группа и адрес</h4>
              <div class="detail-grid">
                <div class="detail-item">
                  <label>Группа:</label>
                  <span>{{ selectedStation.org_unit_name || 'Без группы' }}</span>
                </div>
                <div class="detail-item">
                  <label>Адрес:</label>
                  <span>{{ selectedStation.address || 'N/A' }}</span>
                </div>
              </div>
            </div>

            <!-- Информация о слотах -->
            <div class="detail-section">
              <h4>Слоты и павербанки</h4>
              <div class="detail-grid">
                <div class="detail-item">
                  <label>Всего слотов:</label>
                  <span>{{ selectedStation.slots_declared || selectedStation.totalPorts || 0 }}</span>
                </div>
                <div class="detail-item">
                  <label>Занято слотов:</label>
                  <span>{{ selectedStation.occupiedPorts || ((selectedStation.slots_declared || 0) - (selectedStation.remain_num || 0)) }}</span>
                </div>
                <div class="detail-item">
                  <label>Свободно слотов:</label>
                  <span>{{ selectedStation.remain_num || 0 }}</span>
                </div>
                <div class="detail-item">
                  <label>Заполненность:</label>
                  <span>{{ getSlotsPercentage(selectedStation) }}%</span>
                </div>
              </div>
              <div class="slots-visual">
                <div class="slots-bar-large">
                  <div 
                    class="slots-progress-large" 
                    :style="{ width: getSlotsPercentage(selectedStation) + '%' }"
                  ></div>
                </div>
              </div>
            </div>

            <!-- Дополнительная информация -->
            <div class="detail-section" v-if="selectedStation.station_id || selectedStation.id">
              <h4>Дополнительная информация</h4>
              <div class="detail-grid">
                <div class="detail-item">
                  <label>ID станции:</label>
                  <span>{{ selectedStation.station_id || selectedStation.id }}</span>
                </div>
                <div class="detail-item" v-if="selectedStation.created_at">
                  <label>Дата создания:</label>
                  <span>{{ formatTime(selectedStation.created_at) }}</span>
                </div>
                <div class="detail-item" v-if="selectedStation.updated_at">
                  <label>Последнее обновление:</label>
                  <span>{{ formatTime(selectedStation.updated_at) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="$emit('view-powerbanks', selectedStation)" class="btn-action">
            🔋 Павербанки
          </button>
          <button @click="$emit('edit-station', selectedStation)" class="btn-action">
            ✏️ Редактировать
          </button>
          <button @click="$emit('restart-station', selectedStation)" class="btn-action">
            🔄 Перезагрузить
          </button>
          <button @click="closeStationModal" class="btn-close">
            Закрыть
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  stations: {
    type: Array,
    default: () => []
  },
  itemsPerPage: {
    type: Number,
    default: 20
  }
})

const emit = defineEmits([
  'filter-stations',
  'view-powerbanks', 
  'edit-station',
  'restart-station',
  'delete-station',
  'station-clicked'
])

// Состояние компонента
const searchQuery = ref('')
const sortField = ref('box_id')
const sortDirection = ref('asc')
const currentPage = ref(1)
const selectedStation = ref(null)
const isModalOpen = ref(false)

// Вычисляемые свойства
const filteredStations = computed(() => {
  let filtered = [...props.stations]
  
  // Фильтрация по поисковому запросу
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(station => {
      const boxId = (station.box_id || '').toLowerCase()
      const orgUnitName = (station.org_unit_name || '').toLowerCase()
      const status = (station.status || '').toLowerCase()
      const iccid = (station.iccid || '').toLowerCase()
      const address = (station.address || '').toLowerCase()
      
      return boxId.includes(query) || 
             orgUnitName.includes(query) || 
             status.includes(query) ||
             iccid.includes(query) ||
             address.includes(query)
    })
  }
  
  // Сортировка
  filtered.sort((a, b) => {
    let aValue = a[sortField.value]
    let bValue = b[sortField.value]
    
    // Обработка специальных случаев
    if (sortField.value === 'last_seen') {
      aValue = new Date(aValue || 0).getTime()
      bValue = new Date(bValue || 0).getTime()
    } else if (typeof aValue === 'string') {
      aValue = aValue.toLowerCase()
      bValue = bValue.toLowerCase()
    }
    
    if (aValue < bValue) return sortDirection.value === 'asc' ? -1 : 1
    if (aValue > bValue) return sortDirection.value === 'asc' ? 1 : -1
    return 0
  })
  
  return filtered
})

const totalPages = computed(() => {
  return Math.ceil(filteredStations.value.length / props.itemsPerPage)
})

const paginatedStations = computed(() => {
  const start = (currentPage.value - 1) * props.itemsPerPage
  const end = start + props.itemsPerPage
  return filteredStations.value.slice(start, end)
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
const openStationModal = (station) => {
  selectedStation.value = station
  isModalOpen.value = true
  emit('station-clicked', station)
}

const closeStationModal = () => {
  isModalOpen.value = false
  selectedStation.value = null
}

const getStationStatusText = (status) => {
  switch (status) {
    case 'active': return 'Активна'
    case 'pending': return 'Ожидает'
    case 'inactive': return 'Неактивна'
    case 'maintenance': return 'Сервис'
    default: return 'Неизвестно'
  }
}

const getStationRowClass = (status) => {
  return `status-${status}`
}

const formatTime = (timestamp) => {
  if (!timestamp) return '—'
  const date = new Date(timestamp)
  return date.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const getRelativeTime = (timestamp) => {
  if (!timestamp) return ''
  const now = new Date()
  const date = new Date(timestamp)
  const diffMs = now - date
  const diffMinutes = Math.floor(diffMs / (1000 * 60))
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  
  if (diffMinutes < 1) return 'только что'
  if (diffMinutes < 60) return `${diffMinutes} мин назад`
  if (diffHours < 24) return `${diffHours} ч назад`
  if (diffDays < 7) return `${diffDays} дн назад`
  return 'давно'
}

const getSlotsPercentage = (station) => {
  const total = station.slots_declared || station.totalPorts || 0
  const used = station.occupiedPorts || ((station.slots_declared || 0) - (station.remain_num || 0))
  if (total === 0) return 0
  return Math.round((used / total) * 100)
}

// Сброс страницы при изменении поиска
watch(searchQuery, () => {
  currentPage.value = 1
})
</script>

<style scoped>
.stations-table-container {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.stations-table-header {
  padding: 20px 24px;
  border-bottom: 1px solid #e9ecef;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f8f9fa;
}

.stations-table-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.stations-table-title h2 {
  margin: 0;
  color: #333;
  font-size: 1.5rem;
  font-weight: 700;
}

.stations-count {
  background: #667eea;
  color: white;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 600;
}

.stations-table-actions {
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

.btn-filter-stations {
  padding: 10px 20px;
  background: #28a745;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: background-color 0.3s ease;
}

.btn-filter-stations:hover {
  background: #218838;
}

.table-wrapper {
  overflow-x: auto;
}

.stations-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
}

.stations-table th {
  background: #f8f9fa;
  padding: 16px 12px;
  text-align: left;
  font-weight: 600;
  color: #333;
  border-bottom: 2px solid #e9ecef;
  position: sticky;
  top: 0;
  z-index: 10;
}

.th-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.sort-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  color: #666;
  transition: color 0.3s ease;
}

.sort-btn:hover {
  color: #667eea;
}

.sort-btn.active {
  color: #667eea;
}

.stations-table td {
  padding: 16px 12px;
  border-bottom: 1px solid #e9ecef;
  vertical-align: middle;
}

.station-row {
  transition: background-color 0.2s ease;
}

.station-row:hover {
  background: #f8f9fa;
}

.station-row.status-active {
  border-left: 4px solid #28a745;
}

.station-row.status-pending {
  border-left: 4px solid #ffc107;
}

.station-row.status-inactive {
  border-left: 4px solid #dc3545;
}

.station-row.status-maintenance {
  border-left: 4px solid #fd7e14;
}

/* Колонки */
.col-box-id {
  width: 15%;
  min-width: 120px;
}

.col-org-unit {
  width: 25%;
  min-width: 200px;
}

.col-status {
  width: 15%;
  min-width: 120px;
}

.col-last-seen {
  width: 20%;
  min-width: 160px;
}

.col-slots {
  width: 15%;
  min-width: 100px;
}

.col-actions {
  width: 10%;
  min-width: 120px;
}

/* Содержимое ячеек */
.station-box-id {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.box-id-text {
  font-weight: 600;
  color: #333;
  font-family: 'Courier New', monospace;
}

.iccid-text {
  font-size: 0.8rem;
  color: #666;
  font-family: 'Courier New', monospace;
}

.org-unit-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.org-unit-name {
  font-weight: 500;
  color: #333;
}

.station-address {
  font-size: 0.8rem;
  color: #666;
}

.status-container {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-indicator.status-active {
  background: #28a745;
  box-shadow: 0 0 8px rgba(40, 167, 69, 0.5);
}

.status-indicator.status-pending {
  background: #ffc107;
  box-shadow: 0 0 8px rgba(255, 193, 7, 0.5);
}

.status-indicator.status-inactive {
  background: #dc3545;
  box-shadow: 0 0 8px rgba(220, 53, 69, 0.5);
}

.status-indicator.status-maintenance {
  background: #fd7e14;
  box-shadow: 0 0 8px rgba(253, 126, 20, 0.5);
}

.status-text {
  font-size: 0.9rem;
  font-weight: 500;
  color: #333;
}

.last-seen-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.last-seen-time {
  font-size: 0.9rem;
  color: #333;
}

.last-seen-relative {
  font-size: 0.8rem;
  color: #666;
}

.slots-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.slots-summary {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.9rem;
  font-weight: 500;
}

.slots-used {
  color: #333;
}

.slots-separator {
  color: #666;
}

.slots-total {
  color: #666;
}

.slots-bar {
  width: 100%;
  height: 4px;
  background: #e9ecef;
  border-radius: 2px;
  overflow: hidden;
}

.slots-progress {
  height: 100%;
  background: #667eea;
  transition: width 0.3s ease;
}

.actions-container {
  display: flex;
  gap: 6px;
  align-items: center;
}

.action-btn {
  background: none;
  border: none;
  padding: 6px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.action-btn:hover {
  transform: scale(1.1);
}

.action-powerbanks:hover {
  background: #d4edda;
}

.action-edit:hover {
  background: #fff3cd;
}

.action-restart:hover {
  background: #d1ecf1;
}

.action-delete:hover {
  background: #f8d7da;
}

/* Пагинация */
.pagination {
  padding: 20px 24px;
  border-top: 1px solid #e9ecef;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f8f9fa;
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
  .stations-table-header {
    flex-direction: column;
    gap: 16px;
    align-items: stretch;
  }

  .stations-table-actions {
    flex-direction: column;
    gap: 12px;
  }

  .search-input {
    width: 100%;
  }

  .pagination {
    flex-direction: column;
    gap: 16px;
  }

  .pagination-pages {
    order: -1;
  }

  .stations-table {
    font-size: 0.9rem;
  }

  .stations-table th,
  .stations-table td {
    padding: 12px 8px;
  }

  .actions-container {
    flex-wrap: wrap;
    gap: 4px;
  }

  .action-btn {
    padding: 4px;
    font-size: 14px;
  }
}

/* Модальное окно */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-content {
  background: white;
  border-radius: 12px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
  max-width: 600px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  animation: modalSlideIn 0.3s ease-out;
}

@keyframes modalSlideIn {
  from {
    opacity: 0;
    transform: scale(0.9) translateY(-20px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.modal-header {
  padding: 20px 24px;
  border-bottom: 1px solid #e9ecef;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f8f9fa;
  border-radius: 12px 12px 0 0;
}

.modal-header h3 {
  margin: 0;
  color: #333;
  font-size: 1.3rem;
  font-weight: 700;
}

.modal-close-btn {
  background: none;
  border: none;
  font-size: 24px;
  color: #666;
  cursor: pointer;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: all 0.2s ease;
}

.modal-close-btn:hover {
  background: #e9ecef;
  color: #333;
}

.modal-body {
  padding: 24px;
}

.station-details {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.detail-section {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  border-left: 4px solid #667eea;
}

.detail-section h4 {
  margin: 0 0 16px 0;
  color: #333;
  font-size: 1.1rem;
  font-weight: 600;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-item label {
  font-weight: 600;
  color: #666;
  font-size: 0.9rem;
}

.detail-item span {
  color: #333;
  font-size: 1rem;
}

.status-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 600;
  text-align: center;
  min-width: 80px;
}

.status-badge.status-active {
  background: #d4edda;
  color: #155724;
}

.status-badge.status-pending {
  background: #fff3cd;
  color: #856404;
}

.status-badge.status-inactive {
  background: #f8d7da;
  color: #721c24;
}

.status-badge.status-maintenance {
  background: #ffeaa7;
  color: #6c5ce7;
}

.slots-visual {
  margin-top: 16px;
}

.slots-bar-large {
  width: 100%;
  height: 8px;
  background: #e9ecef;
  border-radius: 4px;
  overflow: hidden;
}

.slots-progress-large {
  height: 100%;
  background: linear-gradient(90deg, #667eea, #764ba2);
  transition: width 0.3s ease;
}

.modal-footer {
  padding: 20px 24px;
  border-top: 1px solid #e9ecef;
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  background: #f8f9fa;
  border-radius: 0 0 12px 12px;
}

.btn-action {
  padding: 10px 16px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.3s ease;
  font-size: 0.9rem;
}

.btn-action:hover {
  background: #5a6fd8;
}

.btn-close {
  padding: 10px 20px;
  background: #6c757d;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.3s ease;
}

.btn-close:hover {
  background: #5a6268;
}

/* Курсор для кликабельных строк */
.station-row {
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.station-row:hover {
  background: #f8f9fa;
}

/* Мобильные стили для модалки */
@media (max-width: 768px) {
  .modal-overlay {
    padding: 10px;
  }

  .modal-content {
    max-height: 95vh;
  }

  .modal-header {
    padding: 16px 20px;
  }

  .modal-header h3 {
    font-size: 1.1rem;
  }

  .modal-body {
    padding: 20px;
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }

  .modal-footer {
    padding: 16px 20px;
    flex-direction: column;
  }

  .btn-action,
  .btn-close {
    width: 100%;
  }
}

@media (max-width: 480px) {
  .stations-table-header {
    padding: 16px;
  }

  .stations-table-title h2 {
    font-size: 1.3rem;
  }

  .stations-count {
    font-size: 0.75rem;
    padding: 3px 8px;
  }

  .btn-filter-stations {
    padding: 8px 16px;
    font-size: 0.9rem;
  }

  .stations-table th,
  .stations-table td {
    padding: 8px 6px;
  }

  .box-id-text,
  .org-unit-name,
  .status-text {
    font-size: 0.85rem;
  }

  .iccid-text,
  .station-address,
  .last-seen-relative {
    font-size: 0.75rem;
  }
}
</style>
