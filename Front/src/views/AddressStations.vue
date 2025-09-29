<template>
  <div class="address-stations-container">
    <div class="address-header">
      <button @click="goBack" class="btn-back">
        ← Назад
      </button>
      <div class="address-info">
        <h1>{{ address.locationName }}</h1>
        <p class="address-text">{{ address.address }}</p>
        <div class="address-summary">
          <span class="summary-item">
            <strong>Станций:</strong> {{ address.totalStations }}
          </span>
          <span class="summary-item">
            <strong>Всего портов:</strong> {{ address.totalPorts }}
          </span>
          <span class="summary-item">
            <strong>Свободных:</strong> {{ address.availablePorts }}
          </span>
        </div>
      </div>
    </div>

    <div class="stations-content">
      <!-- Список станций -->
      <div class="stations-section">
        <h2>🔌 Станции по адресу</h2>
        <div class="stations-grid">
          <div 
            v-for="station in stations" 
            :key="station.id"
            class="station-card"
            :class="`station-${station.status}`"
          >
            <div class="station-header">
              <h3>{{ station.name }}</h3>
              <span class="station-status" :class="`status-${station.status}`">
                {{ getStationStatusText(station.status) }}
              </span>
            </div>
            
            <div class="station-location">
              <p><strong>Расположение:</strong> {{ station.location }}</p>
            </div>
            
            <div class="station-ports-info">
              <div class="port-counts">
                <span class="port-count available">
                  <strong>{{ station.availablePorts }}</strong> на выдачу
                </span>
                <span class="port-count occupied">
                  <strong>{{ station.occupiedPorts }}</strong> на возврат
                </span>
              </div>
            </div>

            <div class="station-actions">
              <button 
                v-if="station.availablePorts > 0"
                @click="takeBattery(station)"
                class="btn-action btn-take"
                :disabled="isLoading"
              >
                🔋 Взять аккумулятор
              </button>
              
              <button 
                v-if="station.occupiedPorts > 0"
                @click="returnBattery(station)"
                class="btn-action btn-return"
                :disabled="isLoading"
              >
                🔌 Вернуть аккумулятор
              </button>
              
              <button 
                v-if="station.availablePorts === 0 && station.occupiedPorts === 0"
                class="btn-action btn-disabled"
                disabled
              >
                ⚠️ Станция неактивна
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Быстрые действия -->
      <div class="quick-actions">
        <h2>⚡ Быстрые действия</h2>
        <div class="action-buttons">
          <button @click="refreshStations" class="btn-action btn-refresh" :disabled="isLoading">
            🔄 Обновить статус
          </button>
          <button @click="goToQRScanner" class="btn-action btn-qr">
            📱 Сканировать QR
          </button>
          <button @click="goToDashboard" class="btn-action btn-dashboard">
            🏠 На главную
          </button>
        </div>
      </div>
    </div>

    <!-- Модальное окно для подтверждения действий -->
    <div v-if="showConfirmModal" class="modal-overlay" @click="closeModal">
      <div class="modal-content" @click.stop>
        <h3>{{ modalTitle }}</h3>
        <p>{{ modalMessage }}</p>
        <div class="modal-actions">
          <button @click="confirmAction" class="btn-confirm" :disabled="isLoading">
            {{ isLoading ? 'Выполняется...' : 'Подтвердить' }}
          </button>
          <button @click="closeModal" class="btn-cancel">
            Отмена
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

// Состояние
const isLoading = ref(false)
const showConfirmModal = ref(false)
const modalTitle = ref('')
const modalMessage = ref('')
const currentAction = ref(null)
const currentStation = ref(null)

// Данные адреса
const address = ref({
  id: 1,
  locationName: 'ТЦ "Мегамолл"',
  address: 'ул. Ленина, 123',
  totalStations: 5,
  totalPorts: 20,
  availablePorts: 8
})

// База данных всех адресов и их станций
const addressesData = {
  1: {
    id: 1,
    locationName: 'ТЦ "Мегамолл"',
    address: 'ул. Ленина, 123',
    totalStations: 5,
    totalPorts: 20,
    availablePorts: 8,
    stations: [
      {
        id: 1,
        name: 'Станция ST001',
        location: 'Вкусно и точка, 3 этаж',
        status: 'active',
        availablePorts: 1,
        occupiedPorts: 3
      },
      {
        id: 2,
        name: 'Станция ST002',
        location: 'Магазин "Пятёрочка", 1 этаж',
        status: 'active',
        availablePorts: 2,
        occupiedPorts: 1
      },
      {
        id: 3,
        name: 'Станция ST003',
        location: 'Кафе "Бургер Кинг", 2 этаж',
        status: 'active',
        availablePorts: 0,
        occupiedPorts: 4
      },
      {
        id: 4,
        name: 'Станция ST004',
        location: 'Аптека "36.6", 1 этаж',
        status: 'maintenance',
        availablePorts: 0,
        occupiedPorts: 0
      },
      {
        id: 5,
        name: 'Станция ST005',
        location: 'Банк "Сбербанк", 1 этаж',
        status: 'active',
        availablePorts: 3,
        occupiedPorts: 2
      }
    ]
  },
  2: {
    id: 2,
    locationName: 'Бизнес-центр "Современник"',
    address: 'пр. Мира, 45',
    totalStations: 3,
    totalPorts: 12,
    availablePorts: 3,
    stations: [
      {
        id: 6,
        name: 'Станция ST006',
        location: 'Офис 101, 1 этаж',
        status: 'active',
        availablePorts: 1,
        occupiedPorts: 2
      },
      {
        id: 7,
        name: 'Станция ST007',
        location: 'Конференц-зал, 2 этаж',
        status: 'active',
        availablePorts: 2,
        occupiedPorts: 1
      },
      {
        id: 8,
        name: 'Станция ST008',
        location: 'Столовая, 1 этаж',
        status: 'active',
        availablePorts: 0,
        occupiedPorts: 3
      }
    ]
  },
  3: {
    id: 3,
    locationName: 'ТРК "Галерея"',
    address: 'ул. Пушкина, 67',
    totalStations: 4,
    totalPorts: 16,
    availablePorts: 0,
    stations: [
      {
        id: 9,
        name: 'Станция ST009',
        location: 'Кинотеатр, 3 этаж',
        status: 'maintenance',
        availablePorts: 0,
        occupiedPorts: 0
      },
      {
        id: 10,
        name: 'Станция ST010',
        location: 'Ресторан "У Пушкина", 2 этаж',
        status: 'maintenance',
        availablePorts: 0,
        occupiedPorts: 0
      },
      {
        id: 11,
        name: 'Станция ST011',
        location: 'Детская площадка, 1 этаж',
        status: 'maintenance',
        availablePorts: 0,
        occupiedPorts: 0
      },
      {
        id: 12,
        name: 'Станция ST012',
        location: 'Парковка, подземный этаж',
        status: 'maintenance',
        availablePorts: 0,
        occupiedPorts: 0
      }
    ]
  }
}

// Список станций по адресу
const stations = ref([])

// Вычисляемые свойства
const totalAvailablePorts = computed(() => {
  return stations.value.reduce((sum, station) => sum + station.availablePorts, 0)
})

const totalOccupiedPorts = computed(() => {
  return stations.value.reduce((sum, station) => sum + station.occupiedPorts, 0)
})

// Методы
const goBack = () => {
  router.go(-1)
}

const goToDashboard = () => {
  router.push('/dashboard')
}

const goToQRScanner = () => {
  router.push('/qr-scanner')
}

const refreshStations = async () => {
  isLoading.value = true
  try {
    // Имитируем обновление данных
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    // Обновляем общее количество свободных портов
    address.value.availablePorts = totalAvailablePorts.value
    
    // Обновляем данные в базе
    if (addressesData[address.value.id]) {
      addressesData[address.value.id].availablePorts = totalAvailablePorts.value
    }
    
    alert('✅ Статус станций обновлен!')
  } catch (error) {
    alert('❌ Ошибка при обновлении статуса')
  } finally {
    isLoading.value = false
  }
}

const takeBattery = (station) => {
  currentAction.value = 'take'
  currentStation.value = station
  modalTitle.value = 'Взять аккумулятор'
  modalMessage.value = `Взять аккумулятор из станции "${station.name}"?`
  showConfirmModal.value = true
}

const returnBattery = (station) => {
  currentAction.value = 'return'
  currentStation.value = station
  modalTitle.value = 'Вернуть аккумулятор'
  modalMessage.value = `Вернуть аккумулятор в станцию "${station.name}"?`
  showConfirmModal.value = true
}

const confirmAction = async () => {
  if (!currentAction.value || !currentStation.value) return
  
  isLoading.value = true
  
  try {
    switch (currentAction.value) {
      case 'take':
        await takeBatteryAction()
        break
      case 'return':
        await returnBatteryAction()
        break
    }
    
    closeModal()
    alert('✅ Действие выполнено успешно!')
  } catch (error) {
    alert('❌ Ошибка при выполнении действия')
  } finally {
    isLoading.value = false
  }
}

const takeBatteryAction = async () => {
  // Имитируем задержку
  await new Promise(resolve => setTimeout(resolve, 1500))
  
  // Обновляем количество портов
  currentStation.value.availablePorts--
  currentStation.value.occupiedPorts++
  
  // Обновляем общее количество свободных портов
  address.value.availablePorts = totalAvailablePorts.value
  
  // Обновляем данные в базе
  if (addressesData[address.value.id]) {
    addressesData[address.value.id].availablePorts = totalAvailablePorts.value
  }
}

const returnBatteryAction = async () => {
  // Имитируем задержку
  await new Promise(resolve => setTimeout(resolve, 1000))
  
  // Обновляем количество портов
  currentStation.value.occupiedPorts--
  currentStation.value.availablePorts++
  
  // Обновляем общее количество свободных портов
  address.value.availablePorts = totalAvailablePorts.value
  
  // Обновляем данные в базе
  if (addressesData[address.value.id]) {
    addressesData[address.value.id].availablePorts = totalAvailablePorts.value
  }
}

const closeModal = () => {
  showConfirmModal.value = false
  currentAction.value = null
  currentStation.value = null
}

const getStationStatusText = (status) => {
  const statusMap = {
    'active': 'Работает',
    'maintenance': 'Обслуживание',
    'inactive': 'Не работает'
  }
  return statusMap[status] || status
}

onMounted(() => {
  // Получаем ID адреса из маршрута
  const addressId = parseInt(route.params.id)
  
  // В реальном приложении здесь был бы запрос к API

  // Загружаем данные для выбранного адреса
  if (addressesData[addressId]) {
    const selectedAddress = addressesData[addressId]
    
    // Обновляем данные адреса
    address.value = {
      id: selectedAddress.id,
      locationName: selectedAddress.locationName,
      address: selectedAddress.address,
      totalStations: selectedAddress.totalStations,
      totalPorts: selectedAddress.totalPorts,
      availablePorts: selectedAddress.availablePorts
    }
    
    // Загружаем станции для этого адреса
    stations.value = selectedAddress.stations
  } else {
    alert('❌ Адрес не найден')
    router.push('/dashboard')
  }
})
</script>

<style scoped>
.address-stations-container {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.address-header {
  display: flex;
  align-items: flex-start;
  gap: 20px;
  margin-bottom: 30px;
  padding: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 20px;
  color: white;
}

.btn-back {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: none;
  padding: 10px 15px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1rem;
  transition: background-color 0.3s ease;
  white-space: nowrap;
}

.btn-back:hover {
  background: rgba(255, 255, 255, 0.3);
}

.address-info {
  flex: 1;
}

.address-info h1 {
  margin: 0 0 10px 0;
  font-size: 2.5rem;
  color: white;
}

.address-text {
  margin: 0 0 15px 0;
  font-size: 1.2rem;
  opacity: 0.9;
  color: white;
}

.address-summary {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
}

.summary-item {
  background: rgba(255, 255, 255, 0.2);
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 0.9rem;
}

.summary-item strong {
  color: #ffd700;
}

.stations-content {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

/* Секция станций */
.stations-section h2 {
  color: #333;
  margin-bottom: 25px;
  text-align: center;
  font-size: 1.8rem;
}

.stations-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 20px;
}

.station-card {
  background: white;
  border: 2px solid #e9ecef;
  border-radius: 15px;
  padding: 25px;
  transition: all 0.3s ease;
}

.station-active {
  border-color: #28a745;
  background: #f8fff9;
}

.station-maintenance {
  border-color: #ffc107;
  background: #fffdf8;
}

.station-inactive {
  border-color: #dc3545;
  background: #fff8f8;
}

.station-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.station-header h3 {
  color: #333;
  margin: 0;
  font-size: 1.3rem;
}

.station-status {
  padding: 6px 12px;
  border-radius: 15px;
  font-size: 0.8rem;
  font-weight: 500;
}

.station-status.status-active {
  background: #d4edda;
  color: #155724;
}

.station-status.status-maintenance {
  background: #fff3cd;
  color: #856404;
}

.station-status.status-inactive {
  background: #f8d7da;
  color: #721c24;
}

.station-location p {
  margin: 8px 0;
  color: #666;
  font-size: 1rem;
}

.station-ports-info {
  margin: 20px 0;
}

.port-counts {
  display: flex;
  gap: 15px;
  justify-content: center;
}

.port-count {
  padding: 10px 15px;
  border-radius: 10px;
  font-size: 0.9rem;
  text-align: center;
}

.port-count.available {
  background: #d4edda;
  color: #155724;
}

.port-count.occupied {
  background: #fff3cd;
  color: #856404;
}

.port-count strong {
  display: block;
  font-size: 1.2rem;
  margin-bottom: 2px;
}

.station-actions {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.btn-action {
  padding: 12px 20px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.3s ease;
}

.btn-action:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-take {
  background: #28a745;
  color: white;
}

.btn-take:hover:not(:disabled) {
  background: #218838;
}

.btn-return {
  background: #17a2b8;
  color: white;
}

.btn-return:hover:not(:disabled) {
  background: #138496;
}

.btn-disabled {
  background: #6c757d;
  color: white;
}

/* Быстрые действия */
.quick-actions {
  background: white;
  padding: 30px;
  border-radius: 15px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
}

.quick-actions h2 {
  color: #333;
  margin-bottom: 25px;
  text-align: center;
  font-size: 1.8rem;
}

.action-buttons {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.btn-refresh {
  background: #6c757d;
  color: white;
}

.btn-refresh:hover:not(:disabled) {
  background: #5a6268;
}

.btn-qr {
  background: #667eea;
  color: white;
}

.btn-qr:hover {
  background: #5a6fd8;
}

.btn-dashboard {
  background: #17a2b8;
  color: white;
}

.btn-dashboard:hover {
  background: #138496;
}

/* Модальное окно */
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
  padding: 30px;
  border-radius: 15px;
  min-width: 400px;
  max-width: 500px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
}

.modal-content h3 {
  color: #333;
  margin-bottom: 15px;
  text-align: center;
}

.modal-content p {
  color: #666;
  margin-bottom: 25px;
  text-align: center;
  line-height: 1.5;
}

.modal-actions {
  display: flex;
  gap: 15px;
  justify-content: center;
}

.btn-confirm,
.btn-cancel {
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1rem;
  transition: background-color 0.2s ease;
}

.btn-confirm {
  background: #28a745;
  color: white;
}

.btn-confirm:hover:not(:disabled) {
  background: #218838;
}

.btn-cancel {
  background: #6c757d;
  color: white;
}

.btn-cancel:hover {
  background: #5a6268;
}

/* Мобильные стили */
@media (max-width: 768px) {
  .address-stations-container {
    padding: 15px;
  }
  
  .address-header {
    flex-direction: column;
    text-align: center;
    gap: 15px;
  }
  
  .address-info h1 {
    font-size: 2rem;
  }
  
  .address-summary {
    justify-content: center;
  }
  
  .stations-grid {
    grid-template-columns: 1fr;
  }
  
  .port-counts {
    flex-direction: column;
    gap: 10px;
  }
  
  .action-buttons {
    grid-template-columns: 1fr;
  }
  
  .modal-content {
    min-width: 90vw;
    margin: 20px;
  }
}
</style>
