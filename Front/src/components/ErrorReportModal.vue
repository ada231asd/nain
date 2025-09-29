<template>
  <div v-if="isVisible" class="modal-overlay" @click="closeModal">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h3>🚨 Сообщить об ошибке</h3>
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
              <span class="error-type-icon">{{ errorType.icon }}</span>
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
        <button @click="closeModal" class="btn-cancel">
          Отмена
        </button>
        <button 
          @click="submitErrorReport" 
          class="btn-submit"
          :disabled="!canSubmit || isSubmitting"
        >
          <span v-if="isSubmitting">⏳ Отправка...</span>
          <span v-else>📤 Отправить</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'

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
const additionalNotes = ref('')
const isSubmitting = ref(false)

// Вычисляемые свойства
const canSubmit = computed(() => {
  return !!selectedErrorType.value
})

// Типы ошибок
const errorTypes = ref([
  {
    id: 'cable_type_c_damaged',
    name: 'Поврежден кабель Type-C',
    icon: '🔌',
    description: 'Кабель Type-C поврежден или не работает'
  },
  {
    id: 'cable_lightning_damaged',
    name: 'Поврежден кабель Lightning',
    icon: '⚡',
    description: 'Кабель Lightning поврежден или не работает'
  },
  {
    id: 'cable_micro_usb_damaged',
    name: 'Поврежден кабель MicroUSB',
    icon: '📱',
    description: 'Кабель MicroUSB поврежден или не работает'
  },
  {
    id: 'powerbank_not_working',
    name: 'Повербанк не работает',
    icon: '🔋',
    description: 'Повербанк не заряжается или не включается'
  }
])

// Методы
const closeModal = () => {
  selectedErrorType.value = null
  additionalNotes.value = ''
  isSubmitting.value = false
  emit('close')
}

const submitErrorReport = async () => {
  if (!canSubmit.value) return
  
  try {
    isSubmitting.value = true
    
    const errorReport = {
      order_id: props.order?.order_id || props.order?.id,
      powerbank_id: props.order?.powerbank_id,
      station_id: props.order?.station_id,
      user_id: props.order?.user_id,
      error_type: selectedErrorType.value,
      additional_notes: additionalNotes.value,
      timestamp: new Date().toISOString()
    }
    
    emit('submit', errorReport)
    
  } catch (error) {
    console.error('Ошибка при отправке отчета:', error)
    alert('❌ Ошибка при отправке отчета об ошибке')
  } finally {
    isSubmitting.value = false
  }
}

// Сброс формы при открытии модального окна
watch(() => props.isVisible, (newValue) => {
  if (newValue) {
    selectedErrorType.value = null
    additionalNotes.value = ''
    isSubmitting.value = false
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
  gap: 15px;
  flex: 1;
}

.error-type-icon {
  font-size: 2rem;
  line-height: 1;
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
  
  .error-type-content {
    gap: 10px;
  }
  
  .error-type-icon {
    font-size: 1.5rem;
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
