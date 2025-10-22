<template>
  <div class="org-unit-card" :class="getCardClass()">
    <div class="org-unit-info">
      <div class="org-unit-main">
        <h3 class="org-unit-name">{{ orgUnit.name }}</h3>
        <p class="org-unit-type">{{ getUnitTypeText(orgUnit.unit_type) }}</p>
        <p v-if="orgUnit.adress" class="org-unit-address">
          Адрес: {{ orgUnit.adress }}
        </p>
        <p v-if="orgUnit.parent_name" class="org-unit-parent">
          Родительская группа: <strong>{{ orgUnit.parent_name }}</strong>
        </p>
        <div v-if="orgUnit.default_powerbank_limit" class="org-unit-limit">
          <span class="limit-icon">🔋</span>
          <span>Лимит: {{ orgUnit.default_powerbank_limit }}</span>
        </div>
        <div v-if="orgUnit.reminder_hours" class="org-unit-reminder">
          <span class="reminder-icon">⏰</span>
          <span>Напоминание: {{ orgUnit.reminder_hours }}ч</span>
        </div>
      </div>
      
      <div class="org-unit-stats">
        <div class="stat-item">
          <span class="stat-label">ID:</span>
          <span class="stat-value">{{ orgUnit.org_unit_id }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Создана:</span>
          <span class="stat-value">{{ formatDate(orgUnit.created_at) }}</span>
        </div>
        <div v-if="orgUnit.updated_at" class="stat-item">
          <span class="stat-label">Обновлена:</span>
          <span class="stat-value">{{ formatDate(orgUnit.updated_at) }}</span>
        </div>
      </div>
    </div>
    
    <div class="org-unit-actions">
      <button 
        @click="viewStations" 
        class="btn-action btn-stations"
        title="Просмотреть станции"
      >
        📡 Станции
      </button>
      <select 
        class="action-select" 
        @change="handleAction"
        :value="''"
      >
        <option value="">Действия</option>
        <option value="edit">✏️ Редактировать</option>
        <option value="stations">📡 Станции группы</option>
        <option value="delete">🗑️ Удалить</option>
      </select>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  orgUnit: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['edit', 'delete', 'view-stations'])

// Получение CSS класса для карточки
const getCardClass = () => {
  const classes = []
  
  // Класс по типу группы
  if (props.orgUnit.unit_type === 'group') {
    classes.push('type-group')
  } else if (props.orgUnit.unit_type === 'subgroup') {
    classes.push('type-subgroup')
  }
  
  // Класс для групп с родителем
  if (props.orgUnit.parent_org_unit_id) {
    classes.push('has-parent')
  }
  
  return classes.join(' ')
}

// Получение текста типа группы
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

// Форматирование даты
const formatDate = (dateString) => {
  if (!dateString) return '—'
  
  try {
    const date = new Date(dateString)
    return date.toLocaleDateString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch (error) {
    return '—'
  }
}

// Обработка действий
const handleAction = (event) => {
  const action = event.target.value
  if (!action) return
  
  switch (action) {
    case 'edit':
      emit('edit', props.orgUnit)
      break
    case 'stations':
      viewStations()
      break
    case 'delete':
      if (confirm(`Вы уверены, что хотите удалить группу "${props.orgUnit.name}"?`)) {
        emit('delete', props.orgUnit.org_unit_id)
      }
      break
  }
  
  // Сброс значения select
  event.target.value = ''
}

// Просмотр станций группы
const viewStations = () => {
  emit('view-stations', props.orgUnit)
}
</script>

<style scoped>
.org-unit-card {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 12px;
  border-left: 6px solid #17a2b8;
  transition: all 0.3s ease;
  margin-bottom: 15px;
}

.org-unit-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
}

/* Типы групп */
.org-unit-card.type-group {
  border-left-color: #28a745;
}

.org-unit-card.type-subgroup {
  border-left-color: #ffc107;
}

.org-unit-card.has-parent {
  background: #f0f8ff;
}

.org-unit-info {
  display: flex;
  align-items: flex-start;
  gap: 20px;
  flex: 1;
}

.org-unit-main {
  flex: 1;
}

.org-unit-name {
  color: #333;
  margin: 0 0 8px 0;
  font-size: 1.2rem;
  font-weight: 600;
}

.org-unit-type {
  color: #667eea;
  margin: 0 0 8px 0;
  font-size: 0.9rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.org-unit-address {
  color: #666;
  margin: 0 0 8px 0;
  font-size: 0.9rem;
  line-height: 1.4;
}

.org-unit-parent {
  color: #666;
  margin: 0;
  font-size: 0.85rem;
}

.org-unit-parent strong {
  color: #333;
}

.org-unit-limit,
.org-unit-reminder {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #666;
  margin: 4px 0;
  font-size: 0.85rem;
}

.limit-icon,
.reminder-icon {
  font-size: 1rem;
}

.org-unit-stats {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 120px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.85rem;
}

.stat-label {
  color: #666;
  font-weight: 500;
}

.stat-value {
  color: #333;
  font-weight: 600;
}

.org-unit-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: flex-end;
}

.btn-action {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.btn-stations {
  background: #17a2b8;
  color: white;
}

.btn-stations:hover {
  background: #138496;
}

.action-select {
  padding: 8px 12px;
  border: 2px solid #e9ecef;
  border-radius: 6px;
  font-size: 0.85rem;
  background: white;
  cursor: pointer;
  transition: border-color 0.2s;
  min-width: 140px;
}

.action-select:focus {
  outline: none;
  border-color: #667eea;
}

/* Мобильные стили */
@media (max-width: 768px) {
  .org-unit-card {
    flex-direction: column;
    gap: 15px;
  }
  
  .org-unit-info {
    flex-direction: column;
    gap: 15px;
  }
  
  .org-unit-stats {
    flex-direction: row;
    flex-wrap: wrap;
    gap: 15px;
  }
  
  .stat-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 2px;
  }
  
  .org-unit-actions {
    flex-direction: row;
    justify-content: space-between;
    width: 100%;
  }
  
  .action-select {
    flex: 1;
    min-width: auto;
  }
}
</style>
