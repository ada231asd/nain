<template>
  <div v-if="isVisible" class="modal-overlay" @click="$emit('close')">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h2>Активация станции</h2>
        <button class="btn-close" @click="$emit('close')">&times;</button>
      </div>
      
      <div class="form">
        <div class="station-info">
          <h3>Станция: {{ station?.box_id || 'N/A' }}</h3>
          <p class="station-details">
            <span v-if="station?.org_unit_name">Организация: {{ station.org_unit_name }}</span>
            <span v-if="station?.slots_declared">Слотов: {{ station.slots_declared }}</span>
          </p>
        </div>
        
        <div class="form-group">
          <label>Секретный ключ *</label>
          <input 
            v-model="secretKey" 
            placeholder="Введите секретный ключ" 
            class="input" 
            type="password"
            required 
          />
        </div>
        
        <div class="form-group">
          <label>Группа/Подгруппа *</label>
          <select v-model="orgUnitId" class="input" required>
            <option value="">Выберите группу/подгруппу</option>
            <option v-for="orgUnit in orgUnits" :key="orgUnit.org_unit_id" :value="orgUnit.org_unit_id">
              {{ orgUnit.name }}
            </option>
          </select>
        </div>
        
        <div class="warning-message">
          <p>⚠️ Для активации станции необходимо указать секретный ключ и назначить группу/подгруппу.</p>
        </div>
      </div>
      
      <div class="actions">
        <button 
          class="btn-primary" 
          @click="activateStation" 
          :disabled="!isFormValid || isLoading"
        >
          <span v-if="isLoading">Активация...</span>
          <span v-else>Активировать станцию</span>
        </button>
        <button class="btn-secondary" @click="$emit('close')" :disabled="isLoading">
          Отмена
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useAdminStore } from '../stores/admin'
import { pythonAPI } from '../api/pythonApi'

const props = defineProps({
  isVisible: { type: Boolean, default: false },
  station: { type: Object, default: null }
})

const emit = defineEmits(['close', 'station-activated'])

const adminStore = useAdminStore()

const secretKey = ref('')
const orgUnitId = ref(null)
const isLoading = ref(false)

const orgUnits = computed(() => adminStore.orgUnits)

const isFormValid = computed(() => {
  return secretKey.value.trim() && orgUnitId.value
})

watch(
  () => props.station,
  (station) => {
    if (station) {
      // Сбрасываем форму при смене станции
      secretKey.value = ''
      orgUnitId.value = null
    }
  },
  { immediate: true }
)

const activateStation = async () => {
  if (!isFormValid.value || !props.station) return
  
  isLoading.value = true
  
  try {
    const stationId = props.station.station_id || props.station.id
    
    // Сначала создаем секретный ключ для станции
    await pythonAPI.createStationSecretKey({
      station_id: stationId,
      key_value: secretKey.value.trim()
    })
    
    // Затем обновляем статус станции на "active" и назначаем группу
    await adminStore.updateStation(stationId, {
      status: 'active',
      org_unit_id: orgUnitId.value
    })
    
    // Уведомляем родительский компонент об успешной активации
    emit('station-activated', {
      stationId,
      secretKey: secretKey.value.trim(),
      orgUnitId: orgUnitId.value
    })
    
    // Закрываем модальное окно
    emit('close')
    
  } catch (error) {
    // Error handled with alert below
    alert('Ошибка активации станции: ' + (error.message || 'Неизвестная ошибка'))
  } finally {
    isLoading.value = false
  }
}

onMounted(async () => {
  // Загружаем организационные единицы если они еще не загружены
  if (orgUnits.value.length === 0) {
    await adminStore.fetchOrgUnits()
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
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
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
  padding: 4px;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.btn-close:hover {
  color: #333;
  background: #f8f9fa;
}

.form {
  padding: 24px;
}

.station-info {
  background: #f8f9fa;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 24px;
  border-left: 4px solid #667eea;
}

.station-info h3 {
  margin: 0 0 8px 0;
  color: #333;
  font-size: 1.2rem;
}

.station-details {
  margin: 0;
  color: #666;
  font-size: 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  color: #333;
  font-weight: 500;
  font-size: 14px;
}

.input {
  width: 100%;
  padding: 12px 16px;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  font-size: 14px;
  transition: border-color 0.2s ease;
  box-sizing: border-box;
}

.input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.input:invalid {
  border-color: #dc3545;
}

.warning-message {
  background: #fff3cd;
  border: 1px solid #ffeaa7;
  border-radius: 8px;
  padding: 12px 16px;
  margin-top: 16px;
}

.warning-message p {
  margin: 0;
  color: #856404;
  font-size: 14px;
  line-height: 1.4;
}

.actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  padding: 20px 24px;
  border-top: 1px solid #e9ecef;
  background: #f8f9fa;
}

.btn-primary {
  padding: 12px 24px;
  background: #28a745;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: background-color 0.2s ease;
  min-width: 140px;
}

.btn-primary:hover:not(:disabled) {
  background: #218838;
}

.btn-primary:disabled {
  background: #6c757d;
  cursor: not-allowed;
}

.btn-secondary {
  padding: 12px 24px;
  background: #6c757d;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: background-color 0.2s ease;
}

.btn-secondary:hover:not(:disabled) {
  background: #5a6268;
}

.btn-secondary:disabled {
  background: #adb5bd;
  cursor: not-allowed;
}

/* Mobile styles */
@media (max-width: 768px) {
  .modal-content {
    width: 95%;
    margin: 20px;
  }
  
  .modal-header {
    padding: 16px 20px;
  }
  
  .form {
    padding: 20px;
  }
  
  .actions {
    padding: 16px 20px;
    flex-direction: column;
  }
  
  .btn-primary,
  .btn-secondary {
    width: 100%;
  }
}
</style>
