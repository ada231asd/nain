<template>
  <div class="test-page">
    <h1>Тестирование компонента StationsTable</h1>


    <!-- Тестируемый компонент -->
    <StationsTable 
      :stations="stations"
      :items-per-page="10"
      @filter-stations="handleFilterStations"
      @view-powerbanks="handleViewPowerbanks"
      @edit-station="handleEditStation"
      @restart-station="handleRestartStation"
      @station-clicked="handleStationClicked"
    />

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import StationsTable from '../components/AdminComponents/StationsTable.vue'
import { useAdminStore } from '../stores/admin'

// Store
const adminStore = useAdminStore()

// Состояние
const stations = ref([])
const eventLog = ref([])

// Загрузка данных
const loadStations = async () => {
  try {
    await adminStore.fetchStations()
    stations.value = adminStore.stations
    logEvent(`Загружено станций: ${stations.value.length}`)
  } catch (error) {
    logEvent(`Ошибка загрузки станций: ${error.message}`)
  }
}

// Методы
const logEvent = (message) => {
  const timestamp = new Date().toLocaleTimeString()
  eventLog.value.unshift(`[${timestamp}] ${message}`)
  if (eventLog.value.length > 20) {
    eventLog.value.pop()
  }
}

// Обработчики событий компонента
const handleFilterStations = () => {
  logEvent('Событие: Фильтр станций')
}

const handleViewPowerbanks = (station) => {
  logEvent(`Событие: Просмотр павербанков станции ${station.box_id}`)
}

const handleEditStation = (station) => {
  logEvent(`Событие: Редактирование станции ${station.box_id}`)
}

const handleRestartStation = (station) => {
  logEvent(`Событие: Перезагрузка станции ${station.box_id}`)
}

const handleStationClicked = (station) => {
  logEvent(`Событие: Клик по станции ${station.box_id}`)
}

// Жизненный цикл
onMounted(() => {
  loadStations()
})
</script>

<style scoped>
.test-page {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.test-page h1 {
  color: #333;
  margin-bottom: 20px;
}

.test-controls {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.btn {
  padding: 10px 20px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.3s ease;
}

.btn:hover {
  background: #5a6fd8;
}

.test-info {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.test-info p {
  margin: 5px 0;
  color: #666;
}

.event-log {
  margin-top: 30px;
  background: #f8f9fa;
  border-radius: 8px;
  padding: 20px;
}

.event-log h3 {
  margin-top: 0;
  color: #333;
}

.log-entries {
  max-height: 300px;
  overflow-y: auto;
  background: white;
  border-radius: 6px;
  padding: 10px;
}

.log-entry {
  padding: 5px 0;
  border-bottom: 1px solid #eee;
  font-family: 'Courier New', monospace;
  font-size: 0.9rem;
  color: #666;
}

.log-entry:last-child {
  border-bottom: none;
}

@media (max-width: 768px) {
  .test-controls {
    flex-direction: column;
  }
  
  .btn {
    width: 100%;
  }
}
</style>
