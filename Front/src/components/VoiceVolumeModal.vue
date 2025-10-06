<template>
  <div v-if="isVisible" class="modal-overlay" @click="closeModal">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h2>Управление громкостью</h2>
        <button @click="closeModal" class="btn-close">×</button>
      </div>
      
      <div class="modal-body">
        <div class="station-info">
          <h3>Станция: {{ station?.box_id || 'N/A' }}</h3>
          <p v-if="station?.org_unit_name" class="station-org">{{ station.org_unit_name }}</p>
        </div>

        <div class="volume-control">
          <label for="volume-slider" class="volume-label">
            Текущая громкость: {{ currentVolume }}
          </label>
          <div class="volume-slider-container">
            <input
              id="volume-slider"
              v-model.number="volumeLevel"
              type="range"
              min="0"
              max="15"
              step="1"
              class="volume-slider"
              :disabled="isLoading"
            />
            <div class="volume-labels">
              <span>0</span>
              <span>5</span>
              <span>10</span>
              <span>15</span>
            </div>
          </div>
          <div class="volume-description">
            <span v-if="volumeLevel <= 2" class="volume-desc">🔇 Очень тихо</span>
            <span v-else-if="volumeLevel <= 4" class="volume-desc">🔉 Тихо</span>
            <span v-else-if="volumeLevel <= 6" class="volume-desc">🔊 Средне</span>
            <span v-else-if="volumeLevel <= 8" class="volume-desc">🔊 Громко</span>
            <span v-else-if="volumeLevel <= 12" class="volume-desc">🔊 Очень громко</span>
            <span v-else class="volume-desc">🔊 Максимально</span>
          </div>
        </div>

        <div v-if="error" class="error-message">
          {{ error }}
        </div>
      </div>

      <div class="modal-footer">
        <button @click="closeModal" class="btn btn-secondary" :disabled="isLoading">
          Отмена
        </button>
        <button @click="saveVolume" class="btn btn-primary" :disabled="isLoading || !hasChanges">
          <span v-if="isLoading">Сохранение...</span>
          <span v-else>Сохранить</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { pythonAPI } from '../api/pythonApi'

const props = defineProps({
  isVisible: {
    type: Boolean,
    default: false
  },
  station: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close', 'volume-updated'])

// Состояние
const currentVolume = ref(0)
const volumeLevel = ref(0)
const isLoading = ref(false)
const error = ref('')

// Вычисляемые свойства
const hasChanges = computed(() => {
  return volumeLevel.value !== currentVolume.value
})

// Методы
const closeModal = () => {
  emit('close')
}

const loadCurrentVolume = async () => {
  if (!props.station?.station_id) return
  
  try {
    isLoading.value = true
    error.value = ''
    // Сначала триггерим запрос уровня громкости через TCP
    await pythonAPI.queryVoiceVolume(props.station.station_id)

    // Затем пробуем получить данные (может потребоваться время)
   // Делаем до 15 попыток c интервалом ~1000мс
    let lastError = ''
    for (let attempt = 0; attempt < 15; attempt++) {
      try {
        const response = await pythonAPI.getVoiceVolume(props.station.station_id)
        if (response.success) {
          currentVolume.value = response.voice_volume || 0
          volumeLevel.value = response.voice_volume || 0
          lastError = ''
          break
        } else {
          lastError = response.error || 'Не удалось получить текущую громкость'
        }
      } catch (e) {
        lastError = e?.message || 'Не удалось получить текущую громкость'
      }
      // подождать перед следующей попыткой
      await new Promise(r => setTimeout(r, 1000))
    }
    if (lastError) {
      error.value = lastError
    }
  } catch (err) {
    console.error('Ошибка при загрузке громкости:', err)
    error.value = 'Ошибка при загрузке громкости: ' + (err.message || 'Неизвестная ошибка')
  } finally {
    isLoading.value = false
  }
}

const saveVolume = async () => {
  if (!props.station?.station_id) return
  
  try {
    isLoading.value = true
    error.value = ''
    
    const response = await pythonAPI.setVoiceVolume({
      station_id: props.station.station_id,
      volume_level: volumeLevel.value
    })
    
    if (response.success) {
      currentVolume.value = volumeLevel.value
      emit('volume-updated', {
        station: props.station,
        volume: volumeLevel.value
      })
      closeModal()
    } else {
      error.value = 'Не удалось установить громкость'
    }
  } catch (err) {
    console.error('Ошибка при сохранении громкости:', err)
    error.value = 'Ошибка при сохранении громкости: ' + (err.message || 'Неизвестная ошибка')
  } finally {
    isLoading.value = false
  }
}

// Сброс состояния при открытии модального окна
watch(() => props.isVisible, (newValue) => {
  if (newValue) {
    error.value = ''
    loadCurrentVolume()
  }
})

// Сброс состояния при смене станции
watch(() => props.station, () => {
  if (props.isVisible) {
    error.value = ''
    loadCurrentVolume()
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
  max-width: 500px;
  width: 90%;
  max-height: 80vh;
  overflow: hidden;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #e9ecef;
  background: #f8f9fa;
}

.modal-header h2 {
  margin: 0;
  color: #333;
  font-size: 1.3rem;
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
  transition: all 0.2s ease;
}

.btn-close:hover {
  background: #e9ecef;
  color: #333;
}

.modal-body {
  padding: 24px;
}

.station-info {
  margin-bottom: 24px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
  border-left: 4px solid #667eea;
}

.station-info h3 {
  margin: 0 0 8px 0;
  color: #333;
  font-size: 1.1rem;
  font-weight: 600;
  font-family: 'Courier New', monospace;
}

.station-org {
  margin: 0;
  color: #667eea;
  font-size: 0.9rem;
  font-weight: 500;
}

.volume-control {
  margin-bottom: 20px;
}

.volume-label {
  display: block;
  margin-bottom: 16px;
  color: #333;
  font-weight: 600;
  font-size: 1rem;
}

.volume-slider-container {
  margin-bottom: 16px;
}

.volume-slider {
  width: 100%;
  height: 8px;
  border-radius: 4px;
  background: #e9ecef;
  outline: none;
  -webkit-appearance: none;
  appearance: none;
  cursor: pointer;
}

.volume-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #667eea;
  cursor: pointer;
  border: 2px solid white;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
}

.volume-slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #667eea;
  cursor: pointer;
  border: 2px solid white;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
}

.volume-slider:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.volume-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  font-size: 0.8rem;
  color: #666;
}

.volume-description {
  text-align: center;
  margin-top: 12px;
}

.volume-desc {
  font-size: 0.9rem;
  color: #333;
  font-weight: 500;
}

.error-message {
  background: #f8d7da;
  color: #721c24;
  padding: 12px;
  border-radius: 6px;
  border: 1px solid #f5c6cb;
  margin-bottom: 16px;
  font-size: 0.9rem;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 20px 24px;
  border-top: 1px solid #e9ecef;
  background: #f8f9fa;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s ease;
  min-width: 100px;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background: #5a6268;
}

.btn-primary {
  background: #667eea;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #5a6fd8;
}

/* Мобильные стили */
@media (max-width: 768px) {
  .modal-content {
    width: 95%;
    margin: 20px;
  }
  
  .modal-header,
  .modal-body,
  .modal-footer {
    padding: 16px;
  }
  
  .modal-footer {
    flex-direction: column;
  }
  
  .btn {
    width: 100%;
  }
}
</style>
