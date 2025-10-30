<template>
  <div v-if="isVisible" class="modal-overlay" @click="closeModal()">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h3>Сообщить об ошибке</h3>
        <button @click="closeModal" class="btn-close">×</button>
      </div>
      
      <div class="modal-body">
        <p class="modal-description">
          Выберите тип проблемы с повербанком:
        </p>
        
        <div class="error-types">
          <label 
            v-for="errorType in errorTypes" 
            :key="errorType.id"
            class="error-type-option"
            :class="{ 'selected': selectedErrorType === errorType.id }"
          >
            <input 
              type="radio" 
              :value="errorType.id" 
              v-model="selectedErrorType"
              class="error-type-radio"
            />
            <div class="error-type-content">
              <div class="error-type-text">
                <strong>{{ errorType.name }}</strong>
                <p>{{ errorType.description }}</p>
              </div>
            </div>
          </label>
        </div>
      </div>
      
      <div class="modal-footer">
        <button 
          @click="submitErrorReport" 
          class="btn-submit"
          :disabled="!canSubmit"
        >
          Отправить
        </button>
        <button @click="closeModal" class="btn-cancel">
          Отмена
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed, onMounted } from 'vue'
import { pythonAPI } from '../api/pythonApi'

const props = defineProps({
  isVisible: {
    type: Boolean,
    default: false
  },
  order: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close', 'submit'])

// Состояние
const selectedErrorType = ref(null)

// Вычисляемые свойства
const canSubmit = computed(() => {
  // Требуем выбор типа ошибки, так как сервер не принимает пустую строку
  return !!selectedErrorType.value
})

// Типы ошибок (загружаются с сервера)
const errorTypes = ref([])
const isLoadingErrorTypes = ref(false)

// Загружаем типы ошибок с сервера
const loadErrorTypes = async () => {
  try {
    isLoadingErrorTypes.value = true
    const response = await pythonAPI.getErrorTypes()

    // Унифицированное извлечение массива типов из разных форматов ответа
    let rawTypes = []
    if (Array.isArray(response)) {
      rawTypes = response
    } else if (Array.isArray(response?.data)) {
      rawTypes = response.data
    } else if (Array.isArray(response?.error_types)) {
      rawTypes = response.error_types
    } else if (Array.isArray(response?.data?.error_types)) {
      rawTypes = response.data.error_types
    }

    if (!Array.isArray(rawTypes) || rawTypes.length === 0) {
      throw new Error('Unexpected error types response shape')
    }

    // Приводим к единому формату для UI
    errorTypes.value = rawTypes.map((error) => {
      const id = error.id_er ?? error.id ?? error.error_type_id ?? error.value
      const name = error.type_error ?? error.name ?? error.label ?? String(id)
      return {
        id: parseInt(id),
        name,
        description: error.description || name
      }
    }).filter(e => Number.isFinite(e.id) && e.name)
  } catch (error) {
    console.error('❌ Ошибка загрузки типов ошибок:', error)
    // Fallback к старым типам в случае ошибки
    errorTypes.value = [
      { id: 1, name: 'Аккумулятор не заряжает', description: 'Аккумулятор не заряжает' },
      { id: 2, name: 'Сломан Type C', description: 'Сломан Type C' },
      { id: 3, name: 'Сломан Micro usb', description: 'Сломан Micro usb' },
      { id: 4, name: 'Сломан liting', description: 'Сломан liting' }
    ]
  } finally {
    isLoadingErrorTypes.value = false
  }
}

// Загружаем типы ошибок при создании компонента
onMounted(() => {
  loadErrorTypes()
})

// Методы
const closeModal = () => {
  selectedErrorType.value = null
  emit('close')
}

const submitErrorReport = () => {
  if (!canSubmit.value) return
  
  // Сразу отправляем данные родителю и закрываем модалку
  const errorReport = {
    order_id: props.order?.order_id || props.order?.id,
    powerbank_serial: props.order?.powerbank_serial,
    station_box_id: props.order?.station_box_id,
    user_phone: props.order?.user_phone,
    error_type_id: selectedErrorType.value,
    timestamp: new Date().toISOString()
  }
  
  emit('submit', errorReport)
  
  // Закрываем модалку
  selectedErrorType.value = null
  emit('close')
}

// Сброс формы при открытии модального окна
watch(() => props.isVisible, (newValue) => {
  if (newValue) {
    selectedErrorType.value = null
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
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-content {
  background: white;
  border-radius: 15px;
  max-width: 600px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
  animation: modalSlideIn 0.3s ease-out;
}

@keyframes modalSlideIn {
  from {
    opacity: 0;
    transform: translateY(-50px) scale(0.9);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 25px 30px 20px;
  border-bottom: 2px solid #f0f0f0;
}

.modal-header h3 {
  margin: 0;
  color: #333;
  font-size: 1.5rem;
  font-weight: 600;
}

.btn-close {
  background: none;
  border: none;
  font-size: 2rem;
  color: #999;
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

.btn-close:hover {
  background: #f5f5f5;
  color: #666;
}

.modal-body {
  padding: 30px;
}

.modal-description {
  color: #666;
  margin-bottom: 25px;
  font-size: 1.1rem;
  line-height: 1.5;
}

.error-types {
  display: flex;
  flex-direction: column;
  gap: 15px;
  margin-bottom: 25px;
}

.error-type-option {
  display: flex;
  align-items: flex-start;
  padding: 20px;
  border: 2px solid #e9ecef;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  background: #fafafa;
}

.error-type-option:hover {
  border-color: #667eea;
  background: #f8f9ff;
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(102, 126, 234, 0.1);
}

.error-type-option.selected {
  border-color: #667eea;
  background: #f0f4ff;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.error-type-radio {
  margin: 0 15px 0 0;
  width: 20px;
  height: 20px;
  accent-color: #667eea;
}

.error-type-content {
  display: flex;
  align-items: flex-start;
  flex: 1;
}

.error-type-text strong {
  display: block;
  color: #333;
  font-size: 1.1rem;
  margin-bottom: 5px;
  font-weight: 600;
}

.error-type-text p {
  color: #666;
  margin: 0;
  font-size: 0.95rem;
  line-height: 1.4;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 15px;
  padding: 20px 30px 30px;
  border-top: 2px solid #f0f0f0;
}

.btn-cancel,
.btn-submit {
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  min-width: 120px;
}

.btn-cancel {
  background: #6c757d;
  color: white;
}

.btn-cancel:hover {
  background: #5a6268;
  transform: translateY(-1px);
}

.btn-submit {
  background: #667eea;
  color: white;
}

.btn-submit:hover:not(:disabled) {
  background: #5a6fd8;
  transform: translateY(-1px);
}

.btn-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

/* Мобильные стили */
@media (max-width: 768px) {
  .modal-overlay {
    padding: 10px;
  }
  
  .modal-content {
    max-height: 95vh;
  }
  
  .modal-header,
  .modal-body,
  .modal-footer {
    padding-left: 20px;
    padding-right: 20px;
  }
  
  .error-type-option {
    padding: 15px;
  }
  
  .modal-footer {
    flex-direction: column;
  }
  
  .btn-cancel,
  .btn-submit {
    width: 100%;
  }
}
</style>
