<template>
  <div v-if="isVisible" class="modal-overlay" @click="closeModal">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h2>Управление адресом сервера</h2>
        <button @click="closeModal" class="close-btn">&times;</button>
      </div>
      
      <div class="modal-body">
        <div v-if="isLoading" class="loading-state">
          <div class="loading-spinner"></div>
          <p>Загрузка данных...</p>
        </div>
        
        <div v-else-if="error" class="error-state">
          <div class="error-icon">⚠️</div>
          <p> нет соединения </p>
          <button @click="loadServerAddress" class="btn btn-primary">Повторить</button>
        </div>
        
        <form v-else @submit.prevent="saveServerAddress" class="server-address-form">
          <div class="station-info">
            <h3>Станция: {{ station?.box_id || 'N/A' }}</h3>
            <p v-if="station?.org_unit_name" class="station-org">{{ station.org_unit_name }}</p>
          </div>
          
          <div class="form-group">
            <label for="server_address">Адрес сервера:</label>
            <input 
              id="server_address"
              v-model="formData.server_address" 
              type="text" 
              placeholder="192.168.1.100"
              required 
              class="form-input"
              :disabled="isSaving"
            />
            <small class="form-hint">IP-адрес сервера без порта</small>
          </div>
          
          <div class="form-group">
            <label for="server_port">Порт сервера:</label>
            <input 
              id="server_port"
              v-model.number="formData.server_port" 
              type="number" 
              min="1" 
              max="65535"
              placeholder="8080"
              required 
              class="form-input"
              :disabled="isSaving"
            />
            <small class="form-hint">Порт сервера (1-65535)</small>
          </div>
          
          <div class="form-group">
            <label for="heartbeat_interval">Интервал heartbeat (сек):</label>
            <input 
              id="heartbeat_interval"
              v-model.number="formData.heartbeat_interval" 
              type="number" 
              min="1" 
              max="255"
              placeholder="30"
              required 
              class="form-input"
              :disabled="isSaving"
            />
            <small class="form-hint">Интервал отправки heartbeat (1-255 секунд)</small>
          </div>
          
          <div v-if="currentServerAddress" class="current-info">
            <h4>Текущие настройки:</h4>
            <div class="current-details">
              <div class="detail-row">
                <span class="detail-label">Адрес:</span>
                <span class="detail-value">{{ currentServerAddress.server_address || 'Не установлен' }}</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">Порт:</span>
                <span class="detail-value">{{ currentServerAddress.server_port || 'Не установлен' }}</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">Box ID:</span>
                <span class="detail-value">{{ currentServerAddress.station_box_id || 'N/A' }}</span>
              </div>
            </div>
          </div>
          
          <div class="form-actions">
            <button type="button" @click="closeModal" class="btn btn-secondary" :disabled="isSaving">
              Отмена
            </button>
            <button type="submit" class="btn btn-primary" :disabled="isSaving || !isFormValid">
              {{ isSaving ? 'Сохранение...' : 'Сохранить настройки' }}
            </button>
          </div>
        </form>
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

const emit = defineEmits(['close', 'address-updated'])

const isLoading = ref(false)
const isSaving = ref(false)
const error = ref('')
const currentServerAddress = ref(null)

const formData = ref({
  server_address: '',
  server_port: 8080,
  heartbeat_interval: 30
})

const isFormValid = computed(() => {
  const address = formData.value.server_address.trim()
  return address && 
         address.length > 0 &&
         formData.value.server_port > 0 && 
         formData.value.server_port <= 65535 &&
         formData.value.heartbeat_interval >= 1 &&
         formData.value.heartbeat_interval <= 255
})

// Загружаем текущие настройки при открытии модального окна
watch(() => props.isVisible, async (isVisible) => {
  if (isVisible && props.station) {
    await loadServerAddress()
  }
})

const loadServerAddress = async () => {
  if (!props.station?.station_id) return
  
  isLoading.value = true
  error.value = ''
  
  try {
    // Сначала триггерим запрос адреса сервера через TCP
    await pythonAPI.queryServerAddress(props.station.station_id)

    // Затем пробуем получить данные с ретраями
    let lastError = ''
    let result = null
    for (let attempt = 0; attempt < 15; attempt++) {
      try {
        result = await pythonAPI.getServerAddress(props.station.station_id)
        if (result?.success) break
        lastError = result?.error || 'Данные пока не готовы'
      } catch (e) {
        lastError = e?.message || 'Данные пока не готовы'
      }
      await new Promise(r => setTimeout(r, 1000))
    }

    if (lastError && !result?.success) {
      throw new Error(lastError)
    }

    currentServerAddress.value = result
    
    // Бэкенд кладет данные в connection.server_address_data как объект с полями address/port/heartbeat
    const addrObj = result?.server_address || {}
    const addressStr = addrObj.address || ''
    const portStr = addrObj.port || ''
    if (addressStr) {
      formData.value.server_address = addressStr
    }
    if (portStr) {
      const port = parseInt(String(portStr).split(':').pop(), 10)
      if (!Number.isNaN(port)) {
        formData.value.server_port = port
      }
    }
    if (addrObj.heartbeat_interval != null) {
      formData.value.heartbeat_interval = Number(addrObj.heartbeat_interval) || 30
    }
  } catch (err) {
    error.value = err.message || 'Ошибка загрузки настроек сервера'
    console.error('Ошибка загрузки адреса сервера:', err)
  } finally {
    isLoading.value = false
  }
}

const saveServerAddress = async () => {
  if (!props.station?.station_id || !isFormValid.value) return
  
  // Дополнительная проверка на пустой адрес
  const address = formData.value.server_address.trim()
  if (!address || address.length === 0) {
    error.value = 'Адрес сервера не может быть пустым'
    return
  }
  
  isSaving.value = true
  error.value = ''
  
  try {
    const result = await pythonAPI.setServerAddress({
      station_id: props.station.station_id,
      server_address: address,
      server_port: formData.value.server_port,
      heartbeat_interval: formData.value.heartbeat_interval
    })
    
    emit('address-updated', result)
    closeModal()
  } catch (err) {
    error.value = err.message || 'Ошибка сохранения настроек сервера'
    console.error('Ошибка сохранения адреса сервера:', err)
  } finally {
    isSaving.value = false
  }
}

const closeModal = () => {
  emit('close')
  // Сбрасываем состояние
  error.value = ''
  currentServerAddress.value = null
  formData.value = {
    server_address: '',
    server_port: 8080,
    heartbeat_interval: 30
  }
}
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
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #e0e0e0;
}

.modal-header h2 {
  margin: 0;
  color: #333;
  font-size: 1.5rem;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #666;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: all 0.2s;
}

.close-btn:hover {
  color: #333;
  background: #f5f5f5;
}

.modal-body {
  padding: 20px;
}

.loading-state {
  text-align: center;
  padding: 40px 20px;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-state {
  text-align: center;
  padding: 40px 20px;
}

.error-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.error-state p {
  color: #dc3545;
  margin-bottom: 20px;
}

.station-info {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 20px;
  border-left: 4px solid #667eea;
}

.station-info h3 {
  margin: 0 0 5px 0;
  color: #333;
  font-size: 1.1rem;
}

.station-org {
  margin: 0;
  color: #667eea;
  font-size: 0.9rem;
}

.server-address-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
}

.form-group label {
  font-weight: 600;
  color: #333;
  margin-bottom: 8px;
  font-size: 0.95rem;
}

.form-input {
  padding: 12px;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  font-size: 14px;
  transition: all 0.2s;
  background: white;
}

.form-input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.form-input:disabled {
  background-color: #f8f9fa;
  color: #6c757d;
  cursor: not-allowed;
}

.form-hint {
  color: #6c757d;
  font-size: 0.8rem;
  margin-top: 4px;
}

.current-info {
  background: #e3f2fd;
  padding: 15px;
  border-radius: 8px;
  border-left: 4px solid #2196f3;
}

.current-info h4 {
  margin: 0 0 12px 0;
  color: #1976d2;
  font-size: 0.95rem;
}

.current-details {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
}

.detail-label {
  font-size: 0.85rem;
  color: #666;
  font-weight: 500;
}

.detail-value {
  font-size: 0.85rem;
  color: #333;
  font-weight: 600;
  font-family: 'Courier New', monospace;
}

.form-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid #e0e0e0;
}

.btn {
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.2s;
  min-width: 120px;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: #667eea;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #5a6fd8;
  transform: translateY(-1px);
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background: #5a6268;
}

/* Мобильные стили */
@media (max-width: 768px) {
  .modal-content {
    width: 95%;
    margin: 10px;
  }
  
  .modal-header {
    padding: 15px;
  }
  
  .modal-body {
    padding: 15px;
  }
  
  .form-actions {
    flex-direction: column;
  }
  
  .btn {
    width: 100%;
  }
}
</style>
