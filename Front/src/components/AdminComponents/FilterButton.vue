<template>
  <div class="filter-container">
    <button ref="filterButtonRef" @click="toggleFilterPanel" class="filter-button" :class="{ active: isOpen || hasActiveFilters }">
      <span class="filter-icon">🔽</span>
      <span class="filter-text">Фильтры</span>
      <span v-if="activeFilterCount > 0" class="filter-badge">{{ activeFilterCount }}</span>
    </button>

    <!-- Панель фильтров -->
    <transition name="slide-fade">
      <div v-if="isOpen" ref="filterPanelRef" class="filter-panel" :style="{ top: panelPosition.top, right: panelPosition.right, left: panelPosition.left }">
        <div class="filter-panel-header">
          <h4>Фильтры</h4>
          <button @click="clearAllFilters" class="btn-clear-all">
            Сбросить все
          </button>
        </div>

        <div class="filter-panel-body">
          <!-- Фильтр по группам/подгруппам -->
          <div v-if="showOrgUnitFilter" class="filter-group">
            <label class="filter-label">Группа / Подгруппа</label>
            <div class="filter-options">
              <button 
                @click="toggleOrgUnit(null)"
                :class="['filter-chip', { active: selectedOrgUnits.length === 0 }]"
              >
                Все
              </button>
              <button 
                v-for="orgUnit in orgUnits" 
                :key="orgUnit.org_unit_id"
                @click="toggleOrgUnit(orgUnit.org_unit_id)"
                :class="['filter-chip', { active: selectedOrgUnits.includes(orgUnit.org_unit_id) }]"
              >
                {{ orgUnit.name }}
              </button>
            </div>
          </div>

          <!-- Фильтр по статусу -->
          <div v-if="showStatusFilter" class="filter-group">
            <label class="filter-label">Статус</label>
            <div class="filter-options">
              <button 
                @click="toggleStatus(null)"
                :class="['filter-chip', { active: selectedStatuses.length === 0 }]"
              >
                Все
              </button>
              <button 
                v-for="status in availableStatuses" 
                :key="status.value"
                @click="toggleStatus(status.value)"
                :class="['filter-chip', 'status-chip', `status-${status.class}`, { active: isStatusActive(status.value) }]"
              >
                <span class="status-dot" :class="`dot-${status.class}`"></span>
                {{ status.label }}
              </button>
            </div>
          </div>

          <!-- Фильтр по ролям (только для пользователей) -->
          <div v-if="showRoleFilter" class="filter-group">
            <label class="filter-label">Роль</label>
            <div class="filter-options">
              <button 
                @click="toggleRole(null)"
                :class="['filter-chip', { active: selectedRoles.length === 0 }]"
              >
                Все
              </button>
              <button 
                v-for="role in availableRoles" 
                :key="role.value"
                @click="toggleRole(role.value)"
                :class="['filter-chip', 'role-chip', { active: selectedRoles.includes(role.value) }]"
              >
                {{ role.label }}
              </button>
            </div>
          </div>

          <!-- Дополнительные фильтры (кастомные) -->
          <slot name="custom-filters"></slot>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  // Тип фильтра: 'users', 'stations', 'powerbanks', 'orders'
  filterType: {
    type: String,
    required: true,
    validator: (value) => ['users', 'stations', 'powerbanks', 'orders'].includes(value)
  },
  // Список организационных единиц
  orgUnits: {
    type: Array,
    default: () => []
  },
  // Показывать фильтр по группам/подгруппам
  showOrgUnitFilter: {
    type: Boolean,
    default: true
  },
  // Показывать фильтр по статусу
  showStatusFilter: {
    type: Boolean,
    default: true
  },
  // Показывать фильтр по ролям (только для пользователей)
  showRoleFilter: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['filter-change', 'filters-applied'])

// Локальное состояние
const isOpen = ref(false)
const selectedOrgUnits = ref([])
const selectedStatuses = ref([])
const selectedRoles = ref([])
const filterButtonRef = ref(null)
const filterPanelRef = ref(null)
const panelPosition = ref({ top: 0, right: 0, left: 'auto' })

// Доступные статусы в зависимости от типа
const availableStatuses = computed(() => {
  switch (props.filterType) {
    case 'users':
      return [
        { value: 'pending', label: 'Ожидание', class: 'pending', aliases: ['ожидает'] },
        { value: 'active', label: 'Активный', class: 'active', aliases: ['активный'] },
        { value: 'blocked', label: 'Заблокирован', class: 'blocked', aliases: ['заблокирован'] }
      ]
    case 'stations':
      return [
        { value: 'pending', label: 'Ожидание', class: 'pending', aliases: ['ожидает'] },
        { value: 'active', label: 'Активна', class: 'active', aliases: ['активна'] },
        { value: 'inactive', label: 'Неактивна', class: 'inactive', aliases: ['неактивна'] }
      ]
    case 'powerbanks':
      return [
        { value: 'active', label: 'Активный', class: 'active', aliases: [] },
        { value: 'user_reported_broken', label: 'Сломан', class: 'broken', aliases: [] },
        { value: 'system_error', label: 'Ошибка системы', class: 'broken', aliases: [] },
        { value: 'written_off', label: 'Списан', class: 'inactive', aliases: [] }
      ]
    case 'orders':
      return [
        { value: 'borrow', label: 'Взято', class: 'borrowed', aliases: [] },
        { value: 'return', label: 'Возвращено', class: 'return', aliases: [] },
        { value: 'deleted', label: 'Удалённые', class: 'deleted', aliases: [] }
      ]
    default:
      return []
  }
})

// Доступные роли (только для пользователей)
const availableRoles = computed(() => {
  if (props.filterType !== 'users') return []
  return [
    { value: 'service_admin', label: 'Сервис-администратор' },
    { value: 'group_admin', label: 'Администратор группы' },
    { value: 'subgroup_admin', label: 'Администратор подгруппы' },
    { value: 'user', label: 'Пользователь' }
  ]
})

// Количество активных фильтров
const activeFilterCount = computed(() => {
  return selectedOrgUnits.value.length + 
         selectedStatuses.value.length + 
         selectedRoles.value.length
})

// Есть ли активные фильтры
const hasActiveFilters = computed(() => {
  return activeFilterCount.value > 0
})

// Проверка активности статуса с учетом aliases
const isStatusActive = (status) => {
  const statusObj = availableStatuses.value.find(s => s.value === status)
  const allVariants = [status, ...(statusObj?.aliases || [])]
  return allVariants.some(variant => selectedStatuses.value.includes(variant))
}

// Методы
const updatePanelPosition = () => {
  if (!filterButtonRef.value) return
  
  const rect = filterButtonRef.value.getBoundingClientRect()
  const windowHeight = window.innerHeight
  const windowWidth = window.innerWidth
  const panelHeight = 500 // примерная высота панели
  const panelWidth = 400
  
  // Выравнивание по правому краю кнопки
  let top = rect.bottom + window.scrollY + 8
  let right = windowWidth - (rect.right + window.scrollX)
  
  // Если панель выходит за левый край экрана
  if (rect.right - panelWidth < 0) {
    right = windowWidth - (rect.left + window.scrollX) - panelWidth
  }
  
  // Проверка выхода за нижний край
  if (rect.bottom + panelHeight > windowHeight) {
    top = rect.top + window.scrollY - panelHeight - 8
  }
  
  panelPosition.value = { top: `${top}px`, right: `${right}px`, left: 'auto' }
}

const toggleFilterPanel = () => {
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    setTimeout(updatePanelPosition, 10)
  }
}

const toggleOrgUnit = (orgUnitId) => {
  if (orgUnitId === null) {
    selectedOrgUnits.value = []
  } else {
    const index = selectedOrgUnits.value.indexOf(orgUnitId)
    if (index > -1) {
      selectedOrgUnits.value.splice(index, 1)
    } else {
      selectedOrgUnits.value.push(orgUnitId)
    }
  }
}

const toggleStatus = (status) => {
  if (status === null) {
    selectedStatuses.value = []
  } else {
    // Находим статус с aliases
    const statusObj = availableStatuses.value.find(s => s.value === status)
    const allVariants = [status, ...(statusObj?.aliases || [])]
    
    // Проверяем, есть ли любой вариант в выбранных
    const hasAnyVariant = allVariants.some(variant => selectedStatuses.value.includes(variant))
    
    if (hasAnyVariant) {
      // Удаляем все варианты
      selectedStatuses.value = selectedStatuses.value.filter(s => !allVariants.includes(s))
    } else {
      // Добавляем основной статус и все aliases
      selectedStatuses.value.push(...allVariants)
    }
  }
}

const toggleRole = (role) => {
  if (role === null) {
    selectedRoles.value = []
  } else {
    const index = selectedRoles.value.indexOf(role)
    if (index > -1) {
      selectedRoles.value.splice(index, 1)
    } else {
      selectedRoles.value.push(role)
    }
  }
}

const clearAllFilters = () => {
  selectedOrgUnits.value = []
  selectedStatuses.value = []
  selectedRoles.value = []
  applyFilters()
}

const applyFilters = () => {
  const filters = {
    orgUnits: selectedOrgUnits.value,
    statuses: selectedStatuses.value,
    roles: selectedRoles.value
  }
  emit('filter-change', filters)
  emit('filters-applied', filters)
}

// Автоматическое применение фильтров при изменении
watch([selectedOrgUnits, selectedStatuses, selectedRoles], () => {
  applyFilters()
}, { deep: true })

// Закрытие панели при клике вне её
const handleClickOutside = (event) => {
  if (!filterButtonRef.value || !filterPanelRef.value) return
  
  if (!filterButtonRef.value.contains(event.target) && 
      !filterPanelRef.value.contains(event.target)) {
    isOpen.value = false
  }
}

// Обработка скролла и ресайза
onMounted(() => {
  window.addEventListener('scroll', updatePanelPosition, true)
  window.addEventListener('resize', updatePanelPosition)
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  window.removeEventListener('scroll', updatePanelPosition, true)
  window.removeEventListener('resize', updatePanelPosition)
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.filter-container {
  position: relative;
}

.filter-button {
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

.filter-button:hover {
  border-color: #667eea;
  background: #f8f9fa;
}

.filter-button.active {
  border-color: #667eea;
  background: #667eea;
  color: white;
}

.filter-icon {
  font-size: 14px;
  transition: transform 0.3s ease;
}

.filter-button.active .filter-icon {
  transform: rotate(180deg);
}

.filter-text {
  font-weight: 600;
}

.filter-badge {
  background: #28a745;
  color: white;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  min-width: 20px;
  text-align: center;
}

.filter-button.active .filter-badge {
  background: white;
  color: #667eea;
}

/* Панель фильтров */
.filter-panel {
  position: fixed;
  background: white;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  min-width: 400px;
  max-width: 600px;
  z-index: 1000;
  overflow: hidden;
  margin-top: 8px;
}

.filter-panel-header {
  padding: 16px 20px;
  border-bottom: 1px solid #e9ecef;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f8f9fa;
}

.filter-panel-header h4 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 700;
  color: #333;
}

.btn-clear-all {
  padding: 6px 12px;
  background: transparent;
  border: 1px solid #dc3545;
  border-radius: 6px;
  color: #dc3545;
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 500;
  transition: all 0.3s ease;
}

.btn-clear-all:hover {
  background: #dc3545;
  color: white;
}

.filter-panel-body {
  padding: 20px;
  max-height: 500px;
  overflow-y: auto;
}

.filter-group {
  margin-bottom: 20px;
}

.filter-group:last-child {
  margin-bottom: 0;
}

.filter-label {
  display: block;
  margin-bottom: 12px;
  font-weight: 600;
  color: #333;
  font-size: 0.95rem;
}

.filter-options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.filter-chip {
  padding: 8px 16px;
  background: #f8f9fa;
  border: 2px solid #e9ecef;
  border-radius: 20px;
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 500;
  color: #333;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 6px;
}

.filter-chip:hover {
  border-color: #667eea;
  background: #f0f2ff;
}

.filter-chip.active {
  background: #667eea;
  border-color: #667eea;
  color: white;
}

/* Статусные чипы */
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.dot-active {
  background: #28a745;
}

.dot-pending {
  background: #ffc107;
}

.dot-blocked,
.dot-broken {
  background: #dc3545;
}

.dot-inactive {
  background: #6c757d;
}

.dot-borrowed {
  background: #17a2b8;
}

.dot-maintenance {
  background: #fd7e14;
}

.dot-completed {
  background: #28a745;
}

.dot-cancelled {
  background: #6c757d;
}

.dot-return {
  background: #28a745;
}

.filter-chip.active .status-dot {
  background: white;
}

/* Анимации */
.slide-fade-enter-active {
  transition: all 0.3s ease-out;
}

.slide-fade-leave-active {
  transition: all 0.2s ease-in;
}

.slide-fade-enter-from {
  opacity: 0;
  transform: translateY(-10px);
}

.slide-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* Мобильные стили */
@media (max-width: 768px) {
  .filter-panel {
    min-width: 300px;
    max-width: calc(100vw - 40px);
    left: 20px !important;
    right: 20px;
  }

  .filter-panel-body {
    max-height: 400px;
  }
  
  .filter-options {
    gap: 6px;
  }
  
  .filter-chip {
    font-size: 0.8rem;
    padding: 6px 12px;
  }
}
</style>

