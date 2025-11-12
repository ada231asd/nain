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
        <RefreshButton @refresh="handleRefresh" />
        <FilterButton 
          filter-type="stations"
          :org-units="orgUnits"
          @filter-change="handleFilterChange"
        />
      </div>
    </div>

    <!-- Таблица станций -->
    <div class="table-wrapper">
      <!-- Индикатор загрузки -->
      <div v-if="isLoading" class="table-loading-overlay">
        <div class="table-loading-spinner"></div>
      </div>
      <table class="stations-table">
        <thead>
          <tr>
            <th class="col-box-id">
              <div class="th-content">
                <span>Box ID/ICCID</span>
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
                  <span class="slots-used">{{ station.remain_num || 0 }}</span>
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
              <div class="detail-rows">
                <div class="detail-row">
                  <span class="detail-label">Box ID:</span>
                  <span class="detail-value">{{ selectedStation.box_id || 'N/A' }}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">ICCID:</span>
                  <span class="detail-value">{{ selectedStation.iccid || 'N/A' }}</span>
                </div>
                <div class="detail-row" :class="{ 'editable-field': isEditing }">
                  <span class="detail-label">Статус:</span>
                  <span v-if="!isEditing" class="detail-value">{{ getStationStatusText(selectedStation.status) }}</span>
                  <div v-else class="status-edit-container">
                    <select v-model="editForm.status" class="edit-input" :disabled="selectedStation.status === 'pending'">
                      <option value="inactive">Неактивна</option>
                      <option v-if="selectedStation.status === 'active'" value="active" disabled>Активна (только через активацию)</option>
                    </select>
                    
                  </div>
                </div>
                <div class="detail-row">
                  <span class="detail-label">Последний сигнал:</span>
                  <span class="detail-value">{{ formatTime(selectedStation.last_seen) }}</span>
                </div>
              </div>
            </div>

            <!-- Информация о группе -->
            <div class="detail-section">
              <h4>Группа и адрес</h4>
              <div class="detail-rows">
                <div class="detail-row" :class="{ 'editable-field': isEditing }">
                  <span class="detail-label">Группа:</span>
                  <span v-if="!isEditing" class="detail-value">{{ selectedStation.org_unit_name || 'Без группы' }}</span>
                  <select v-else v-model="editForm.org_unit_id" class="edit-input">
                    <option value="">Без группы</option>
                    <option v-for="orgUnit in orgUnits" :key="orgUnit.org_unit_id" :value="orgUnit.org_unit_id">
                      {{ orgUnit.name }}
                    </option>
                  </select>
                </div>
                <div class="detail-row" v-if="groupAddressData.adress || groupAddressData.address">
                  <span class="detail-label">Адрес группы:</span>
                  <span class="detail-value">{{ groupAddressData.adress || groupAddressData.address }}</span>
                </div>
              </div>
            </div>

            <!-- Информация о слотах -->
            <div class="detail-section">
              <h4>Слоты и аккумуляторы</h4>
              <div class="detail-rows">
                <div class="detail-row">
                  <span class="detail-label">Всего слотов:</span>
                  <span class="detail-value">{{ selectedStation.slots_declared || selectedStation.totalPorts || 0 }}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">Занято слотов (повербанков):</span>
                  <span class="detail-value">{{ selectedStation.remain_num || 0 }}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">Свободно слотов:</span>
                  <span class="detail-value">{{ Math.max(0, (selectedStation.slots_declared || 0) - (selectedStation.remain_num || 0)) }}</span>
                </div>
              </div>
            </div>

            <!-- Информация о сервере -->
            <div class="detail-section">
              <h4>Настройки сервера</h4>
              <div class="detail-rows">
                <div class="detail-row" :class="{ 'editable-field': isEditing }">
                  <span class="detail-label">Имя сервера:</span>
                  <span v-if="!isEditing" class="detail-value">{{ serverAddressData.address || 'N/A' }}</span>
                  <input v-else v-model="editForm.server_address" class="edit-input" type="text" placeholder="Введите адрес сервера" />
                </div>
                <div class="detail-row" :class="{ 'editable-field': isEditing }">
                  <span class="detail-label">Порт:</span>
                  <span v-if="!isEditing" class="detail-value">{{ serverAddressData.port || 'N/A' }}</span>
                  <input v-else v-model="editForm.server_port" class="edit-input" type="number" placeholder="Введите порт" />
                </div>
                <div class="detail-row" :class="{ 'editable-field': isEditing }">
                  <span class="detail-label">Интервал heartbeat:</span>
                  <span v-if="!isEditing" class="detail-value">{{ serverAddressData.heartbeat_interval || 'N/A' }}</span>
                  <input v-else v-model="editForm.heartbeat_interval" class="edit-input" type="number" placeholder="Введите интервал" />
                </div>
              </div>
            </div>

            <!-- Настройки громкости -->
            <div class="detail-section">
              <h4>Настройки громкости</h4>
              <div class="detail-rows">
                <div class="detail-row">
                  <span class="detail-label">Текущая громкость:</span>
                  <span class="detail-value">{{ currentVoiceVolume }}</span>
                </div>
                <div class="detail-row volume-control-row">
                  <span class="detail-label">Регулировка громкости:</span>
                  <div class="volume-control">
                    <div class="volume-slider-container">
                      <input 
                        type="range" 
                        min="0" 
                        max="15" 
                        step="1"
                        v-model.number="voiceVolumeLevel"
                        @change="updateVoiceVolume"
                        class="volume-slider"
                        :disabled="isVoiceVolumeLoading"
                      />
                      <div class="volume-labels">
                        <span>0</span>
                        <span>5</span>
                        <span>10</span>
                        <span>15</span>
                      </div>
                    </div>
                    <div class="volume-description">
                      <span v-if="voiceVolumeLevel <= 2" class="volume-desc">🔇 Очень тихо</span>
                      <span v-else-if="voiceVolumeLevel <= 4" class="volume-desc">🔉 Тихо</span>
                      <span v-else-if="voiceVolumeLevel <= 6" class="volume-desc">🔊 Средне</span>
                      <span v-else-if="voiceVolumeLevel <= 8" class="volume-desc">🔊 Громко</span>
                      <span v-else-if="voiceVolumeLevel <= 12" class="volume-desc">🔊 Очень громко</span>
                      <span v-else class="volume-desc">🔊 Максимально</span>
                    </div>
                    <div v-if="voiceVolumeError" class="error-message">
                      {{ voiceVolumeError }}
                    </div>
                    <div v-if="isVoiceVolumeLoading" class="loading-indicator">
                      <span>Обновление громкости...</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- QR код -->
            <div class="detail-section">
              <h4>QR код станции</h4>
              <div class="qr-section">
                <div v-if="qrCodeUrl" class="qr-display">
                  <img :src="qrCodeUrl" alt="QR Code" class="qr-image-small" />
                  <div class="qr-info">
                    <p class="qr-link">{{ qrLink }}</p>
                    <button @click="copyQRUrl" class="copy-qr-btn">Копировать ссылку</button>
                  </div>
                </div>
                <div v-else class="qr-loading">
                  <div class="spinner-small"></div>
                  <span>Генерация QR-кода...</span>
                </div>
              </div>
            </div>

            <!-- Дополнительная информация -->
            <div class="detail-section" v-if="selectedStation.station_id || selectedStation.id">
              <h4>Дополнительная информация</h4>
              <div class="detail-rows">
                <div class="detail-row">
                  <span class="detail-label">ID станции:</span>
                  <span class="detail-value">{{ selectedStation.station_id || selectedStation.id }}</span>
                </div>
                <div class="detail-row" v-if="selectedStation.created_at">
                  <span class="detail-label">Дата создания:</span>
                  <span class="detail-value">{{ formatTime(selectedStation.created_at) }}</span>
                </div>
                <div class="detail-row" v-if="selectedStation.updated_at">
                  <span class="detail-label">Последнее обновление:</span>
                  <span class="detail-value">{{ formatTime(selectedStation.updated_at) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <div v-if="isEditing" class="edit-actions">
            <button @click="saveChanges" class="btn-action btn-save">
              💾 Сохранить
            </button>
            <button @click="cancelEdit" class="btn-action btn-cancel">
              ❌ Отменить
            </button>
          </div>
          <div v-else class="view-actions">
            <button @click="$emit('view-powerbanks', selectedStation)" class="btn-action">
              🔋 Аккумуляторы
            </button>
            <button @click="refreshInventory" class="btn-action">
              Обновить
            </button>
            <button @click="toggleEditMode" class="btn-action">
              ✏️ Редактировать
            </button>
            <button v-if="selectedStation.status === 'pending'" @click="showActivationModal" class="btn-action btn-activate">
              🚀 Активировать
            </button>
            <button @click="$emit('restart-station', selectedStation)" class="btn-action">
              🔄 Перезагрузить
            </button>
            <!-- Показываем кнопку восстановления для удалённых -->
            <button 
              v-if="showDeletedStations"
              @click="handleRestore"
              class="btn-action btn-restore"
              title="Восстановить станцию"
            >
              ↺ Восстановить
            </button>
            <!-- Показываем кнопку удаления -->
            <button 
              @click="showDeleteConfirmation" 
              class="btn-action btn-delete"
              :class="{ 'btn-hard-delete': showDeletedStations }"
              :title="showDeletedStations ? 'Удалить навсегда' : 'Удалить станцию'"
            >
              {{ showDeletedStations ? '✕ Удалить навсегда' : '🗑️ Удалить' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Модальное окно активации станции -->
    <div v-if="isActivationModalOpen" class="modal-overlay" @click="closeActivationModal">
      <div class="modal-content activation-modal" @click.stop>
        <div class="modal-header">
          <h3>Активация станции</h3>
          <button @click="closeActivationModal" class="modal-close-btn">×</button>
        </div>
        
        <div class="modal-body">
          <div class="activation-form">
            <div class="form-group">
              <label for="secretKey">Секретный ключ станции *</label>
              <input 
                id="secretKey"
                v-model="activationForm.secretKey" 
                type="password" 
                placeholder="Введите секретный ключ"
                class="form-input"
                @keyup.enter="activateStation"
              />
              <small class="form-hint">
                Секретный ключ необходим для активации станции и обеспечения безопасности
              </small>
            </div>
            
            <div class="station-info">
              <h4>Информация о станции:</h4>
              <div class="info-row">
                <span class="info-label">Box ID:</span>
                <span class="info-value">{{ selectedStation?.box_id || 'N/A' }}</span>
              </div>
              <div class="info-row">
                <span class="info-label">ICCID:</span>
                <span class="info-value">{{ selectedStation?.iccid || 'N/A' }}</span>
              </div>
              <div class="info-row">
                <span class="info-label">Группа:</span>
                <span class="info-value">{{ selectedStation?.org_unit_name || 'Без группы' }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="closeActivationModal" class="btn-action btn-cancel">
            ❌ Отменить
          </button>
          <button 
            @click="activateStation" 
            class="btn-action btn-activate"
            :disabled="!activationForm.secretKey.trim() || isActivating"
          >
            <span v-if="isActivating" class="spinner-small"></span>
            🚀 Активировать станцию
          </button>
        </div>
      </div>
    </div>

    <!-- Модальное окно подтверждения удаления -->
    <div v-if="isDeleteModalOpen" class="modal-overlay" @click="closeDeleteModal">
      <div class="modal-content delete-modal" @click.stop>
        <div class="modal-header">
          <h3>Подтверждение удаления</h3>
          <button @click="closeDeleteModal" class="modal-close-btn">×</button>
        </div>
        
        <div class="modal-body">
          <div class="delete-warning">
            <div class="warning-icon">⚠️</div>
            <div class="warning-content">
              <h4>Вы уверены, что хотите удалить станцию?</h4>
              <p><strong>Box ID:</strong> {{ selectedStation?.box_id || 'N/A' }}</p>
              <p><strong>ICCID:</strong> {{ selectedStation?.iccid || 'N/A' }}</p>
              <p><strong>Группа:</strong> {{ selectedStation?.org_unit_name || 'Без группы' }}</p>
              <div class="warning-text">
                <p>⚠️ Это действие нельзя отменить!</p>
                <p>Все данные о станции будут безвозвратно удалены.</p>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="closeDeleteModal" class="btn-action btn-cancel">
            ❌ Отменить
          </button>
          <button 
            @click="confirmDeleteStation" 
            class="btn-action btn-delete-confirm"
            :disabled="isDeleting"
          >
            <span v-if="isDeleting" class="spinner-small"></span>
            🗑️ Удалить станцию
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import FilterButton from './FilterButton.vue'
import RefreshButton from '../RefreshButton.vue'
import QRCode from 'qrcode'
import { pythonAPI } from '../../api/pythonApi.js'
import { formatMoscowTime, getRelativeTime as getRelativeTimeUtil } from '../../utils/timeUtils.js'
import { showSuccess, showError, showWarning, showInfo, showConfirm } from '../../utils/notifications'

const props = defineProps({
  stations: {
    type: Array,
    default: () => []
  },
  orgUnits: {
    type: Array,
    default: () => []
  },
  itemsPerPage: {
    type: Number,
    default: 50
  }
})

const emit = defineEmits([
  'filter-stations',
  'view-powerbanks', 
  'restart-station',
  'delete-station',
  'restore-station',
  'station-clicked',
  'station-updated',
  'add-station',
  'refresh'
])

// Состояние компонента
const searchQuery = ref('')
const sortField = ref('box_id')
const sortDirection = ref('asc')
const currentPage = ref(1)
const itemsPerPage = ref(props.itemsPerPage)
const selectedStation = ref(null)
const isModalOpen = ref(false)
const isLoading = ref(false)
const activeFilters = ref({
  orgUnits: [],
  statuses: [],
  roles: []
})

// Проверка, показываем ли удалённые станции
const showDeletedStations = computed(() => {
  return activeFilters.value.statuses.includes('deleted')
})

// Новые переменные для модального окна
const serverAddressData = ref({})
const voiceVolumeData = ref({})
const currentVoiceVolume = ref(0)
const voiceVolumeLevel = ref(0)
const isVoiceVolumeLoading = ref(false)
const voiceVolumeError = ref('')
const qrCodeUrl = ref('')
const qrLink = ref('')
const groupAddressData = ref({})

// Состояние редактирования
const isEditing = ref(false)
const editForm = ref({
  status: '',
  org_unit_id: '',
  server_address: '',
  server_port: '',
  heartbeat_interval: ''
})

// Состояние активации станции
const isActivationModalOpen = ref(false)
const isActivating = ref(false)
const activationForm = ref({
  secretKey: ''
})

// Состояние удаления станции
const isDeleteModalOpen = ref(false)
const isDeleting = ref(false)

// Вычисляемые свойства
const filteredStations = computed(() => {
  let filtered = [...props.stations]
  
  // ФИЛЬТРАЦИЯ ПО УДАЛЁННЫМ/НЕУДАЛЁННЫМ СТАНЦИЯМ
  if (showDeletedStations.value) {
    // Показываем только удалённые станции (is_deleted = 1)
    filtered = filtered.filter(station => station.is_deleted === 1 || station.is_deleted === true)
  } else {
    // По умолчанию показываем только НЕ удалённые станции (is_deleted = 0 или null)
    filtered = filtered.filter(station => !station.is_deleted || station.is_deleted === 0)
  }
  
  // Фильтрация по группам/подгруппам
  if (activeFilters.value.orgUnits.length > 0) {
    filtered = filtered.filter(station => {
      return activeFilters.value.orgUnits.includes(station.org_unit_id)
    })
  }
  
  // Фильтрация по статусу (кроме 'deleted')
  if (activeFilters.value.statuses.length > 0) {
    // Исключаем фильтр 'deleted' из обычной фильтрации статусов
    const statusesWithoutDeleted = activeFilters.value.statuses.filter(s => s !== 'deleted')
    
    if (statusesWithoutDeleted.length > 0) {
      filtered = filtered.filter(station => {
        return statusesWithoutDeleted.includes(station.status)
      })
    }
  }
  
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
const handleFilterChange = (filters) => {
  activeFilters.value = filters
  currentPage.value = 1 // Сбрасываем на первую страницу при изменении фильтров
}

const handleRefresh = async () => {
  if (isLoading.value) return
  isLoading.value = true
  try {
    await emit('refresh')
  } finally {
    isLoading.value = false
  }
}

const openStationModal = async (station) => {
  selectedStation.value = station
  isModalOpen.value = true
  isEditing.value = false
  emit('station-clicked', station)
  
  // Инициализируем форму редактирования
  initEditForm(station)
  
  // Загружаем дополнительные данные
  await loadStationData(station)
}

const closeStationModal = () => {
  isModalOpen.value = false
  selectedStation.value = null
  isEditing.value = false
  // Очищаем данные
  serverAddressData.value = {}
  voiceVolumeData.value = {}
  currentVoiceVolume.value = 0
  voiceVolumeLevel.value = 0
  isVoiceVolumeLoading.value = false
  voiceVolumeError.value = ''
  qrCodeUrl.value = ''
  qrLink.value = ''
  groupAddressData.value = {}
  editForm.value = {
    status: '',
    org_unit_id: '',
    server_address: '',
    server_port: '',
    heartbeat_interval: ''
  }
}

// Загрузка дополнительных данных станции
const loadStationData = async (station) => {
  const stationId = station.station_id || station.id
  if (!stationId) return
  
  try {
    // Загружаем данные сервера
    await loadServerAddressData(stationId)
    
    // Загружаем данные громкости
    await loadVoiceVolumeData(stationId)
    
    // Загружаем адрес группы
    await loadGroupAddressData(station)
    
    // Генерируем QR код
    await generateQRCode(station)
    
    // Обновляем форму редактирования с актуальными данными
    initEditForm(station)
  } catch (error) {
    console.error('Ошибка загрузки данных станции:', error)
  }
}

// Загрузка данных сервера
const loadServerAddressData = async (stationId) => {
  try {
    // Сначала запрашиваем адрес сервера
    await pythonAPI.queryServerAddress(stationId)
    
    // Ждем немного для обработки запроса
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    // Затем получаем данные
    const response = await pythonAPI.getServerAddress(stationId)
    if (response.success) {
      serverAddressData.value = response.server_address || {}
    } else {
      console.warn('Данные о сервере не найдены:', response.error)
    }
  } catch (error) {
    console.error('Ошибка загрузки данных сервера:', error)
  }
}

// Загрузка данных громкости
const loadVoiceVolumeData = async (stationId) => {
  try {
    isVoiceVolumeLoading.value = true
    voiceVolumeError.value = ''
    
    // Сначала триггерим запрос уровня громкости через TCP
    await pythonAPI.queryVoiceVolume(stationId)

    // Затем пробуем получить данные (может потребоваться время)
    // Делаем до 15 попыток c интервалом ~1000мс
    let lastError = ''
    for (let attempt = 0; attempt < 15; attempt++) {
      try {
        const data = await pythonAPI.getVoiceVolume(stationId)
        if (data.success) {
          const volumeLevel = data.voice_volume?.volume_level || 0
          currentVoiceVolume.value = volumeLevel
          voiceVolumeLevel.value = volumeLevel
          voiceVolumeData.value = data.voice_volume || {}
          lastError = ''
          break
        } else {
          lastError = data.error || 'Не удалось получить текущую громкость'
        }
      } catch (e) {
        lastError = e?.message || 'Не удалось получить текущую громкость'
      }
      // подождать перед следующей попыткой
      await new Promise(r => setTimeout(r, 1000))
    }
    if (lastError) {
      voiceVolumeError.value = lastError
    }
  } catch (err) {
    console.error('Ошибка при загрузке громкости:', err)
    voiceVolumeError.value = 'Ошибка при загрузке громкости: ' + (err.message || 'Неизвестная ошибка')
  } finally {
    isVoiceVolumeLoading.value = false
  }
}

// Загрузка адреса группы
const loadGroupAddressData = async (station) => {
  try {
    const orgUnitId = station.org_unit_id
    if (!orgUnitId) {
      groupAddressData.value = {}
      return
    }

    // Используем pythonAPI вместо прямого fetch
    const response = await pythonAPI.getOrgUnit(orgUnitId)
    if (response.success && response.data) {
      // Проверяем, является ли data.data массивом или объектом
      if (Array.isArray(response.data) && response.data.length > 0) {
        groupAddressData.value = response.data[0] || {}
      } else if (response.data && typeof response.data === 'object') {
        groupAddressData.value = response.data
      }
    }
  } catch (error) {
    console.error('Ошибка загрузки адреса группы:', error)
  }
}

// Методы для редактирования
const initEditForm = (station) => {
  editForm.value = {
    status: station.status || '',
    org_unit_id: station.org_unit_id || '',
    server_address: serverAddressData.value?.address || '',
    server_port: serverAddressData.value?.port || '',
    heartbeat_interval: serverAddressData.value?.heartbeat_interval || ''
  }
}

const toggleEditMode = () => {
  if (!isEditing.value) {
    // Включаем режим редактирования
    initEditForm(selectedStation.value)
  }
  isEditing.value = !isEditing.value
}

const cancelEdit = () => {
  isEditing.value = false
  initEditForm(selectedStation.value)
}

const saveChanges = async () => {
  const stationId = selectedStation.value?.station_id || selectedStation.value?.id
  if (!stationId) return
  
  // Валидация статуса
  if (selectedStation.value.status === 'pending') {
    showWarning('Станция в статусе "Ожидает" не может быть изменена через редактирование. Используйте кнопку "🚀 Активировать" для активации.')
    return
  }
  
  if (editForm.value.status === 'active' && selectedStation.value.status !== 'active') {
    showWarning('Нельзя активировать станцию через редактирование. Используйте кнопку "🚀 Активировать" для ввода секретного ключа.')
    return
  }
  
  if (selectedStation.value.status === 'active' && editForm.value.status === 'pending') {
    showWarning('Нельзя перевести активную станцию в статус "Ожидает".')
    return
  }
  
  try {
    // Обновляем данные станции
    const stationUpdateData = {
      status: editForm.value.status,
      org_unit_id: editForm.value.org_unit_id || null
    }
    
    // Отправляем обновление станции используя pythonAPI
    const stationResponse = await pythonAPI.updateStation(stationId, stationUpdateData)
    
    if (!stationResponse.success) {
      throw new Error(stationResponse.error || 'Ошибка обновления станции')
    }
    
    // Обновляем настройки сервера, если они изменились
    if (editForm.value.server_address || editForm.value.server_port || editForm.value.heartbeat_interval) {
      const serverUpdateData = {
        station_id: stationId,
        server_address: editForm.value.server_address,
        server_port: editForm.value.server_port ? parseInt(editForm.value.server_port) : null,
        heartbeat_interval: editForm.value.heartbeat_interval ? parseInt(editForm.value.heartbeat_interval) : null
      }
      
      // Используем pythonAPI вместо прямого fetch для автоматического добавления токена авторизации
      const serverResponse = await pythonAPI.setServerAddress(serverUpdateData)
      
      if (!serverResponse.success) {
        throw new Error(serverResponse.error || 'Ошибка обновления настроек сервера')
      }
    }
    
    // Обновляем локальные данные
    selectedStation.value.status = editForm.value.status
    selectedStation.value.org_unit_id = editForm.value.org_unit_id
    
    // Обновляем данные сервера
    if (editForm.value.server_address) serverAddressData.value.address = editForm.value.server_address
    if (editForm.value.server_port) serverAddressData.value.port = editForm.value.server_port
    if (editForm.value.heartbeat_interval) serverAddressData.value.heartbeat_interval = editForm.value.heartbeat_interval
    
    isEditing.value = false
    showSuccess('Изменения сохранены успешно')
    
    // Обновляем список станций
    emit('station-updated', selectedStation.value)
    
  } catch (error) {
    console.error('Ошибка сохранения изменений:', error)
    showError('Ошибка сохранения: ' + error.message)
  }
}

// Методы для активации станции
const showActivationModal = () => {
  isActivationModalOpen.value = true
  activationForm.value.secretKey = ''
}

const closeActivationModal = () => {
  isActivationModalOpen.value = false
  activationForm.value.secretKey = ''
  isActivating.value = false
}

const activateStation = async () => {
  const stationId = selectedStation.value?.station_id || selectedStation.value?.id
  if (!stationId || !activationForm.value.secretKey.trim()) return
  
  isActivating.value = true
  
  try {
    // Используем pythonAPI вместо прямого fetch для автоматического добавления токена авторизации
    const response = await pythonAPI.createStationSecretKey({
      station_id: stationId,
      key_value: activationForm.value.secretKey.trim()
    })
    
    if (response.success) {
      // Обновляем статус станции на активную
      selectedStation.value.status = 'active'
      
      // Закрываем модальное окно активации
      closeActivationModal()
      
      showSuccess('Станция успешно активирована!')
      
      // Обновляем список станций
      emit('station-updated', selectedStation.value)
    } else {
      throw new Error(response.error || 'Ошибка активации станции')
    }
  } catch (error) {
    console.error('Ошибка активации станции:', error)
    showError('Ошибка активации: ' + (error.message || 'Неизвестная ошибка'))
  } finally {
    isActivating.value = false
  }
}

// Обновление громкости
const updateVoiceVolume = async (event) => {
  const volumeLevel = parseInt(event.target.value)
  const stationId = selectedStation.value?.station_id || selectedStation.value?.id
  
  if (!stationId) return
  
  try {
    isVoiceVolumeLoading.value = true
    voiceVolumeError.value = ''
    
    const data = await pythonAPI.setVoiceVolume({
      station_id: stationId,
      volume_level: volumeLevel
    })
    
    if (data.success) {
      currentVoiceVolume.value = volumeLevel
      voiceVolumeData.value.volume_level = volumeLevel
      // Показываем уведомление об успехе
      console.log('Громкость успешно обновлена')
    } else {
      voiceVolumeError.value = 'Не удалось установить громкость'
    }
  } catch (error) {
    console.error('Ошибка обновления громкости:', error)
    voiceVolumeError.value = 'Ошибка при сохранении громкости: ' + (error.message || 'Неизвестная ошибка')
  } finally {
    isVoiceVolumeLoading.value = false
  }
}

// Генерация QR кода
const generateQRCode = async (station) => {
  try {
    const stationName = station.name || station.station_name || station.box_id || `Станция ${station.station_id || station.id}`
    const baseUrl = window.location.origin
    const authUrl = `${baseUrl}/${encodeURIComponent(stationName)}`
    
    qrLink.value = authUrl
    
    const qrCodeDataURL = await QRCode.toDataURL(authUrl, {
      width: 150,
      margin: 2,
      color: {
        dark: '#000000',
        light: '#FFFFFF'
      }
    })
    
    qrCodeUrl.value = qrCodeDataURL
  } catch (error) {
    console.error('Ошибка генерации QR-кода:', error)
  }
}

// Обновление инвентаря
const refreshInventory = async () => {
  const stationId = selectedStation.value?.station_id || selectedStation.value?.id
  
  if (!stationId) {
    showError('Не удалось определить ID станции')
    return
  }
  
  try {
    // Сначала запрашиваем обновление инвентаря
    await pythonAPI.queryInventory(stationId)
    
    // Ждем немного для обработки запроса
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    // Затем получаем обновленные данные
    const data = await pythonAPI.getStationInventory(stationId)
    
    if (data.success) {
      showSuccess('Инвентарь успешно обновлен')
      // Можно добавить обновление данных станции
      await loadStationData(selectedStation.value)
    } else {
      showError('Ошибка обновления инвентаря: ' + (data.error || 'Неизвестная ошибка'))
    }
  } catch (error) {
    console.error('Ошибка обновления инвентаря:', error)
    showError('Ошибка обновления инвентаря: ' + error.message)
  }
}

// Копирование QR ссылки
const copyQRUrl = async () => {
  try {
    await navigator.clipboard.writeText(qrLink.value)
    showSuccess('Ссылка скопирована в буфер обмена')
  } catch (error) {
    console.error('Ошибка копирования:', error)
    // Fallback для старых браузеров
    const textArea = document.createElement('textarea')
    textArea.value = qrLink.value
    document.body.appendChild(textArea)
    textArea.select()
    document.execCommand('copy')
    document.body.removeChild(textArea)
    showSuccess('Ссылка скопирована в буфер обмена')
  }
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

const formatTime = (timestamp) => formatMoscowTime(timestamp, {
  day: '2-digit',
  month: '2-digit',
  year: '2-digit',
  hour: '2-digit',
  minute: '2-digit'
})

const getRelativeTime = (timestamp) => getRelativeTimeUtil(timestamp)

const getSlotsPercentage = (station) => {
  const total = station.slots_declared || station.totalPorts || 0
  // remain_num = количество повербанков (занятых слотов)
  const used = station.remain_num || 0
  if (total === 0) return 0
  return Math.round((used / total) * 100)
}

// Функции для работы с удалением станции
const showDeleteConfirmation = () => {
  isDeleteModalOpen.value = true
}

const closeDeleteModal = () => {
  isDeleteModalOpen.value = false
}

const confirmDeleteStation = async () => {
  if (!selectedStation.value) return
  
  const stationId = selectedStation.value.station_id || selectedStation.value.id
  if (!stationId) {
    showError('Не удалось определить ID станции')
    return
  }
  
  // Сохраняем данные до закрытия модального окна
  const deleteData = {
    stationId,
    hardDelete: showDeletedStations.value,
    stationName: selectedStation.value.box_id
  }
  
  // Закрываем модальные окна
  closeDeleteModal()
  closeStationModal()
  
  // Эмитим события с сохранёнными данными
  emit('delete-station', deleteData)
  emit('station-updated')
}

// Восстановление удалённой станции
const handleRestore = async () => {
  if (!selectedStation.value) return
  
  const stationId = selectedStation.value.station_id || selectedStation.value.id
  if (!stationId) {
    showError('Не удалось определить ID станции')
    return
  }
  
  // Сохраняем данные до закрытия модального окна
  const restoreData = {
    stationId,
    stationName: selectedStation.value.box_id
  }
  
  // Закрываем модальное окно
  closeStationModal()
  
  // Эмитим события с сохранёнными данными
  emit('restore-station', restoreData)
  emit('station-updated')
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
  position: relative;
}

.table-loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.table-loading-spinner {
  width: 50px;
  height: 50px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
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
  width: 20%;
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
  max-width: 630px;
  width: 100%;
  max-height: 90vh;
  overflow: hidden;
  animation: modalSlideIn 0.3s ease-out;
  display: flex;
  flex-direction: column;
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
  overflow-y: auto;
  flex: 1;
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

.detail-rows {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.detail-row:last-child {
  border-bottom: none;
}

.detail-label {
  font-weight: 600;
  color: #666;
  font-size: 0.9rem;
  min-width: 140px;
}

.detail-value {
  color: #333;
  font-size: 1rem;
  text-align: right;
  flex: 1;
}

.editable-field {
  background: rgba(102, 126, 234, 0.05);
  border-radius: 6px;
  padding: 8px;
  border: 2px solid transparent;
  transition: all 0.3s ease;
}

.editable-field:hover {
  background: rgba(102, 126, 234, 0.1);
  border-color: rgba(102, 126, 234, 0.3);
}

.edit-input {
  width: 100%;
  padding: 8px 12px;
  border: 2px solid #e9ecef;
  border-radius: 6px;
  font-size: 0.9rem;
  background: white;
  transition: border-color 0.3s ease;
}

.edit-input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.edit-input[type="number"] {
  text-align: right;
}

.edit-input:disabled {
  background-color: #f8f9fa;
  color: #6c757d;
  cursor: not-allowed;
  opacity: 0.6;
}

.volume-control-row {
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
}

.volume-control {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
}

.volume-slider-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.volume-slider {
  width: 100%;
  height: 8px;
  border-radius: 4px;
  background: #e9ecef;
  outline: none;
  -webkit-appearance: none;
  appearance: none;
  cursor: pointer;
}

.volume-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #667eea;
  cursor: pointer;
  border: 2px solid white;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
}

.volume-slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #667eea;
  cursor: pointer;
  border: 2px solid white;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
}

.volume-slider:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.volume-labels {
  display: flex;
  justify-content: space-between;
  font-size: 0.8rem;
  color: #666;
}

.volume-description {
  text-align: center;
  margin-top: 8px;
}

.volume-desc {
  font-size: 0.9rem;
  color: #333;
  font-weight: 500;
}

.error-message {
  background: #f8d7da;
  color: #721c24;
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px solid #f5c6cb;
  font-size: 0.85rem;
  margin-top: 8px;
}

.loading-indicator {
  text-align: center;
  color: #667eea;
  font-size: 0.85rem;
  font-style: italic;
  margin-top: 8px;
}

.qr-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.qr-display {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.qr-image-small {
  width: 150px;
  height: 150px;
  border: 2px solid #e9ecef;
  border-radius: 8px;
}

.qr-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.qr-link {
  font-size: 0.8rem;
  color: #666;
  word-break: break-all;
  text-align: center;
  margin: 0;
}

.copy-qr-btn {
  padding: 6px 12px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
  transition: background-color 0.3s ease;
}

.copy-qr-btn:hover {
  background: #5a6fd8;
}

.qr-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: #666;
}

.spinner-small {
  width: 20px;
  height: 20px;
  border: 2px solid #e9ecef;
  border-top: 2px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.modal-footer {
  padding: 20px 24px;
  border-top: 1px solid #e9ecef;
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  background: #f8f9fa;
  border-radius: 0 0 12px 12px;
  flex-shrink: 0;
}

.btn-action {
  padding: 8px 12px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.3s ease;
  font-size: 0.8rem;
  white-space: nowrap;
  flex-shrink: 0;
}

.btn-action:hover {
  background: #5a6fd8;
}

.btn-save {
  background: #28a745;
}

.btn-save:hover {
  background: #218838;
}

.btn-cancel {
  background: #dc3545;
}

.btn-cancel:hover {
  background: #c82333;
}

.btn-activate {
  background: #28a745;
}

.btn-activate:hover:not(:disabled) {
  background: #218838;
}

.btn-activate:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.activation-modal {
  max-width: 500px;
}

.activation-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  font-weight: 600;
  color: #333;
  font-size: 0.9rem;
}

.form-input {
  padding: 12px 16px;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  font-size: 1rem;
  background: white;
  transition: border-color 0.3s ease;
}

.form-input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.form-hint {
  font-size: 0.8rem;
  color: #666;
  font-style: italic;
}

.station-info {
  background: #f8f9fa;
  padding: 16px;
  border-radius: 8px;
  border-left: 4px solid #28a745;
}

.station-info h4 {
  margin: 0 0 12px 0;
  color: #333;
  font-size: 1rem;
  font-weight: 600;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  border-bottom: 1px solid #e9ecef;
}

.info-row:last-child {
  border-bottom: none;
}

.info-label {
  font-weight: 500;
  color: #666;
  font-size: 0.9rem;
}

.info-value {
  color: #333;
  font-size: 0.9rem;
  font-weight: 500;
}

.status-edit-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.status-hint {
  font-size: 0.8rem;
  color: #666;
  font-style: italic;
  padding: 6px 8px;
  background: rgba(102, 126, 234, 0.1);
  border-radius: 4px;
  border-left: 3px solid #667eea;
}

.edit-actions {
  display: flex;
  gap: 8px;
  justify-content: center;
  width: 100%;
  flex-wrap: nowrap;
}

.view-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  flex-wrap: nowrap;
  overflow-x: auto;
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

  .detail-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }

  .detail-label {
    min-width: auto;
  }

  .detail-value {
    text-align: left;
  }

  .volume-control {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }

  .qr-image-small {
    width: 120px;
    height: 120px;
  }

  .modal-footer {
    padding: 16px 20px;
    flex-direction: column;
    flex-shrink: 0;
  }

  .btn-action {
    padding: 6px 10px;
    font-size: 0.75rem;
  }
}

/* Стили для кнопки удаления */
.btn-delete {
  background: #ffc107;
  color: #856404;
  border: none;
  transition: all 0.3s ease;
}

.btn-delete:hover {
  background: #ff9800;
  color: white;
}

.btn-delete:active {
  transform: translateY(0);
}

/* Стили для кнопки жёсткого удаления */
.btn-hard-delete {
  background: #dc3545 !important;
  color: white !important;
}

.btn-hard-delete:hover {
  background: #c82333 !important;
}

/* Стили для кнопки восстановления */
.btn-restore {
  background: #28a745;
  color: white;
  font-size: 1.2rem;
}

.btn-restore:hover {
  background: #218838;
}

/* Стили для модального окна удаления */
.delete-modal {
  max-width: 500px;
}

.delete-warning {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

.warning-icon {
  font-size: 2rem;
  flex-shrink: 0;
}

.warning-content {
  flex: 1;
}

.warning-content h4 {
  margin: 0 0 12px 0;
  color: #e53e3e;
  font-size: 1.1rem;
}

.warning-content p {
  margin: 8px 0;
  color: #4a5568;
}

.warning-text {
  margin-top: 16px;
  padding: 12px;
  background: #fef5e7;
  border: 1px solid #f6ad55;
  border-radius: 8px;
}

.warning-text p {
  margin: 4px 0;
  color: #c05621;
  font-weight: 500;
}

/* Стили для кнопки подтверждения удаления */
.btn-delete-confirm {
  background: linear-gradient(135deg, #e53e3e, #c53030);
  color: white;
  border: none;
  font-weight: 600;
  transition: all 0.3s ease;
}

.btn-delete-confirm:hover:not(:disabled) {
  background: linear-gradient(135deg, #c53030, #9c2626);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(229, 62, 62, 0.4);
}

.btn-delete-confirm:disabled {
  background: #a0aec0;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.edit-actions {
  flex-wrap: wrap;
  gap: 6px;
}

.view-actions {
  flex-wrap: wrap;
  gap: 6px;
  justify-content: center;
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
