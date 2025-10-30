<template>
  <div v-if="isVisible" class="modal-overlay" @click="!isLoading && closeModal()">
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
        

        <div class="additional-notes">
          <label for="notes">Дополнительные комментарии (необязательно):</label>
          <textarea 
            id="notes"
            v-model="additionalNotes"
            placeholder="Опишите проблему подробнее..."
            class="notes-textarea"
            rows="3"
          ></textarea>
        </div>
      </div>
      
      <div class="modal-footer">
        <button 
          @click="submitErrorReport" 
          class="btn-submit"
          :disabled="!canSubmit || isLoading"
        >
          <span v-if="isLoading" class="submitting-content">
            <span class="spinner"></span>
            Ожидание подтверждения...
          </span>
          <span v-else>Отправить</span>
        </button>
        <button @click="closeModal" class="btn-cancel" :disabled="isLoading">
          Отмена
        </button>
      </div>
      
      <!-- Информационное сообщение о долгом ожидании -->
      <div v-if="isLoading" class="waiting-info">
        <p>⏳ Ожидаем вставки повербанка в станцию (до 30 секунд)...</p>
        <p class="waiting-hint">Пожалуйста, вставьте повербанк в станцию и не закрывайте это окно.</p>
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
  },
  isLoading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close', 'submit'])

// Состояние
const selectedErrorType = ref(null)
const additionalNotes = ref('')

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
  // Не закрываем модальное окно, если идет загрузка
  if (props.isLoading) return
  
  selectedErrorType.value = null
  additionalNotes.value = ''
  emit('close')
}

const submitErrorReport = async () => {
  if (!canSubmit.value || props.isLoading) return
  
  try {
    // Отправляем запрос на возврат с ошибкой через Long Polling API
    const response = await pythonAPI.returnError({
      station_box_id: props.order?.station_box_id,
      user_phone: props.order?.user_phone,
      error_type_id: selectedErrorType.value,
      timeout_seconds: 30 // 30 секунд ожидания
    })
    
    if (response.success) {
      // Успешно обработан возврат с ошибкой
      const errorReport = {
        order_id: props.order?.order_id || props.order?.id,
        powerbank_serial: response.powerbank_serial || props.order?.powerbank_serial,
        station_box_id: response.station_box_id || props.order?.station_box_id,
        user_phone: response.user_phone || props.order?.user_phone,
        error_type: response.error_type || selectedErrorType.value,
        error_name: response.error_name,
        slot_number: response.slot_number,
        additional_notes: additionalNotes.value,
        timestamp: new Date().toISOString(),
        return_request_success: true,
        return_message: response.message
      }
      
      emit('submit', errorReport)
    } else {
      // Ошибка при обработке возврата
      console.error('❌ Ошибка возврата с ошибкой:', response.error)
      emit('submit', {
        ...props.order,
        error_type: selectedErrorType.value,
        additional_notes: additionalNotes.value,
        return_request_success: false,
        return_error: response.error
      })
    }
  } catch (error) {
    console.error('❌ Ошибка API запроса возврата с ошибкой:', error)
    emit('submit', {
      ...props.order,
      error_type: selectedErrorType.value,
      additional_notes: additionalNotes.value,
      return_request_success: false,
      return_error: error.message || 'Ошибка отправки запроса'
    })
  }
}

// Сброс формы при открытии модального окна
watch(() => props.isVisible, (newValue) => {
  if (newValue) {
    selectedErrorType.value = null
    additionalNotes.value = ''
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

.additional-notes {
  margin-top: 25px;
}

.additional-notes label {
  display: block;
  color: #333;
  font-weight: 600;
  margin-bottom: 10px;
  font-size: 1rem;
}

.notes-textarea {
  width: 100%;
  padding: 15px;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  font-size: 1rem;
  font-family: inherit;
  resize: vertical;
  min-height: 80px;
  transition: border-color 0.3s ease;
}

.notes-textarea:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
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

.submitting-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

.spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.waiting-info {
  padding: 20px 30px;
  background: #fff9e6;
  border-top: 2px solid #ffd966;
  text-align: center;
}

.waiting-info p {
  margin: 5px 0;
  color: #856404;
  font-size: 1rem;
}

.waiting-hint {
  font-size: 0.9rem;
  opacity: 0.8;
  font-style: italic;
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
