<template>
  <div v-if="isVisible" class="modal-overlay" @click="closeModal">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h2>{{ isEditing ? 'Редактировать группу' : 'Добавить группу' }}</h2>
        <button @click="closeModal" class="btn-close">×</button>
      </div>

      <form @submit.prevent="handleSubmit" class="modal-form">
        <div class="form-group">
          <label for="unit_type">Тип группы *</label>
          <select 
            id="unit_type" 
            v-model="formData.unit_type" 
            required
            class="form-select"
          >
            <option value="">Выберите тип</option>
            <option value="group">Группа</option>
            <option value="subgroup">Подгруппа</option>
          </select>
        </div>

        <div v-if="formData.unit_type === 'subgroup'" class="form-group">
          <label for="parent_org_unit_id">Родительская группа *</label>
          <select 
            id="parent_org_unit_id" 
            v-model="formData.parent_org_unit_id" 
            :required="formData.unit_type === 'subgroup'"
            class="form-select"
          >
            <option value="">Выберите родительскую группу</option>
            <option 
              v-for="parent in availableParents" 
              :key="parent.org_unit_id" 
              :value="parent.org_unit_id"
            >
              {{ parent.name }}
            </option>
          </select>
          <small class="form-hint">Подгруппа должна принадлежать родительской группе</small>
        </div>

        <div class="form-group">
          <label for="name">Название *</label>
          <input 
            id="name" 
            v-model="formData.name" 
            type="text" 
            required
            class="form-input"
            placeholder="Введите название группы"
          />
        </div>

        <div class="form-group">
          <label for="adress">Адрес</label>
          <input 
            id="adress" 
            v-model="formData.adress" 
            type="text"
            class="form-input"
            placeholder="Введите адрес группы"
          />
        </div>

        <div class="form-group">
          <label for="default_powerbank_limit">Лимит повербанков по умолчанию</label>
          <input 
            id="default_powerbank_limit" 
            v-model.number="formData.default_powerbank_limit" 
            type="number"
            min="1"
            class="form-input"
            placeholder="1"
          />
          <small class="form-hint">Количество повербанков, которые может взять пользователь по умолчанию</small>
        </div>

        <div class="form-group">
          <label for="reminder_hours">Время до напоминания (часы)</label>
          <input 
            id="reminder_hours" 
            v-model.number="formData.reminder_hours" 
            type="number"
            min="1"
            class="form-input"
            placeholder="24"
          />
          <small class="form-hint">Через сколько часов отправлять напоминание о возврате повербанка</small>
        </div>

        <div class="form-group">
          <label for="write_off_hours">Время до списания (часы)</label>
          <input 
            id="write_off_hours" 
            v-model.number="formData.write_off_hours" 
            type="number"
            min="1"
            class="form-input"
            placeholder="48"
          />
          <small class="form-hint">Через сколько часов считать повербанк не возвращенным</small>
        </div>

        <div
          v-if="formData.unit_type === 'group'"
          class="form-group auto-approval-group"
        >
          <label class="checkbox-label">
            <input
              type="checkbox"
              v-model="formData.aprof"
            />
            Включить автоодобрение пользователей
          </label>

          <label
            v-if="formData.aprof"
            class="checkbox-label confirmation"
          >
            <input
              type="checkbox"
              v-model="autoApprovalConfirmed"
            />
            Вы точно хотитите включить автоподтверждение
          </label>
        </div>

        <div class="form-group">
          <label for="logo">Логотип группы</label>
          <div class="logo-upload-section">
            <div v-if="logoPreview" class="logo-preview">
              <img :src="logoPreview" alt="Предварительный просмотр логотипа" />
              <button type="button" @click="removeLogo" class="remove-logo-btn">×</button>
            </div>
            <div v-else class="logo-upload-placeholder">
              <div class="upload-icon">📷</div>
              <p>Выберите файл логотипа</p>
            </div>
            <input 
              id="logo" 
              ref="logoInput"
              type="file"
              accept="image/*"
              @change="handleLogoChange"
              class="logo-input"
            />
            <label for="logo" class="logo-upload-btn">
              {{ logoFile ? 'Изменить логотип' : 'Выбрать логотип' }}
            </label>
            <div class="url-divider">или</div>
            <input 
              id="logo_url" 
              v-model="logoUrl" 
              type="url"
              class="form-input"
              placeholder="Введите URL изображения"
              @input="handleLogoUrlChange"
            />
          </div>
        </div>

        <div class="form-actions">
          <button type="button" @click="closeModal" class="btn-secondary">
            Отмена
          </button>
          <button type="submit" :disabled="isSubmitting" class="btn-primary">
            {{ isSubmitting ? 'Сохранение...' : (isEditing ? 'Сохранить' : 'Создать') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useAdminStore } from '../stores/admin'
import { showError, showWarning } from '../utils/notifications'

const props = defineProps({
  isVisible: {
    type: Boolean,
    default: false
  },
  orgUnit: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close', 'org-unit-added', 'org-unit-edited'])

const adminStore = useAdminStore()

const isSubmitting = ref(false)
const logoFile = ref(null)
const logoPreview = ref(null)
const logoInput = ref(null)
const logoUrl = ref('')

const normalizeAutoApproval = (value) => {
  return value === 1 || value === '1' || value === true
}

const formData = ref({
  unit_type: '',
  parent_org_unit_id: '',
  name: '',
  adress: '',
  default_powerbank_limit: 1,
  reminder_hours: 24,
  write_off_hours: 48,
  aprof: false
})

const isEditing = computed(() => !!props.orgUnit)
const autoApprovalConfirmed = ref(false)

// Доступные родительские группы
const availableParents = computed(() => {
  // Показываем только группы (не подгруппы)
  let parents = adminStore.orgUnits.filter(ou => ou.unit_type === 'group')
  
  if (isEditing.value && props.orgUnit) {
    // Исключаем текущую группу при редактировании
    parents = parents.filter(ou => ou.org_unit_id !== props.orgUnit.org_unit_id)
  }
  
  return parents
})

// Сброс формы
const resetForm = () => {
  formData.value = {
    unit_type: '',
    parent_org_unit_id: '',
    name: '',
    adress: '',
    default_powerbank_limit: 1,
    reminder_hours: 24,
    write_off_hours: 48,
    aprof: false
  }
  logoFile.value = null
  logoPreview.value = null
  logoUrl.value = ''
  autoApprovalConfirmed.value = false
  if (logoInput.value) {
    logoInput.value.value = ''
  }
}

// Следим за изменением типа группы и сбрасываем родительскую группу для группы
watch(() => formData.value.unit_type, (newType, oldType) => {
  if (newType === 'group') {
    formData.value.parent_org_unit_id = ''
  } else {
    formData.value.aprof = false
  }
})

watch(() => formData.value.aprof, (isEnabled) => {
  if (!isEnabled) {
    autoApprovalConfirmed.value = false
  }
})

// Заполнение формы при редактировании
const fillForm = () => {
  if (props.orgUnit) {
    formData.value = {
      unit_type: props.orgUnit.unit_type || '',
      parent_org_unit_id: props.orgUnit.parent_org_unit_id || '',
      name: props.orgUnit.name || '',
      adress: props.orgUnit.adress || '',
      default_powerbank_limit: props.orgUnit.default_powerbank_limit || 1,
      reminder_hours: props.orgUnit.reminder_hours || 24,
      write_off_hours: props.orgUnit.write_off_hours || 48,
      aprof: normalizeAutoApproval(props.orgUnit.aprof)
    }
    autoApprovalConfirmed.value = normalizeAutoApproval(props.orgUnit.aprof)
    
    // Устанавливаем предварительный просмотр существующего логотипа
    if (props.orgUnit.logo_url) {
      logoPreview.value = props.orgUnit.logo_url.startsWith('/api/')
        ? props.orgUnit.logo_url
        : props.orgUnit.logo_url
    }
  }
}

// Обработка отправки формы
const handleSubmit = async () => {
  if (isSubmitting.value) return
  
  isSubmitting.value = true
  
  try {
    if (formData.value.unit_type === 'group' && formData.value.aprof && !autoApprovalConfirmed.value) {
      showWarning('Подтвердите включение автоподтверждения пользователей')
      isSubmitting.value = false
      return
    }

    const data = { ...formData.value }
    
    // Валидация: группа не должна иметь родительскую группу
    if (data.unit_type === 'group' && data.parent_org_unit_id) {
      showWarning('Группа не может иметь родительскую группу')
      isSubmitting.value = false
      return
    }
    
    // Валидация: подгруппа должна иметь родительскую группу
    if (data.unit_type === 'subgroup' && !data.parent_org_unit_id) {
      showWarning('Подгруппа должна иметь родительскую группу')
      isSubmitting.value = false
      return
    }
    
    // Очищаем пустые значения
    if (!data.parent_org_unit_id) {
      delete data.parent_org_unit_id
    }
    if (!data.adress) {
      delete data.adress
    }

    data.aprof = data.unit_type === 'group' && formData.value.aprof ? 1 : 0
    
    let orgUnitId
    
    if (isEditing.value) {
      await adminStore.updateOrgUnit(props.orgUnit.org_unit_id, data)
      orgUnitId = props.orgUnit.org_unit_id
      emit('org-unit-edited', { id: orgUnitId, data })
    } else {
      orgUnitId = await adminStore.createOrgUnit(data)
      emit('org-unit-added', { id: orgUnitId, data })
    }
    
    // Загружаем логотип если он был выбран (файл или URL)
    if (logoFile.value || logoUrl.value) {
      await uploadLogo(orgUnitId)
    }
    
    closeModal()
  } catch (error) {
    showError('Ошибка сохранения группы: ' + (error.message || 'Неизвестная ошибка'))
  } finally {
    isSubmitting.value = false
  }
}

// Обработка выбора файла логотипа
const handleLogoChange = (event) => {
  const file = event.target.files[0]
  if (file) {
    // Проверяем размер файла (5MB)
    if (file.size > 5 * 1024 * 1024) {
      showWarning('Размер файла не должен превышать 5MB')
      return
    }
    
    // Проверяем тип файла
    if (!file.type.startsWith('image/')) {
      showWarning('Выберите файл изображения')
      return
    }
    
    logoFile.value = file
    logoUrl.value = '' // Очищаем URL при выборе файла
    
    // Создаем предварительный просмотр
    const reader = new FileReader()
    reader.onload = (e) => {
      logoPreview.value = e.target.result
    }
    reader.readAsDataURL(file)
  }
}

// Обработка ввода URL логотипа
const handleLogoUrlChange = () => {
  if (logoUrl.value) {
    logoFile.value = null // Очищаем файл при вводе URL
    if (logoInput.value) {
      logoInput.value.value = ''
    }
    // Устанавливаем предварительный просмотр URL
    logoPreview.value = logoUrl.value
  }
}

// Удаление логотипа
const removeLogo = () => {
  logoFile.value = null
  logoPreview.value = null
  logoUrl.value = ''
  if (logoInput.value) {
    logoInput.value.value = ''
  }
}

// Загрузка логотипа на сервер
const uploadLogo = async (orgUnitId) => {
  try {
    // Загрузка по URL
    if (logoUrl.value && !logoFile.value) {
      const response = await fetch(`/api/org-units/${orgUnitId}/logo-url`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ logo_url: logoUrl.value })
      })
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Ошибка загрузки логотипа по URL')
      }
      
      const result = await response.json()
      console.log('Логотип загружен по URL:', result)
      return
    }
    
    // Загрузка файла
    if (logoFile.value) {
      const formData = new FormData()
      formData.append('logo', logoFile.value)
      
      const response = await fetch(`/api/org-units/${orgUnitId}/logo`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        },
        body: formData
      })
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Ошибка загрузки логотипа')
      }
      
      const result = await response.json()
      console.log('Логотип загружен:', result)
    }
  } catch (error) {
    console.error('Ошибка загрузки логотипа:', error)
    throw error
  }
}

// Закрытие модального окна
const closeModal = () => {
  resetForm()
  emit('close')
}

// Загрузка групп при открытии модального окна
onMounted(async () => {
  if (adminStore.orgUnits.length === 0) {
    await adminStore.fetchOrgUnits()
  }
})

// Отслеживание изменений orgUnit для заполнения формы
watch(() => props.orgUnit, (newOrgUnit) => {
  if (newOrgUnit) {
    fillForm()
  } else {
    resetForm()
  }
}, { immediate: true })

// Отслеживание видимости модального окна
watch(() => props.isVisible, (isVisible) => {
  if (isVisible) {
    if (props.orgUnit) {
      fillForm()
    } else {
      resetForm()
    }
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
}

.modal-content {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #e9ecef;
}

.modal-header h2 {
  margin: 0;
  color: #333;
  font-size: 1.5rem;
  font-weight: 600;
}

.btn-close {
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
  transition: background-color 0.2s;
}

.btn-close:hover {
  background: #f8f9fa;
}

.modal-form {
  padding: 24px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  color: #333;
  font-weight: 500;
  font-size: 0.9rem;
}

.form-input,
.form-select,
.form-textarea {
  width: 100%;
  padding: 12px;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  font-size: 1rem;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.form-input:focus,
.form-select:focus,
.form-textarea:focus {
  outline: none;
  border-color: #667eea;
}

.form-textarea {
  resize: vertical;
  min-height: 80px;
}

.form-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid #e9ecef;
}

.form-hint {
  display: block;
  margin-top: 4px;
  color: #666;
  font-size: 0.85rem;
}

.auto-approval-group .checkbox-label {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 500;
  color: #333;
}

.auto-approval-group .checkbox-label.confirmation {
  font-weight: 400;
  color: #555;
}

.auto-approval-group input[type="checkbox"] {
  width: 18px;
  height: 18px;
}

.btn-primary,
.btn-secondary {
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background: #667eea;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #5a6fd8;
}

.btn-primary:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover {
  background: #5a6268;
}

/* Стили для загрузки логотипа */
.logo-upload-section {
  position: relative;
}

.logo-preview {
  position: relative;
  width: 120px;
  height: 120px;
  margin-bottom: 15px;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  overflow: hidden;
  background: #f8f9fa;
}

.logo-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.remove-logo-btn {
  position: absolute;
  top: 5px;
  right: 5px;
  background: rgba(220, 53, 69, 0.9);
  color: white;
  border: none;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s;
}

.remove-logo-btn:hover {
  background: rgba(220, 53, 69, 1);
}

.logo-upload-placeholder {
  width: 120px;
  height: 120px;
  border: 2px dashed #ccc;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  margin-bottom: 15px;
  background: #f8f9fa;
  color: #666;
  text-align: center;
  padding: 10px;
}

.upload-icon {
  font-size: 2rem;
  margin-bottom: 8px;
}

.logo-upload-placeholder p {
  margin: 0;
  font-size: 0.8rem;
}

.logo-input {
  display: none;
}

.logo-upload-btn {
  display: inline-block;
  padding: 8px 16px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background-color 0.2s;
}

.logo-upload-btn:hover {
  background: #0056b3;
}

.url-divider {
  text-align: center;
  color: #999;
  margin: 12px 0;
  font-size: 0.9rem;
  font-weight: 500;
  position: relative;
}

.url-divider::before,
.url-divider::after {
  content: '';
  position: absolute;
  top: 50%;
  width: 35%;
  height: 1px;
  background: #e0e0e0;
}

.url-divider::before {
  left: 0;
}

.url-divider::after {
  right: 0;
}

/* Мобильные стили */
@media (max-width: 768px) {
  .modal-content {
    width: 95%;
    margin: 20px;
  }
  
  .modal-header {
    padding: 16px 20px;
  }
  
  .modal-form {
    padding: 20px;
  }
  
  .form-actions {
    flex-direction: column;
  }
  
  .btn-primary,
  .btn-secondary {
    width: 100%;
  }
}
</style>
