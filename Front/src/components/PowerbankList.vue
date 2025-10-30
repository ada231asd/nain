<template>
  <div class="powerbank-list">
    <div class="list-header">
      <h2>Аккумуляторы</h2>
      <div class="header-actions">
        <div class="search-box">
          <input 
            v-model="searchQuery" 
            type="text" 
            placeholder="Поиск по серийному номеру..." 
            class="search-input"
          />
        </div>
        <div class="filters">
          <select v-model="statusFilter" class="filter-select">
            <option value="">Все статусы</option>
            <option value="active">Активные</option>
            <option value="user_reported_broken">Сломанные</option>
            <option value="system_error">Ошибка системы</option>
            <option value="written_off">Списанные</option>
          </select>
          <select v-model="orgUnitFilter" class="filter-select">
            <option value="">Все группы</option>
            <template v-for="group in groups" :key="group.org_unit_id">
              <optgroup :label="group.name">
                <option :value="group.org_unit_id">{{ group.name }}</option>
                <option 
                  v-for="subgroup in getSubgroupsForGroup(group.org_unit_id)" 
                  :key="subgroup.org_unit_id" 
                  :value="subgroup.org_unit_id"
                >
                  &nbsp;&nbsp;{{ subgroup.name }}
                </option>
              </optgroup>
            </template>
            <!-- Отладочная информация -->
            <option v-if="groups.length === 0" disabled>Нет доступных групп</option>
          </select>
        </div>
      </div>
    </div>

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

    <div v-if="isLoading" class="loading">
      Загрузка аккумуляторов...
    </div>

    <div v-else-if="filteredPowerbanks.length === 0" class="empty-state">
      <p>Аккумуляторы не найдены</p>
    </div>

    <div v-else class="powerbank-grid">
      <div 
        v-for="powerbank in filteredPowerbanks" 
        :key="powerbank.id" 
        class="powerbank-card"
        :class="getPowerbankCardClass(powerbank.status)"
      >
        <div class="card-header">
          <div class="powerbank-id">
            <span class="id-label">ID:</span>
            <span class="id-value">{{ powerbank.id }}</span>
          </div>
          <div class="card-actions">
            <button 
              @click="editPowerbank(powerbank)" 
              class="btn-action btn-edit" 
              title="Редактировать"
            >
              ✏️
            </button>
            <button 
              @click="deletePowerbank(powerbank)" 
              class="btn-action btn-delete" 
              title="Удалить"
            >
              🗑️
            </button>
          </div>
        </div>
        
        <div class="card-content">
          <div class="powerbank-info">
            <div class="info-row">
              <span class="info-label">Серийный номер:</span>
              <span class="info-value">{{ powerbank.serial_number || '-' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Группа:</span>
              <span class="info-value">{{ getOrgUnitName(powerbank.org_unit_id) || 'Не назначена' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">SOH:</span>
              <span class="info-value">{{ powerbank.soh || 0 }}%</span>
            </div>
            <div class="info-row">
              <span class="info-label">Статус:</span>
              <span class="status-badge" :class="getStatusClass(powerbank.status)">
                {{ getStatusText(powerbank.status) }}
              </span>
            </div>
            <div v-if="powerbank.write_off_reason && powerbank.write_off_reason !== 'none'" class="info-row">
              <span class="info-label">Причина списания:</span>
              <span class="info-value">{{ getWriteOffReasonText(powerbank.write_off_reason) }}</span>
            </div>
            <div v-if="powerbank.status === 'system_error' && powerbank.error_type" class="info-row">
              <span class="info-label">Ошибка системы:</span>
              <span class="info-value error-text">{{ powerbank.error_type }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Создан:</span>
              <span class="info-value">{{ formatDate(powerbank.created_at) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Модальное окно редактирования -->
    <EditPowerbankModal
      :is-visible="showEditModal"
      :powerbank="selectedPowerbank"
      @close="closeEditModal"
      @saved="handlePowerbankSaved"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useAdminStore } from '../stores/admin'
import EditPowerbankModal from './EditPowerbankModal.vue'
import { showConfirm } from '../utils/notifications'

const adminStore = useAdminStore()

const isLoading = ref(false)
const searchQuery = ref('')
const statusFilter = ref('')
const orgUnitFilter = ref('')
const showEditModal = ref(false)
const selectedPowerbank = ref(null)

// Получаем группы и подгруппы
const groups = computed(() => {
  return adminStore.groups
})
const subgroups = computed(() => {
  return adminStore.subgroups
})

// Функция для получения подгрупп для конкретной группы
const getSubgroupsForGroup = (groupId) => {
  const result = subgroups.value.filter(sub => sub.parent_org_unit_id === groupId)
  return result
}

// Фильтрованные аккумуляторы
const filteredPowerbanks = computed(() => {
  let filtered = adminStore.powerbanks

  // Фильтр по поиску
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(p => 
      p.serial_number?.toLowerCase().includes(query)
    )
  }

  // Фильтр по статусу
  if (statusFilter.value) {
    filtered = filtered.filter(p => p.status === statusFilter.value)
  }

  // Фильтр по группе
  if (orgUnitFilter.value) {
    filtered = filtered.filter(p => p.org_unit_id == orgUnitFilter.value)
  }

  return filtered
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

// Загружаем данные при монтировании
onMounted(async () => {
  await loadData()
})

// Загружаем аккумуляторы и группы
const loadData = async () => {
  isLoading.value = true
  try {
    await Promise.all([
      adminStore.fetchPowerbanks(),
      adminStore.fetchOrgUnits()
    ])
  } catch (error) {
    // Ошибка загрузки данных
  } finally {
    isLoading.value = false
  }
}

// Получение имени группы по ID
const getOrgUnitName = (orgUnitId) => {
  if (!orgUnitId) return null
  const allUnits = [...groups.value, ...subgroups.value]
  const unit = allUnits.find(u => u.org_unit_id == orgUnitId)
  return unit?.name || null
}

// Классы для карточек
const getPowerbankCardClass = (status) => {
  return `status-${status}`
}

// Классы для статусов
const getStatusClass = (status) => {
  return `status-${status}`
}

// Тексты статусов
const getStatusText = (status) => {
  const statusMap = {
    'active': 'Активный',
    'user_reported_broken': 'Сломан',
    'system_error': 'Ошибка системы',
    'written_off': 'Списан'
  }
  return statusMap[status] || status
}

// Тексты причин списания
const getWriteOffReasonText = (reason) => {
  const reasonMap = {
    'none': 'Нет',
    'broken': 'Сломан',
    'lost': 'Потерян',
    'other': 'Другое'
  }
  return reasonMap[reason] || reason
}

// Форматирование даты
const formatDate = (dateString) => {
  if (!dateString) return '-'
  try {
    return new Date(dateString).toLocaleDateString('ru-RU')
  } catch {
    return '-'
  }
}

// Редактирование аккумулятора
const editPowerbank = (powerbank) => {
  selectedPowerbank.value = powerbank
  showEditModal.value = true
}

const closeEditModal = () => {
  showEditModal.value = false
  selectedPowerbank.value = null
}

const handlePowerbankSaved = () => {
  // Данные уже обновлены в store
}

// Удаление аккумулятора
const deletePowerbank = async (powerbank) => {
  if (!await showConfirm(`Вы уверены, что хотите удалить аккумулятор ${powerbank.serial_number}?`)) {
    return
  }

  try {
    await adminStore.deletePowerbank(powerbank.id)
  } catch (error) {
    // Ошибка удаления аккумулятора
  }
}
</script>

<style scoped>
.powerbank-list {
  padding: 20px;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 15px;
}

.list-header h2 {
  margin: 0;
  color: #333;
  font-size: 1.8rem;
}

.header-actions {
  display: flex;
  gap: 15px;
  align-items: center;
  flex-wrap: wrap;
}

.search-box {
  position: relative;
}

.search-input {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  width: 250px;
  font-size: 14px;
}

.search-input:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
}

.filters {
  display: flex;
  gap: 10px;
}

.filter-select {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  background: white;
}

.stats-bar {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
  padding: 15px;
  background: #f8f9fa;
  border-radius: 8px;
  flex-wrap: wrap;
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

.loading {
  text-align: center;
  padding: 40px;
  color: #666;
  font-size: 16px;
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: #666;
}

.empty-state p {
  margin: 0;
  font-size: 16px;
}

.powerbank-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 20px;
}

.powerbank-card {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.2s;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.powerbank-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

.powerbank-card.status-active {
  border-left: 4px solid #28a745;
}

.powerbank-card.status-user_reported_broken,
.powerbank-card.status-system_error {
  border-left: 4px solid #dc3545;
}

.powerbank-card.status-written_off {
  border-left: 4px solid #6c757d;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  background: #f8f9fa;
  border-bottom: 1px solid #e0e0e0;
}

.powerbank-id {
  display: flex;
  align-items: center;
  gap: 5px;
}

.id-label {
  font-size: 12px;
  color: #666;
  font-weight: 500;
}

.id-value {
  font-weight: bold;
  color: #333;
}

.card-actions {
  display: flex;
  gap: 5px;
}

.btn-action {
  background: none;
  border: none;
  padding: 5px;
  cursor: pointer;
  border-radius: 4px;
  font-size: 16px;
  transition: background-color 0.2s;
}

.btn-edit:hover {
  background-color: #e3f2fd;
}

.btn-delete:hover {
  background-color: #ffebee;
}

.card-content {
  padding: 15px;
}

.powerbank-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.info-label {
  font-size: 12px;
  color: #666;
  font-weight: 500;
}

.info-value {
  font-size: 14px;
  color: #333;
  font-weight: 500;
}

.status-badge {
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  text-transform: uppercase;
}

.status-badge.status-active {
  background-color: #d4edda;
  color: #155724;
}

.error-text {
  color: #dc3545;
  font-weight: 500;
}

.status-badge.status-user_reported_broken,
.status-badge.status-system_error {
  background-color: #f8d7da;
  color: #721c24;
}

.status-badge.status-written_off {
  background-color: #d1ecf1;
  color: #0c5460;
}

@media (max-width: 768px) {
  .list-header {
    flex-direction: column;
    align-items: stretch;
  }
  
  .header-actions {
    flex-direction: column;
    align-items: stretch;
  }
  
  .search-input {
    width: 100%;
  }
  
  .filters {
    flex-direction: column;
  }
  
  .powerbank-grid {
    grid-template-columns: 1fr;
  }
  
  .stats-bar {
    flex-direction: column;
    gap: 10px;
  }
}
</style>
