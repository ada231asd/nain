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

        <div class="form-group">
          <label for="parent_org_unit_id">Родительская группа</label>
          <select 
            id="parent_org_unit_id" 
            v-model="formData.parent_org_unit_id" 
            class="form-select"
          >
            <option value="">Без родительской группы</option>
            <option 
              v-for="parent in availableParents" 
              :key="parent.org_unit_id" 
              :value="parent.org_unit_id"
            >
              {{ parent.name }} ({{ parent.unit_type }})
            </option>
          </select>
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
          <label for="logo_url">URL логотипа</label>
          <input 
            id="logo_url" 
            v-model="formData.logo_url" 
            type="url"
            class="form-input"
            placeholder="Введите URL логотипа"
          />
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
const formData = ref({
  unit_type: '',
  parent_org_unit_id: '',
  name: '',
  adress: '',
  logo_url: ''
})

const isEditing = computed(() => !!props.orgUnit)

// Доступные родительские группы (исключаем текущую группу при редактировании)
const availableParents = computed(() => {
  let parents = adminStore.orgUnits.filter(ou => ou.unit_type === 'group')
  
  if (isEditing.value && props.orgUnit) {
    // Исключаем текущую группу и её дочерние элементы
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
    logo_url: ''
  }
}

// Заполнение формы при редактировании
const fillForm = () => {
  if (props.orgUnit) {
    formData.value = {
      unit_type: props.orgUnit.unit_type || '',
      parent_org_unit_id: props.orgUnit.parent_org_unit_id || '',
      name: props.orgUnit.name || '',
      adress: props.orgUnit.adress || '',
      logo_url: props.orgUnit.logo_url || ''
    }
  }
}

// Обработка отправки формы
const handleSubmit = async () => {
  if (isSubmitting.value) return
  
  isSubmitting.value = true
  
  try {
    const data = { ...formData.value }
    
    // Очищаем пустые значения
    if (!data.parent_org_unit_id) {
      delete data.parent_org_unit_id
    }
    if (!data.adress) {
      delete data.adress
    }
    if (!data.logo_url) {
      delete data.logo_url
    }
    
    if (isEditing.value) {
      await adminStore.updateOrgUnit(props.orgUnit.org_unit_id, data)
      emit('org-unit-edited', { id: props.orgUnit.org_unit_id, data })
    } else {
      const id = await adminStore.createOrgUnit(data)
      emit('org-unit-added', { id, data })
    }
    
    closeModal()
  } catch (error) {
    alert('Ошибка сохранения группы: ' + (error.message || 'Неизвестная ошибка'))
  } finally {
    isSubmitting.value = false
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
