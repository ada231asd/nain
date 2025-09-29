<template>
  <div v-if="isVisible" class="modal-overlay" @click="closeModal">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h2>Станции группы: {{ orgUnit?.name || 'Неизвестная группа' }}</h2>
        <button @click="closeModal" class="btn-close">×</button>
      </div>

      <div class="modal-body">
        <div v-if="isLoading" class="loading-state">
          <div class="loading-spinner"></div>
          <p>Загрузка станций...</p>
        </div>

        <div v-else-if="stations.length === 0" class="empty-state">
          <p>В этой группе нет станций</p>
        </div>

        <div v-else class="stations-list">
          <div 
            v-for="station in stations" 
            :key="station.station_id || station.id" 
            class="station-item"
            :class="getStationStatusClass(station.status)"
          >
            <div class="station-info">
              <div class="station-main">
                <h4 class="station-id">ID: {{ station.station_id || station.id }}</h4>
                <p class="station-box-id">Box ID: {{ station.box_id || 'N/A' }}</p>
                <p class="station-iccid">ICCID: {{ station.iccid || 'N/A' }}</p>
              </div>
              
              <div class="station-details">
                <div class="detail-item">
                  <span class="detail-label">Адрес ID:</span>
                  <span class="detail-value">{{ station.address_id || 'N/A' }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">Слотов:</span>
                  <span class="detail-value">{{ station.slots_declared || 'N/A' }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">Свободно:</span>
                  <span class="detail-value">{{ station.remain_num || 'N/A' }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">Последний сигнал:</span>
                  <span class="detail-value">{{ formatTime(station.last_seen) }}</span>
                </div>
              </div>
            </div>
            
            <div class="station-status">
              <span class="status-badge" :class="getStationStatusClass(station.status)">
                {{ getStationStatusText(station.status) }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <button @click="closeModal" class="btn-secondary">
          Закрыть
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
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

const emit = defineEmits(['close'])

const adminStore = useAdminStore()

const stations = ref([])
const isLoading = ref(false)

// Загрузка станций группы
const loadStations = async () => {
  if (!props.orgUnit?.org_unit_id) return
  
  isLoading.value = true
  try {
    const data = await adminStore.getOrgUnitStations(props.orgUnit.org_unit_id)
    stations.value = Array.isArray(data) ? data : []
  } catch (error) {
    stations.value = []
  } finally {
    isLoading.value = false
  }
}

// Получение CSS класса статуса станции
const getStationStatusClass = (status) => {
  switch (status) {
    case 'active':
      return 'status-active'
    case 'pending':
      return 'status-pending'
    case 'inactive':
      return 'status-inactive'
    case 'maintenance':
      return 'status-maintenance'
    default:
      return 'status-unknown'
  }
}

// Получение текста статуса станции
const getStationStatusText = (status) => {
  switch (status) {
    case 'active':
      return 'Активна'
    case 'pending':
      return 'Ожидает'
    case 'inactive':
      return 'Неактивна'
    case 'maintenance':
      return 'Сервис'
    default:
      return 'Неизвестно'
  }
}

// Форматирование времени
const formatTime = (timestamp) => {
  if (!timestamp) return '—'
  
  try {
    const date = new Date(timestamp)
    return date.toLocaleString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch (error) {
    return '—'
  }
}

// Закрытие модального окна
const closeModal = () => {
  stations.value = []
  emit('close')
}

// Отслеживание изменений видимости модального окна
watch(() => props.isVisible, (isVisible) => {
  if (isVisible && props.orgUnit) {
    loadStations()
  }
})

// Отслеживание изменений orgUnit
watch(() => props.orgUnit, (newOrgUnit) => {
  if (props.isVisible && newOrgUnit) {
    loadStations()
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
  max-width: 800px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
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

.modal-body {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #666;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: #666;
}

.stations-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.station-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
  border-left: 4px solid #6c757d;
}

.station-item.status-active {
  border-left-color: #28a745;
}

.station-item.status-pending {
  border-left-color: #ffc107;
}

.station-item.status-inactive {
  border-left-color: #dc3545;
}

.station-item.status-maintenance {
  border-left-color: #fd7e14;
}

.station-info {
  display: flex;
  gap: 20px;
  flex: 1;
}

.station-main {
  flex: 1;
}

.station-id {
  color: #333;
  margin: 0 0 8px 0;
  font-size: 1.1rem;
  font-weight: 600;
}

.station-box-id,
.station-iccid {
  color: #666;
  margin: 0 0 4px 0;
  font-size: 0.9rem;
}

.station-details {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 150px;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.85rem;
}

.detail-label {
  color: #666;
  font-weight: 500;
}

.detail-value {
  color: #333;
  font-weight: 600;
}

.station-status {
  margin-left: 20px;
}

.status-badge {
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
}

.status-active {
  background: #d4edda;
  color: #155724;
}

.status-pending {
  background: #fff3cd;
  color: #856404;
}

.status-inactive {
  background: #f8d7da;
  color: #721c24;
}

.status-maintenance {
  background: #ffeaa7;
  color: #856404;
}

.status-unknown {
  background: #e2e3e5;
  color: #383d41;
}

.modal-footer {
  padding: 20px 24px;
  border-top: 1px solid #e9ecef;
  display: flex;
  justify-content: flex-end;
}

.btn-secondary {
  padding: 12px 24px;
  background: #6c757d;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s;
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
  
  .modal-body {
    padding: 20px;
  }
  
  .modal-footer {
    padding: 16px 20px;
  }
  
  .station-item {
    flex-direction: column;
    gap: 15px;
  }
  
  .station-info {
    flex-direction: column;
    gap: 15px;
  }
  
  .station-details {
    flex-direction: row;
    flex-wrap: wrap;
    gap: 15px;
  }
  
  .detail-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 2px;
  }
  
  .station-status {
    margin-left: 0;
    align-self: flex-start;
  }
}
</style>
