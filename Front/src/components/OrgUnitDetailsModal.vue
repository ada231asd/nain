<template>
  <div v-if="isVisible" class="modal-overlay" @click="closeModal">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h2>{{ isEditing ? 'Редактирование группы' : 'Информация о группе' }}</h2>
        <button @click="closeModal" class="btn-close">×</button>
      </div>

      <div class="modal-body" v-if="orgUnit">
        <div class="org-unit-details">
          <!-- Логотип -->
          <div class="detail-section logo-section-wrapper">
            <div class="logo-section">
              <div class="logo-display">
                <img 
                  v-if="editData.logo_url || orgUnit.logo_url" 
                  :src="editData.logo_url || orgUnit.logo_url" 
                  :alt="orgUnit.name"
                  class="org-logo"
                  @error="handleLogoError"
                />
                <div v-else class="logo-placeholder">
                  <span class="logo-text">{{ getLogoPlaceholder() }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Основная информация -->
          <div class="detail-section">
            <h4>Основная информация</h4>
            <div class="detail-rows">
              <!-- Название -->
              <div class="detail-row" :class="{ 'editable-field': isEditing }">
                <span class="detail-label">Название группы:</span>
                <span v-if="!isEditing" class="detail-value">{{ orgUnit.name }}</span>
                <input v-else v-model="editData.name" class="edit-input" type="text" placeholder="Введите название группы" required />
              </div>

              <!-- Тип группы -->
              <div class="detail-row" :class="{ 'editable-field': isEditing }">
                <span class="detail-label">Тип группы:</span>
                <span v-if="!isEditing" class="detail-value">{{ getUnitTypeText(orgUnit.unit_type) }}</span>
                <select v-else v-model="editData.unit_type" class="edit-input">
                  <option value="group">Группа</option>
                  <option value="subgroup">Подгруппа</option>
                </select>
              </div>

              <!-- Родительская группа -->
              <div class="detail-row" :class="{ 'editable-field': isEditing }">
                <span class="detail-label">Родительская группа:</span>
                <span v-if="!isEditing" class="detail-value">{{ orgUnit.parent_name || 'Нет' }}</span>
                <select v-else v-model="editData.parent_org_unit_id" class="edit-input">
                  <option :value="null">Нет родительской группы</option>
                  <option 
                    v-for="unit in availableParents" 
                    :key="unit.org_unit_id"
                    :value="unit.org_unit_id"
                  >
                    {{ unit.name }}
                  </option>
                </select>
              </div>

              <!-- Адрес -->
              <div class="detail-row" :class="{ 'editable-field': isEditing }">
                <span class="detail-label">Адрес:</span>
                <span v-if="!isEditing" class="detail-value">{{ orgUnit.adress || orgUnit.address || '—' }}</span>
                <input v-else v-model="editData.adress" class="edit-input" type="text" placeholder="Введите адрес" />
              </div>
            </div>
          </div>

          <!-- Настройки -->
          <div class="detail-section">
            <h4>Настройки</h4>
            <div class="detail-rows">
              <!-- Лимит повербанков -->
              <div class="detail-row" :class="{ 'editable-field': isEditing }">
                <span class="detail-label">Лимит повербанков:</span>
                <span v-if="!isEditing" class="detail-value">{{ orgUnit.default_powerbank_limit }}</span>
                <input v-else v-model.number="editData.default_powerbank_limit" class="edit-input" type="number" min="1" max="100" />
              </div>

              <!-- Напоминание -->
              <div class="detail-row" :class="{ 'editable-field': isEditing }">
                <span class="detail-label">Напоминание (часы):</span>
                <span v-if="!isEditing" class="detail-value">{{ orgUnit.reminder_hours }}ч</span>
                <input v-else v-model.number="editData.reminder_hours" class="edit-input" type="number" min="1" max="168" />
              </div>

              <!-- Время до списания -->
              <div class="detail-row" :class="{ 'editable-field': isEditing }">
                <span class="detail-label">Время до списания (часы):</span>
                <span v-if="!isEditing" class="detail-value">{{ orgUnit.write_off_hours }}ч</span>
                <input v-else v-model.number="editData.write_off_hours" class="edit-input" type="number" min="1" max="720" />
              </div>

              <!-- Автоодобрение -->
              <div
                v-if="(isEditing && editData.unit_type === 'group') || (!isEditing && orgUnit.unit_type === 'group')"
                class="detail-row auto-approval-row"
                :class="{ 'editable-field': isEditing }"
              >
                <span class="detail-label">Включить автоодобрение пользователей:</span>
                <span v-if="!isEditing" class="detail-value">
                  {{ isAutoApprovalEnabled ? 'Включено' : 'Выключено' }}
                </span>
                <div v-else class="auto-approval-controls">
                  <label class="checkbox-label">
                    <input type="checkbox" v-model="editData.aprof" />
                    Включить автоодобрение пользователей
                  </label>
                  <label
                    v-if="editData.aprof"
                    class="checkbox-label confirmation"
                  >
                    <input type="checkbox" v-model="autoApprovalConfirmed" />
                    Вы точно хотитите включить автоподтверждение
                  </label>
                </div>
              </div>

              <!-- URL логотипа -->
              <div class="detail-row" :class="{ 'editable-field': isEditing }">
                <span class="detail-label">URL логотипа:</span>
                <span v-if="!isEditing" class="detail-value url-value">{{ orgUnit.logo_url || '—' }}</span>
                <input v-else v-model="editData.logo_url" class="edit-input" type="url" placeholder="https://example.com/logo.png" />
              </div>
            </div>
          </div>

          <!-- Дополнительная информация -->
          <div class="detail-section">
            <h4>Дополнительная информация</h4>
            <div class="detail-rows">
              <div class="detail-row">
                <span class="detail-label">ID группы:</span>
                <span class="detail-value">{{ orgUnit.org_unit_id }}</span>
              </div>
              <div class="detail-row" v-if="orgUnit.created_at">
                <span class="detail-label">Дата создания:</span>
                <span class="detail-value">{{ formatDate(orgUnit.created_at) }}</span>
              </div>
              <div class="detail-row" v-if="orgUnit.updated_at">
                <span class="detail-label">Последнее обновление:</span>
                <span class="detail-value">{{ formatDate(orgUnit.updated_at) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <div v-if="isEditing" class="edit-actions">
          <button @click="saveChanges" class="btn btn-success" :disabled="isSaving">
            {{ isSaving ? 'Сохранение...' : '💾 Сохранить' }}
          </button>
          <button @click="cancelEditing" class="btn btn-cancel" :disabled="isSaving">
            ❌ Отменить
          </button>
        </div>
        <div v-else class="view-actions">
          <button @click="viewStations" class="btn btn-info">
            📡 Станции
          </button>
          <button @click="startEditing" class="btn btn-primary">
            ✏️ Редактировать
          </button>
          <button @click="closeModal" class="btn btn-secondary">
            Закрыть
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useAdminStore } from '../stores/admin'
import { showSuccess, showError, showConfirm, showWarning } from '../utils/notifications'

const props = defineProps({
  isVisible: {
    type: Boolean,
    default: false
  },
  orgUnit: {
    type: Object,
    default: null
  },
  autoEdit: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close', 'updated', 'view-stations'])

const adminStore = useAdminStore()

const normalizeAutoApproval = (value) => {
  return value === 1 || value === '1' || value === true
}

const isEditing = ref(false)
const isSaving = ref(false)
const logoError = ref(false)
const previewError = ref(false)
const autoApprovalConfirmed = ref(false)
const isAutoApprovalEnabled = computed(() => {
  if (!props.orgUnit) return false
  return normalizeAutoApproval(props.orgUnit.aprof)
})

const editData = ref({
  name: '',
  unit_type: 'group',
  adress: '',
  logo_url: '',
  default_powerbank_limit: 1,
  reminder_hours: 24,
  write_off_hours: 48,
  parent_org_unit_id: null,
  aprof: false
})

// Доступные родительские группы (исключая текущую группу и её дочерние)
const availableParents = computed(() => {
  if (!props.orgUnit) return []
  
  return adminStore.orgUnits.filter(unit => {
    // Исключаем саму группу
    if (unit.org_unit_id === props.orgUnit.org_unit_id) return false
    
    // Исключаем дочерние группы (они не могут быть родителями)
    if (unit.parent_org_unit_id === props.orgUnit.org_unit_id) return false
    
    return true
  })
})

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

// Получение плейсхолдера логотипа
const getLogoPlaceholder = () => {
  if (!props.orgUnit?.name) return '?'
  const words = props.orgUnit.name.split(' ').filter(w => w.length > 0)
  if (words.length === 0) return '?'
  if (words.length === 1) return words[0].substring(0, 2).toUpperCase()
  return (words[0][0] + words[1][0]).toUpperCase()
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

// Обработка ошибки загрузки логотипа
const handleLogoError = () => {
  logoError.value = true
}

const handlePreviewError = () => {
  previewError.value = true
}

// Начать редактирование
const startEditing = () => {
  if (!props.orgUnit) return
  
  editData.value = {
    name: props.orgUnit.name || '',
    unit_type: props.orgUnit.unit_type || 'group',
    adress: props.orgUnit.adress || '',
    logo_url: props.orgUnit.logo_url || '',
    default_powerbank_limit: props.orgUnit.default_powerbank_limit || 1,
    reminder_hours: props.orgUnit.reminder_hours || 24,
    write_off_hours: props.orgUnit.write_off_hours || 48,
    parent_org_unit_id: props.orgUnit.parent_org_unit_id || null,
    aprof: normalizeAutoApproval(props.orgUnit.aprof)
  }
  
  autoApprovalConfirmed.value = normalizeAutoApproval(props.orgUnit.aprof)
  isEditing.value = true
}

// Отменить редактирование
const cancelEditing = () => {
  isEditing.value = false
  previewError.value = false
  autoApprovalConfirmed.value = false
}

// Сохранить изменения
const saveChanges = async () => {
  if (!props.orgUnit) return
  
  isSaving.value = true
  
  try {
    if (editData.value.unit_type === 'group' && editData.value.aprof && !autoApprovalConfirmed.value) {
      showWarning('Подтвердите включение автоподтверждения пользователей')
      isSaving.value = false
      return
    }

    const payload = {
      ...editData.value,
      aprof: editData.value.unit_type === 'group' && editData.value.aprof ? 1 : 0
    }

    await adminStore.updateOrgUnit(props.orgUnit.org_unit_id, payload)
    
    // Обновляем локальные данные
    Object.assign(props.orgUnit, payload)
    
    isEditing.value = false
    emit('updated', props.orgUnit)
    
    // Показываем уведомление об успехе
    showSuccess('Группа успешно обновлена!')
  } catch (error) {
    console.error('Ошибка при обновлении группы:', error)
    showError('Ошибка при обновлении группы: ' + (error.message || 'Неизвестная ошибка'))
  } finally {
    isSaving.value = false
  }
}

// Просмотр станций группы
const viewStations = () => {
  emit('view-stations', props.orgUnit)
}

// Закрытие модального окна
const closeModal = async () => {
  if (isEditing.value) {
    if (await showConfirm('У вас есть несохраненные изменения. Закрыть окно?')) {
      isEditing.value = false
      emit('close')
    }
  } else {
    emit('close')
  }
}

// Сброс состояния при закрытии
watch(() => props.isVisible, (newValue) => {
  if (!newValue) {
    isEditing.value = false
    logoError.value = false
    previewError.value = false
    autoApprovalConfirmed.value = false
  } else if (newValue && props.autoEdit) {
    // Автоматически включаем режим редактирования, если передан флаг autoEdit
    startEditing()
  }
})

watch(() => editData.value.unit_type, (newType) => {
  if (newType !== 'group') {
    editData.value.aprof = false
    autoApprovalConfirmed.value = false
  }
})

watch(() => editData.value.aprof, (isEnabled) => {
  if (!isEnabled) {
    autoApprovalConfirmed.value = false
  }
})
</script>

<style scoped>
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
  border-radius: 16px;
  width: 90%;
  max-width: 800px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
  overflow: hidden;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 28px;
  border-bottom: 2px solid #e9ecef;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.modal-header h2 {
  margin: 0;
  color: white;
  font-size: 1.5rem;
  font-weight: 700;
}

.btn-close {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  font-size: 28px;
  color: white;
  cursor: pointer;
  padding: 0;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: all 0.2s;
  font-weight: 300;
}

.btn-close:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: rotate(90deg);
}

.modal-body {
  flex: 1;
  padding: 28px;
  overflow-y: auto;
}

/* Детали группы */
.org-unit-details {
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

.logo-section-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 30px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-left: none;
}

.logo-section {
  display: flex;
  justify-content: center;
}

.logo-display {
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

.org-logo {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.logo-placeholder {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-text {
  font-size: 48px;
  font-weight: 700;
  color: white;
  text-transform: uppercase;
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
  min-width: 180px;
}

.detail-value {
  color: #333;
  font-size: 1rem;
  text-align: right;
  flex: 1;
}

.auto-approval-row {
  align-items: flex-start;
  gap: 16px;
}

.auto-approval-controls {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
  flex: 1;
}

.auto-approval-row .checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  color: #333;
}

.auto-approval-row .checkbox-label.confirmation {
  font-weight: 400;
  color: #555;
}

.auto-approval-row input[type="checkbox"] {
  width: 18px;
  height: 18px;
}

.url-value {
  font-size: 0.85rem;
  word-break: break-all;
  font-family: monospace;
}

/* Редактируемые поля */
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

/* Футер */
.modal-footer {
  padding: 20px 28px;
  border-top: 2px solid #e9ecef;
  background: var(--background-secondary, #f8f9fa);
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

.btn {
  padding: 10px 16px;
  border: none;
  border-radius: 6px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: #667eea;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #5a6fd8;
}

.btn-success {
  background: #28a745;
  color: white;
}

.btn-success:hover:not(:disabled) {
  background: #218838;
}

.btn-info {
  background: #17a2b8;
  color: white;
}

.btn-info:hover:not(:disabled) {
  background: #138496;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background: #5a6268;
}

.btn-cancel {
  background: #dc3545;
  color: white;
}

.btn-cancel:hover:not(:disabled) {
  background: #c82333;
}

/* Мобильные стили */
@media (max-width: 768px) {
  .modal-content {
    width: 95%;
    max-height: 95vh;
  }

  .modal-header {
    padding: 20px;
  }

  .modal-header h2 {
    font-size: 1.2rem;
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

  .edit-actions,
  .view-actions {
    flex-direction: column;
  }

  .btn {
    width: 100%;
  }

  .logo-display {
    width: 100px;
    height: 100px;
  }

  .logo-text {
    font-size: 36px;
  }
}

/* Анимация появления */
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: scale(0.9);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.modal-content {
  animation: fadeIn 0.3s ease;
}
</style>

