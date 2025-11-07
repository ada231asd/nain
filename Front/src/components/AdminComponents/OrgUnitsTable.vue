<template>
  <div class="org-units-table-container">
    <!-- Заголовок с поиском и действиями -->
    <div class="org-units-table-header">
      <div class="org-units-table-title">
        <h2>Группы</h2>
      </div>
      <div class="org-units-table-actions">
        <div class="search-container">
          <input 
            type="text" 
            v-model="searchQuery" 
            placeholder="Поиск по названию, типу, адресу..." 
            class="search-input"
          />
          <span class="search-icon">🔍</span>
        </div>
        
        <button @click="$emit('add-org-unit')" class="btn-add-org-unit">
          + Добавить группу
        </button>

        <RefreshButton @refresh="handleRefresh" />

        <FilterButton 
          filter-type="org-units"
          :org-units="orgUnits"
          :show-org-unit-filter="false"
          :show-status-filter="true"
          :show-role-filter="false"
          @filter-change="handleFilterChange"
        />

      </div>
    </div>

    <!-- Таблица групп -->
    <div class="table-wrapper">
      <!-- Индикатор загрузки -->
      <div v-if="isLoading" class="table-loading-overlay">
        <div class="table-loading-spinner"></div>
      </div>
      <table class="org-units-table">
        <thead>
          <tr>
            <th class="col-logo">Лого</th>
            <th class="col-name">Название</th>
            <th class="col-type">Тип</th>
            <th class="col-parent">Родительская группа</th>
            <th class="col-address">Адрес</th>
            <th class="col-limit">Лимит</th>
            <th class="col-reminder">Напоминание</th>
            <th class="col-writeoff">Списание</th>
            <th class="col-actions">Операции</th>
          </tr>
        </thead>
        <tbody>
          <tr 
            v-for="orgUnit in paginatedOrgUnits" 
            :key="orgUnit.org_unit_id"
            class="org-unit-row"
            :class="getOrgUnitRowClass(orgUnit.unit_type)"
            @click="openOrgUnitModal(orgUnit)"
          >
            <!-- Лого -->
            <td class="col-logo">
              <div class="logo-container">
                <img 
                  v-if="orgUnit.logo_url" 
                  :src="orgUnit.logo_url" 
                  :alt="orgUnit.name"
                  class="org-unit-logo"
                  @error="handleLogoError"
                />
                <div v-else class="org-unit-logo-placeholder">
                  <span class="logo-placeholder-text">{{ getLogoPlaceholder(orgUnit) }}</span>
                </div>
              </div>
            </td>

            <!-- Название -->
            <td class="col-name">
              <div class="org-unit-name-info">
                <span class="org-unit-name-text" :title="orgUnit.name">{{ truncateText(orgUnit.name, 25) }}</span>
                <span v-if="orgUnit.description" class="org-unit-description">{{ truncateText(orgUnit.description, 30) }}</span>
              </div>
            </td>

            <!-- Тип -->
            <td class="col-type">
              <span class="type-badge" :class="getUnitTypeClass(orgUnit.unit_type)">
                {{ getUnitTypeText(orgUnit.unit_type) }}
              </span>
            </td>

            <!-- Родительская группа -->
            <td class="col-parent">
              <span class="parent-text">{{ orgUnit.parent_name || '—' }}</span>
            </td>

            <!-- Адрес -->
            <td class="col-address">
              <span class="address-text" :title="orgUnit.adress || orgUnit.address">
                {{ truncateText(orgUnit.adress || orgUnit.address || '—', 35) }}
              </span>
            </td>

            <!-- Лимит -->
            <td class="col-limit">
              <span class="limit-badge" v-if="orgUnit.default_powerbank_limit">
                🔋 {{ orgUnit.default_powerbank_limit }}
              </span>
              <span v-else class="no-limit">—</span>
            </td>

            <!-- Напоминание -->
            <td class="col-reminder">
              <span class="reminder-badge" v-if="orgUnit.reminder_hours">
                ⏰ {{ orgUnit.reminder_hours }}ч
              </span>
              <span v-else class="no-reminder">—</span>
            </td>

            <!-- Списание -->
            <td class="col-writeoff">
              <span class="writeoff-badge" v-if="orgUnit.write_off_hours">
                📋 {{ orgUnit.write_off_hours }}ч
              </span>
              <span v-else class="no-writeoff">—</span>
            </td>

            <!-- Операции -->
            <td class="col-actions" @click.stop>
              <div class="actions-container">
                <!-- Показываем кнопку восстановления для удалённых -->
                <button 
                  v-if="showDeletedOrgUnits"
                  @click="handleRestore(orgUnit)"
                  class="btn-action btn-restore"
                  title="Восстановить группу"
                >
                  ↺
                </button>
                <!-- Показываем кнопку удаления -->
                <button 
                  @click="handleDelete(orgUnit)"
                  class="btn-action btn-delete-action"
                  :class="{ 'btn-hard-delete': showDeletedOrgUnits }"
                  :title="showDeletedOrgUnits ? 'Удалить навсегда' : 'Удалить группу'"
                >
                  {{ showDeletedOrgUnits ? '✕' : '🗑' }}
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
    <div v-if="filteredOrgUnits.length === 0" class="empty-state">
      <div class="empty-icon">🏢</div>
      <h3>Группы не найдены</h3>
      <p v-if="searchQuery">Попробуйте изменить поисковый запрос</p>
      <p v-else>Добавьте первую группу</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { pythonAPI } from '../../api/pythonApi'
import { useAdminStore } from '../../stores/admin'
import FilterButton from './FilterButton.vue'
import RefreshButton from '../RefreshButton.vue'

const props = defineProps({
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
  'add-org-unit',
  'edit',
  'delete',
  'restore',
  'view-stations',
  'view-details',
  'org-unit-clicked',
  'org-unit-deleted',
  'org-unit-restored',
  'refresh'
])

const adminStore = useAdminStore()

// Состояние компонента
const searchQuery = ref('')
const currentPage = ref(1)
const isLoading = ref(false)
const activeFilters = ref({
  orgUnits: [],
  statuses: [],
  roles: []
})
// selectedOrgUnit и isModalOpen удалены - используется OrgUnitDetailsModal из AdminPanel

// Проверка, показываем ли удалённые группы
const showDeletedOrgUnits = computed(() => {
  return activeFilters.value.statuses.includes('deleted')
})

// Методы
const handleFilterChange = (filters) => {
  activeFilters.value = filters
  currentPage.value = 1
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

// Вычисляемые свойства
const filteredOrgUnits = computed(() => {
  let filtered = [...props.orgUnits]
  
  // ФИЛЬТРАЦИЯ ПО УДАЛЁННЫМ/НЕУДАЛЁННЫМ ГРУППАМ
  if (showDeletedOrgUnits.value) {
    // Показываем только удалённые группы (is_deleted = 1)
    filtered = filtered.filter(orgUnit => orgUnit.is_deleted === 1 || orgUnit.is_deleted === true)
  } else {
    // По умолчанию показываем только НЕ удалённые группы (is_deleted = 0 или null)
    filtered = filtered.filter(orgUnit => !orgUnit.is_deleted || orgUnit.is_deleted === 0)
  }
  
  // Фильтрация по типу (group/subgroup) кроме 'deleted'
  if (activeFilters.value.statuses.length > 0) {
    // Исключаем фильтр 'deleted' из обычной фильтрации
    const statusesWithoutDeleted = activeFilters.value.statuses.filter(s => s !== 'deleted')
    
    if (statusesWithoutDeleted.length > 0) {
      filtered = filtered.filter(orgUnit => {
        return statusesWithoutDeleted.includes(orgUnit.unit_type)
      })
    }
  }
  
  // Фильтрация по поисковому запросу
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(orgUnit => {
      const name = (orgUnit.name || '').toLowerCase()
      const description = (orgUnit.description || '').toLowerCase()
      const unitType = (orgUnit.unit_type || '').toLowerCase()
      const parentName = (orgUnit.parent_name || '').toLowerCase()
      const address = (orgUnit.adress || orgUnit.address || '').toLowerCase()
      
      return name.includes(query) || 
             description.includes(query) || 
             unitType.includes(query) ||
             parentName.includes(query) ||
             address.includes(query)
    })
  }
  
  return filtered
})

const totalPages = computed(() => {
  return Math.ceil(filteredOrgUnits.value.length / props.itemsPerPage)
})

const paginatedOrgUnits = computed(() => {
  const start = (currentPage.value - 1) * props.itemsPerPage
  const end = start + props.itemsPerPage
  return filteredOrgUnits.value.slice(start, end)
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

// Удаление группы (мягкое или жёсткое в зависимости от фильтра)
const handleDelete = async (orgUnit) => {
  const orgUnitId = orgUnit.org_unit_id
  
  // Просто эмитим событие с флагом типа удаления
  // Сам запрос на удаление будет делаться в AdminPanel
  emit('delete', { orgUnitId, hardDelete: showDeletedOrgUnits.value, orgUnitName: orgUnit.name })
}

// Восстановление удалённой группы
const handleRestore = async (orgUnit) => {
  const orgUnitId = orgUnit.org_unit_id
  
  // Просто эмитим событие, запрос будет делаться в AdminPanel
  emit('restore', { orgUnitId, orgUnitName: orgUnit.name })
}

// Открытие модального окна
const openOrgUnitModal = (orgUnit) => {
  // Просто эмитим событие - модальное окно откроется в AdminPanel
  emit('org-unit-clicked', orgUnit)
  emit('view-details', orgUnit)
}

const getOrgUnitRowClass = (unitType) => {
  return `type-${unitType}`
}

const getUnitTypeText = (unitType) => {
  switch (unitType) {
    case 'group':
      return 'Группа'
    case 'subgroup':
      return 'Подгруппа'
    default:
      return unitType || 'Неизвестно'
  }
}

const getUnitTypeClass = (unitType) => {
  return `type-${unitType}`
}

const getLogoPlaceholder = (orgUnit) => {
  if (!orgUnit.name) return '?'
  const words = orgUnit.name.split(' ').filter(w => w.length > 0)
  if (words.length === 0) return '?'
  if (words.length === 1) return words[0].substring(0, 2).toUpperCase()
  return (words[0][0] + words[1][0]).toUpperCase()
}

const handleLogoError = () => {
  // Можно добавить обработку ошибки загрузки логотипа
}

const truncateText = (text, maxLength) => {
  if (!text || text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
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
.org-units-table-container {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: calc(100vh - 120px);
  max-height: 900px;
}

.org-units-table-header {
  padding: 20px 24px;
  border-bottom: 1px solid #e9ecef;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f8f9fa;
  flex-shrink: 0;
}

.org-units-table-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.org-units-table-title h2 {
  margin: 0;
  color: #333;
  font-size: 1.5rem;
  font-weight: 700;
}

.org-units-table-actions {
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

.btn-add-org-unit {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: white;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  color: #333;
  transition: all 0.3s ease;
}

.btn-add-org-unit:hover {
  border-color: #667eea;
  background: #f8f9fa;
}

.table-wrapper {
  flex: 1;
  overflow: auto;
  min-height: 0;
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

.org-units-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
  table-layout: auto;
}

.org-units-table th {
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

.org-units-table td {
  padding: 16px 12px;
  border-bottom: 1px solid #e9ecef;
  vertical-align: middle;
  color: #333;
}

.org-unit-row {
  transition: background-color 0.2s ease;
  cursor: pointer;
}

.org-unit-row:hover {
  background: #f8f9fa;
}

.org-unit-row.type-group {
  border-left: 4px solid #28a745;
}

.org-unit-row.type-subgroup {
  border-left: 4px solid #ffc107;
}

/* Колонки */
.col-logo {
  width: 60px;
  min-width: 60px;
}

.col-name {
  width: 20%;
  min-width: 180px;
}

.col-type {
  width: 12%;
  min-width: 100px;
}

.col-parent {
  width: 15%;
  min-width: 120px;
}

.col-address {
  width: 25%;
  min-width: 200px;
}

.col-limit {
  width: 10%;
  min-width: 80px;
}

.col-reminder {
  width: 10%;
  min-width: 100px;
}

.col-writeoff {
  width: 10%;
  min-width: 100px;
}

.col-actions {
  width: 10%;
  min-width: 100px;
}

/* Содержимое ячеек */
.logo-container {
  display: flex;
  align-items: center;
  justify-content: center;
}

.org-unit-logo {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  object-fit: cover;
}

.org-unit-logo-placeholder {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-placeholder-text {
  font-size: 16px;
  font-weight: 700;
  color: white;
  text-transform: uppercase;
}

.org-unit-name-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.org-unit-name-text {
  font-weight: 500;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
}

.org-unit-description {
  font-size: 0.8rem;
  color: #666;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
}

.type-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.type-badge.type-group {
  color: #28a745;
}

.type-badge.type-subgroup {
  color: #fd7e14;
}

.parent-text {
  font-size: 0.9rem;
  color: #333;
}

.address-text {
  font-size: 0.9rem;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
}

.limit-badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 6px;
  background: #e7f3ff;
  color: #0066cc;
  font-size: 0.85rem;
  font-weight: 500;
}

.reminder-badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 6px;
  background: #fff3cd;
  color: #856404;
  font-size: 0.85rem;
  font-weight: 500;
}

.writeoff-badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 6px;
  background: #f8d7da;
  color: #721c24;
  font-size: 0.85rem;
  font-weight: 500;
}

.no-limit,
.no-reminder,
.no-writeoff {
  color: #999;
  font-size: 0.9rem;
}

/* Кнопки действий */
.actions-container {
  display: flex;
  gap: 6px;
  justify-content: center;
  align-items: center;
}

.btn-action {
  padding: 6px 10px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 600;
  transition: all 0.3s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 32px;
  height: 32px;
}

.btn-delete-action {
  background: #ffc107;
  color: #856404;
}

.btn-delete-action:hover {
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

.org-unit-details {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.logo-section {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 30px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-left: none;
}

.org-unit-logo-large-container {
  width: 120px;
  height: 120px;
  border-radius: 16px;
  overflow: hidden;
  background: white;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
}

.org-unit-logo-large {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.org-unit-logo-placeholder-large {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-placeholder-text-large {
  font-size: 48px;
  font-weight: 700;
  color: white;
  text-transform: uppercase;
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

.btn-delete {
  background: linear-gradient(135deg, #ff6b6b, #ee5a52);
}

.btn-delete:hover {
  background: linear-gradient(135deg, #ff5252, #e53e3e);
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

/* Мобильные стили */
@media (max-width: 768px) {
  .org-units-table-header {
    flex-direction: column;
    gap: 16px;
    align-items: stretch;
  }

  .org-units-table-actions {
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

  .org-units-table {
    font-size: 0.9rem;
  }

  .org-units-table th,
  .org-units-table td {
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

  .btn-action,
  .btn-close {
    flex: 1;
    min-width: 100px;
  }
}
</style>

