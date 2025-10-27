<template>
  <div class="powerbanks-table-container">
    <!-- Заголовок с поиском и действиями -->
    <div class="powerbanks-table-header">
      <div class="powerbanks-table-title">
        <h2>Аккумуляторы</h2>
      </div>
      <div class="powerbanks-table-actions">
        <div class="search-container">
          <input 
            type="text" 
            v-model="searchQuery" 
            placeholder="Поиск по серийному номеру, ID..." 
            class="search-input"
          />
          <span class="search-icon">🔍</span>
        </div>
        <FilterButton 
          filter-type="powerbanks"
          :org-units="orgUnits"
          @filter-change="handleFilterChange"
        />
      </div>
    </div>

    <!-- Статистика -->
    <div class="stats-bar">
      <div class="stat-item">
        <span class="stat-label">Всего:</span>
        <span class="stat-value">{{ filteredPowerbanks.length }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">Активные:</span>
        <span class="stat-value">{{ activeCount }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">Сломанные:</span>
        <span class="stat-value">{{ brokenCount }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">Списанные:</span>
        <span class="stat-value">{{ writtenOffCount }}</span>
      </div>
    </div>

    <!-- Таблица аккумуляторов -->
    <div class="table-wrapper">
      <table class="powerbanks-table">
        <thead>
          <tr>
            <th class="col-id">ID</th>
            <th class="col-serial">Серийный номер</th>
            <th class="col-org-unit">Группа</th>
            <th class="col-soh">SOH</th>
            <th class="col-status">Статус</th>
            <th class="col-error">Ошибка/Причина</th>
            <th class="col-created">Создан</th>
          </tr>
        </thead>
        <tbody>
          <tr 
            v-for="powerbank in paginatedPowerbanks" 
            :key="powerbank.id"
            class="powerbank-row"
            :class="getPowerbankRowClass(powerbank.status)"
            @click="openPowerbankModal(powerbank)"
          >
            <!-- ID -->
            <td class="col-id">
              <span class="id-text">{{ powerbank.id }}</span>
            </td>

            <!-- Серийный номер -->
            <td class="col-serial">
              <span class="serial-text">{{ powerbank.serial_number || 'N/A' }}</span>
            </td>

            <!-- Группа -->
            <td class="col-org-unit">
              <span class="org-unit-text">{{ getOrgUnitName(powerbank.org_unit_id) || 'Не назначена' }}</span>
            </td>

            <!-- SOH -->
            <td class="col-soh">
              <div class="soh-container">
                <span class="soh-text">{{ powerbank.soh || 0 }}%</span>
                <div class="soh-bar">
                  <div 
                    class="soh-progress" 
                    :style="{ width: (powerbank.soh || 0) + '%' }"
                    :class="getSohClass(powerbank.soh)"
                  ></div>
                </div>
              </div>
            </td>

            <!-- Статус -->
            <td class="col-status">
              <div class="status-container">
                <span class="status-indicator" :class="`status-${powerbank.status}`"></span>
                <span class="status-text">{{ getStatusText(powerbank.status) }}</span>
              </div>
            </td>

            <!-- Ошибка/Причина -->
            <td class="col-error">
              <span v-if="powerbank.status === 'system_error' && powerbank.error_type" class="error-text">
                {{ powerbank.error_type }}
              </span>
              <span v-else-if="powerbank.write_off_reason && powerbank.write_off_reason !== 'none'" class="error-text">
                {{ getWriteOffReasonText(powerbank.write_off_reason) }}
              </span>
              <span v-else class="no-error">—</span>
            </td>

            <!-- Создан -->
            <td class="col-created">
              <span class="date-text">{{ formatTime(powerbank.created_at) }}</span>
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
    <div v-if="filteredPowerbanks.length === 0" class="empty-state">
      <div class="empty-icon">🔋</div>
      <h3>Аккумуляторы не найдены</h3>
      <p v-if="searchQuery">Попробуйте изменить поисковый запрос</p>
      <p v-else>Аккумуляторы отсутствуют</p>
    </div>

    <!-- Модальное окно с детальной информацией -->
    <div v-if="isModalOpen" class="modal-overlay" @click="closePowerbankModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>Детальная информация об аккумуляторе</h3>
          <button @click="closePowerbankModal" class="modal-close-btn">×</button>
        </div>
        
        <div class="modal-body" v-if="selectedPowerbank">
          <div class="powerbank-details">
            <!-- Основная информация -->
            <div class="detail-section">
              <h4>Основная информация</h4>
              <div class="detail-rows">
                <div class="detail-row">
                  <span class="detail-label">ID:</span>
                  <span class="detail-value">{{ selectedPowerbank.id }}</span>
                </div>
                <div class="detail-row" :class="{ 'editable-field': isEditing }">
                  <span class="detail-label">Серийный номер:</span>
                  <span v-if="!isEditing" class="detail-value">{{ selectedPowerbank.serial_number || 'N/A' }}</span>
                  <input v-else v-model="editForm.serial_number" class="edit-input" type="text" placeholder="Серийный номер" />
                </div>
                <div class="detail-row" :class="{ 'editable-field': isEditing }">
                  <span class="detail-label">Группа:</span>
                  <span v-if="!isEditing" class="detail-value">{{ getOrgUnitName(selectedPowerbank.org_unit_id) || 'Не назначена' }}</span>
                  <select v-else v-model="editForm.org_unit_id" class="edit-input">
                    <option value="">Без группы</option>
                    <option v-for="orgUnit in orgUnits" :key="orgUnit.org_unit_id" :value="orgUnit.org_unit_id">
                      {{ orgUnit.name }}
                    </option>
                  </select>
                </div>
                <div class="detail-row">
                  <span class="detail-label">SOH:</span>
                  <span class="detail-value">{{ selectedPowerbank.soh || 0 }}%</span>
                </div>
              </div>
            </div>

            <!-- Статус и ошибки -->
            <div class="detail-section">
              <h4>Статус и ошибки</h4>
              <div class="detail-rows">
                <div class="detail-row" :class="{ 'editable-field': isEditing }">
                  <span class="detail-label">Статус:</span>
                  <span v-if="!isEditing" class="detail-value">{{ getStatusText(selectedPowerbank.status) }}</span>
                  <select v-else v-model="editForm.status" class="edit-input">
                    <option value="active">Активный</option>
                    <option value="user_reported_broken">Сломан (пользователь)</option>
                    <option value="system_error">Ошибка системы</option>
                    <option value="written_off">Списан</option>
                  </select>
                </div>
                <div v-if="selectedPowerbank.status === 'system_error'" class="detail-row">
                  <span class="detail-label">Тип ошибки:</span>
                  <span class="detail-value error-text">{{ selectedPowerbank.error_type || 'N/A' }}</span>
                </div>
                <div v-if="selectedPowerbank.write_off_reason && selectedPowerbank.write_off_reason !== 'none'" class="detail-row" :class="{ 'editable-field': isEditing }">
                  <span class="detail-label">Причина списания:</span>
                  <span v-if="!isEditing" class="detail-value">{{ getWriteOffReasonText(selectedPowerbank.write_off_reason) }}</span>
                  <select v-else v-model="editForm.write_off_reason" class="edit-input">
                    <option value="none">Нет</option>
                    <option value="broken">Сломан</option>
                    <option value="lost">Потерян</option>
                    <option value="other">Другое</option>
                  </select>
                </div>
              </div>
            </div>

            <!-- Дополнительная информация -->
            <div class="detail-section">
              <h4>Дополнительная информация</h4>
              <div class="detail-rows">
                <div class="detail-row" v-if="selectedPowerbank.created_at">
                  <span class="detail-label">Дата создания:</span>
                  <span class="detail-value">{{ formatTime(selectedPowerbank.created_at) }}</span>
                </div>
                <div class="detail-row" v-if="selectedPowerbank.updated_at">
                  <span class="detail-label">Последнее обновление:</span>
                  <span class="detail-value">{{ formatTime(selectedPowerbank.updated_at) }}</span>
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
            <button @click="toggleEditMode" class="btn-action">
              ✏️ Редактировать
            </button>
            <button 
              v-if="selectedPowerbank.status === 'system_error'" 
              @click="resetError" 
              class="btn-action btn-reset"
            >
              🔄 Сбросить ошибку
            </button>
            <button @click="showDeleteConfirmation" class="btn-action btn-delete">
              🗑️ Удалить
            </button>
          </div>
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
              <h4>Вы уверены, что хотите удалить аккумулятор?</h4>
              <p><strong>ID:</strong> {{ selectedPowerbank?.id }}</p>
              <p><strong>Серийный номер:</strong> {{ selectedPowerbank?.serial_number || 'N/A' }}</p>
              <div class="warning-text">
                <p>⚠️ Это действие нельзя отменить!</p>
                <p>Все данные об аккумуляторе будут безвозвратно удалены.</p>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="closeDeleteModal" class="btn-action btn-cancel">
            ❌ Отменить
          </button>
          <button 
            @click="confirmDeletePowerbank" 
            class="btn-action btn-delete-confirm"
            :disabled="isDeleting"
          >
            <span v-if="isDeleting" class="spinner-small"></span>
            🗑️ Удалить аккумулятор
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useAdminStore } from '../../stores/admin'
import FilterButton from './FilterButton.vue'
import { pythonAPI } from '../../api/pythonApi'

const props = defineProps({
  powerbanks: {
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
  'powerbank-clicked',
  'powerbank-updated',
  'powerbank-deleted'
])

const adminStore = useAdminStore()

// Состояние компонента
const searchQuery = ref('')
const currentPage = ref(1)
const selectedPowerbank = ref(null)
const isModalOpen = ref(false)
const activeFilters = ref({
  orgUnits: [],
  statuses: [],
  roles: []
})

// Состояние редактирования
const isEditing = ref(false)
const editForm = ref({
  serial_number: '',
  org_unit_id: '',
  status: '',
  write_off_reason: 'none'
})

// Состояние удаления
const isDeleteModalOpen = ref(false)
const isDeleting = ref(false)

// Загружаем данные при монтировании
onMounted(async () => {
  await loadData()
})

// Загружаем аккумуляторы и группы
const loadData = async () => {
  try {
    await Promise.all([
      adminStore.fetchPowerbanks(),
      adminStore.fetchOrgUnits()
    ])
  } catch (error) {
    console.error('Ошибка загрузки данных:', error)
  }
}

// Получаем аккумуляторы из store
const allPowerbanks = computed(() => {
  return adminStore.powerbanks || []
})

// Вычисляемые свойства
const filteredPowerbanks = computed(() => {
  let filtered = [...allPowerbanks.value]
  
  // Фильтрация по группам/подгруппам
  if (activeFilters.value.orgUnits.length > 0) {
    filtered = filtered.filter(powerbank => {
      return activeFilters.value.orgUnits.includes(powerbank.org_unit_id)
    })
  }
  
  // Фильтрация по статусу
  if (activeFilters.value.statuses.length > 0) {
    filtered = filtered.filter(powerbank => {
      return activeFilters.value.statuses.includes(powerbank.status)
    })
  }
  
  // Фильтрация по поисковому запросу
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(powerbank => {
      const serialNumber = (powerbank.serial_number || '').toLowerCase()
      const id = (powerbank.id || '').toString().toLowerCase()
      const errorType = (powerbank.error_type || '').toLowerCase()
      
      return serialNumber.includes(query) || 
             id.includes(query) ||
             errorType.includes(query)
    })
  }
  
  return filtered
})

const totalPages = computed(() => {
  return Math.ceil(filteredPowerbanks.value.length / props.itemsPerPage)
})

const paginatedPowerbanks = computed(() => {
  const start = (currentPage.value - 1) * props.itemsPerPage
  const end = start + props.itemsPerPage
  return filteredPowerbanks.value.slice(start, end)
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

// Статистика
const activeCount = computed(() => 
  filteredPowerbanks.value.filter(p => p.status === 'active').length
)
const brokenCount = computed(() => 
  filteredPowerbanks.value.filter(p => p.status === 'user_reported_broken' || p.status === 'system_error').length
)
const writtenOffCount = computed(() => 
  filteredPowerbanks.value.filter(p => p.status === 'written_off').length
)

// Методы
const handleFilterChange = (filters) => {
  activeFilters.value = filters
  currentPage.value = 1
}

const openPowerbankModal = (powerbank) => {
  selectedPowerbank.value = powerbank
  isModalOpen.value = true
  isEditing.value = false
  emit('powerbank-clicked', powerbank)
  
  // Инициализируем форму редактирования
  initEditForm(powerbank)
}

const closePowerbankModal = () => {
  isModalOpen.value = false
  selectedPowerbank.value = null
  isEditing.value = false
  editForm.value = {
    serial_number: '',
    org_unit_id: '',
    status: '',
    write_off_reason: 'none'
  }
}

const initEditForm = (powerbank) => {
  editForm.value = {
    serial_number: powerbank.serial_number || '',
    org_unit_id: powerbank.org_unit_id || '',
    status: powerbank.status || 'active',
    write_off_reason: powerbank.write_off_reason || 'none'
  }
}

const toggleEditMode = () => {
  if (!isEditing.value) {
    initEditForm(selectedPowerbank.value)
  }
  isEditing.value = !isEditing.value
}

const cancelEdit = () => {
  isEditing.value = false
  initEditForm(selectedPowerbank.value)
}

const saveChanges = async () => {
  if (!selectedPowerbank.value) return
  
  try {
    await adminStore.updatePowerbank(selectedPowerbank.value.id, {
      serial_number: editForm.value.serial_number,
      org_unit_id: editForm.value.org_unit_id || null,
      status: editForm.value.status,
      write_off_reason: editForm.value.write_off_reason
    })
    
    // Обновляем локальные данные
    Object.assign(selectedPowerbank.value, editForm.value)
    
    isEditing.value = false
    alert('Изменения сохранены успешно')
    
    emit('powerbank-updated', selectedPowerbank.value)
  } catch (error) {
    console.error('Ошибка сохранения изменений:', error)
    alert('Ошибка сохранения: ' + error.message)
  }
}

const resetError = async () => {
  if (!selectedPowerbank.value) return
  
  try {
    await pythonAPI.resetPowerbankError(selectedPowerbank.value.id)
    
    // Обновляем данные
    await adminStore.fetchPowerbanks()
    closePowerbankModal()
    alert('Ошибка успешно сброшена')
  } catch (error) {
    console.error('Ошибка сброса ошибки:', error)
    alert('Ошибка сброса: ' + error.message)
  }
}

const showDeleteConfirmation = () => {
  isDeleteModalOpen.value = true
}

const closeDeleteModal = () => {
  isDeleteModalOpen.value = false
}

const confirmDeletePowerbank = async () => {
  if (!selectedPowerbank.value) return
  
  isDeleting.value = true
  
  try {
    await adminStore.deletePowerbank(selectedPowerbank.value.id)
    
    alert('Аккумулятор успешно удален')
    closeDeleteModal()
    closePowerbankModal()
    
    emit('powerbank-deleted', selectedPowerbank.value.id)
  } catch (error) {
    console.error('Ошибка удаления аккумулятора:', error)
    alert('Ошибка удаления: ' + (error.message || 'Неизвестная ошибка'))
  } finally {
    isDeleting.value = false
  }
}

const getPowerbankRowClass = (status) => {
  return `status-${status}`
}

const getOrgUnitName = (orgUnitId) => {
  if (!orgUnitId) return null
  const unit = props.orgUnits.find(u => u.org_unit_id === orgUnitId)
  return unit?.name || null
}

const getStatusText = (status) => {
  const statusMap = {
    'active': 'Активный',
    'user_reported_broken': 'Сломан',
    'system_error': 'Ошибка системы',
    'written_off': 'Списан'
  }
  return statusMap[status] || status
}

const getWriteOffReasonText = (reason) => {
  const reasonMap = {
    'none': 'Нет',
    'broken': 'Сломан',
    'lost': 'Потерян',
    'other': 'Другое'
  }
  return reasonMap[reason] || reason
}

const getSohClass = (soh) => {
  if (soh >= 80) return 'soh-good'
  if (soh >= 50) return 'soh-medium'
  return 'soh-low'
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

// Сброс страницы при изменении поиска
watch(searchQuery, () => {
  currentPage.value = 1
})
</script>

<style scoped>
.powerbanks-table-container {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: calc(100vh - 120px);
  max-height: 900px;
}

.powerbanks-table-header {
  padding: 20px 24px;
  border-bottom: 1px solid #e9ecef;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f8f9fa;
  flex-shrink: 0;
}

.powerbanks-table-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.powerbanks-table-title h2 {
  margin: 0;
  color: #333;
  font-size: 1.5rem;
  font-weight: 700;
}

.powerbanks-table-actions {
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
  width: 350px;
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

.stats-bar {
  display: flex;
  gap: 20px;
  padding: 15px 24px;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
  flex-wrap: wrap;
  flex-shrink: 0;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
}

.stat-label {
  font-size: 12px;
  color: #666;
  font-weight: 500;
}

.stat-value {
  font-size: 18px;
  font-weight: bold;
  color: #333;
}

.table-wrapper {
  flex: 1;
  overflow: auto;
  min-height: 0;
  position: relative;
}

.powerbanks-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
  table-layout: auto;
}

.powerbanks-table th {
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

.powerbanks-table td {
  padding: 16px 12px;
  border-bottom: 1px solid #e9ecef;
  vertical-align: middle;
  color: #333;
}

.powerbank-row {
  transition: background-color 0.2s ease;
  cursor: pointer;
}

.powerbank-row:hover {
  background: #f8f9fa;
}

.powerbank-row.status-active {
  border-left: 4px solid #28a745;
}

.powerbank-row.status-user_reported_broken,
.powerbank-row.status-system_error {
  border-left: 4px solid #dc3545;
}

.powerbank-row.status-written_off {
  border-left: 4px solid #6c757d;
}

/* Колонки */
.col-id {
  width: 8%;
  min-width: 80px;
}

.col-serial {
  width: 20%;
  min-width: 150px;
}

.col-org-unit {
  width: 20%;
  min-width: 150px;
}

.col-soh {
  width: 15%;
  min-width: 120px;
}

.col-status {
  width: 15%;
  min-width: 120px;
}

.col-error {
  width: 15%;
  min-width: 120px;
}

.col-created {
  width: 12%;
  min-width: 120px;
}

/* Содержимое ячеек */
.id-text {
  font-weight: 600;
  color: #333;
  font-family: 'Courier New', monospace;
}

.serial-text {
  font-weight: 500;
  color: #333;
  font-family: 'Courier New', monospace;
}

.org-unit-text {
  font-size: 0.9rem;
  color: #333;
}

.soh-container {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.soh-text {
  font-size: 0.9rem;
  font-weight: 500;
  color: #333;
}

.soh-bar {
  width: 100%;
  height: 6px;
  background: #e9ecef;
  border-radius: 3px;
  overflow: hidden;
}

.soh-progress {
  height: 100%;
  transition: width 0.3s ease;
}

.soh-progress.soh-good {
  background: #28a745;
}

.soh-progress.soh-medium {
  background: #ffc107;
}

.soh-progress.soh-low {
  background: #dc3545;
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

.status-indicator.status-user_reported_broken,
.status-indicator.status-system_error {
  background: #dc3545;
  box-shadow: 0 0 8px rgba(220, 53, 69, 0.5);
}

.status-indicator.status-written_off {
  background: #6c757d;
  box-shadow: 0 0 8px rgba(108, 117, 125, 0.5);
}

.status-text {
  font-size: 0.9rem;
  font-weight: 500;
  color: #333;
}

.error-text {
  font-size: 0.85rem;
  color: #dc3545;
  font-weight: 500;
}

.no-error {
  color: #999;
  font-size: 0.9rem;
}

.date-text {
  font-size: 0.9rem;
  color: #666;
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
  animation: modalSlideIn 0.3s ease-out;
  display: flex;
  flex-direction: column;
  overflow: hidden;
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
  flex-shrink: 0;
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

.powerbank-details {
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

.btn-reset {
  background: #ffc107;
  color: #333;
}

.btn-reset:hover {
  background: #e0a800;
}

.btn-delete {
  background: linear-gradient(135deg, #ff6b6b, #ee5a52);
}

.btn-delete:hover {
  background: linear-gradient(135deg, #ff5252, #e53e3e);
}

.edit-actions {
  display: flex;
  gap: 8px;
  justify-content: center;
  width: 100%;
}

.view-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  flex-wrap: wrap;
}

/* Модальное окно удаления */
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

.spinner-small {
  width: 16px;
  height: 16px;
  border: 2px solid #e9ecef;
  border-top: 2px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  display: inline-block;
  margin-right: 8px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Мобильные стили */
@media (max-width: 768px) {
  .powerbanks-table-header {
    flex-direction: column;
    gap: 16px;
    align-items: stretch;
  }

  .powerbanks-table-actions {
    flex-direction: column;
    gap: 12px;
  }

  .search-input {
    width: 100%;
  }

  .stats-bar {
    flex-direction: column;
    gap: 10px;
  }

  .pagination {
    flex-direction: column;
    gap: 16px;
  }

  .pagination-pages {
    order: -1;
  }

  .powerbanks-table {
    font-size: 0.9rem;
  }

  .powerbanks-table th,
  .powerbanks-table td {
    padding: 12px 8px;
  }

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

  .modal-footer {
    padding: 16px 20px;
    flex-wrap: wrap;
  }

  .btn-action {
    flex: 1;
    min-width: 100px;
  }
}
</style>

