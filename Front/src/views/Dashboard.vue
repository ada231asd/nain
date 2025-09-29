<template>
  <DefaultLayout title="Главная">
    <div class="dashboard-content">
      <!-- Поиск станций -->
      <div class="search-section">
        <div class="search-input-wrapper">
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Поиск станций..."
            class="search-input"
            @input="handleSearch"
          />
        </div>
      </div>

      <!-- Избранные станции -->
      <section class="favorites-section">
        <div class="section-header">
          <h2>Избранные станции</h2>
          
        </div>
        
        <div v-if="favoriteStations.length === 0" class="empty-state">
          <p>У вас пока нет избранных станций</p>
          <button @click="showQRScanner = true" class="btn-primary">
            Добавить станцию
          </button>
        </div>
        
        <div v-else class="stations-grid">
          <StationCard
            v-for="station in favoriteStations"
            :key="station.station_id"
            :station="station"
            :isFavorite="true"
            :showFavoriteButton="true"
            :showTakeBatteryButton="true"
            @toggleFavorite="toggleFavorite"
            @takeBattery="handleTakeBattery"
          />
        </div>
      </section>

      <!-- Результат сканирования: показ карточки станции -->
      <section v-if="scannedStation" class="scanned-station-section">
        <h2>Найденная станция</h2>
        <StationCard
          :station="scannedStation"
          :isFavorite="isStationFavorite(scannedStation)"
          :showFavoriteButton="true"
          :showTakeBatteryButton="true"
          @toggleFavorite="toggleFavorite"
          @takeBattery="handleTakeBattery"
        />
      </section>

      <div v-if="scanningError" class="scan-error">
        {{ scanningError }}
      </div>

      <!-- Быстрые действия -->
      <section class="quick-actions">
        <h2>Быстрые действия</h2>
        <div class="actions-grid">
          <button @click="showQRScanner = true" class="action-btn">
            <span class="action-icon">📱</span>
            <span>Сканировать QR</span>
          </button>
          <button @click="goToAdmin" v-if="isAdmin" class="action-btn">
            <span class="action-icon">⚙️</span>
            <span>Админ панель</span>
          </button>
        </div>
      </section>

    </div>

    <!-- QR Scanner Modal -->
    <QRScanner 
      v-if="showQRScanner" 
      @close="closeQRScanner"
      @scan="handleQRScan"
    />
  </DefaultLayout>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useStationsStore } from '../stores/stations'
import { useAuthStore } from '../stores/auth'
import DefaultLayout from '../layouts/DefaultLayout.vue'
import QRScanner from '../components/QRScanner.vue'
import StationCard from '../components/StationCard.vue'
import { pythonAPI } from '../api/pythonApi'

const router = useRouter()
const stationsStore = useStationsStore()
const auth = useAuthStore()

// Состояние
const searchQuery = ref('')
const showQRScanner = ref(false)
const searchTimeout = ref(null)
const scannedStation = ref(null)
const isScanning = ref(false)
const scanningError = ref('')

// Автоматическое обновление данных
const autoRefreshInterval = ref(null)
const autoRefreshEnabled = ref(true)
const refreshInterval = 30000 // 30 секунд

// Вычисляемые свойства
const user = computed(() => auth.user)
const isLoading = computed(() => stationsStore.isLoading)
const favoriteStations = computed(() => stationsStore.favoriteStations)
const isAdmin = computed(() => auth.user?.role?.includes('admin') || false)

// Отладочная информация
console.log('User в Dashboard:', user.value)
console.log('User ID:', user.value?.user_id)

const refreshFavorites = async () => {
  try {
    await stationsStore.fetchFavoriteStations(user.value?.user_id)
  } catch (err) {
    // Error handled silently
  }
}

// Функции автоматического обновления данных
const startAutoRefresh = () => {
  if (autoRefreshInterval.value) {
    clearInterval(autoRefreshInterval.value)
  }
  
  if (autoRefreshEnabled.value) {
    autoRefreshInterval.value = setInterval(async () => {
      try {
        await refreshFavorites()
      } catch (error) {
        console.warn('Ошибка при автоматическом обновлении избранных станций:', error)
      }
    }, refreshInterval)
  }
}

const stopAutoRefresh = () => {
  if (autoRefreshInterval.value) {
    clearInterval(autoRefreshInterval.value)
    autoRefreshInterval.value = null
  }
}

// Обновление данных после действий
const refreshAfterAction = async () => {
  try {
    await refreshFavorites()
  } catch (error) {
    console.warn('Ошибка при обновлении данных после действия:', error)
  }
}

const removeFromFavorites = async (stationId) => {
  try {
    await stationsStore.removeFavorite(user.value?.user_id, stationId)
  } catch (err) {
    // Error handled silently
  }
}

const isStationFavorite = (station) => {
  if (!station) return false
  const stationId = station.station_id || station.id
  return favoriteStations.value.some(fav => (fav.station_id || fav.id) === stationId)
}

const toggleFavorite = async (station) => {
  try {
    const stationId = station.station_id || station.id
    console.log('Toggle favorite для станции:', station);
    console.log('Station ID:', stationId);
    console.log('User ID:', user.value?.user_id);
    console.log('Is favorite:', isStationFavorite(station));
    
    if (isStationFavorite(station)) {
      console.log('Удаляем из избранного');
      await stationsStore.removeFavorite(user.value?.user_id, stationId)
    } else {
      console.log('Добавляем в избранное');
      await stationsStore.addFavorite(user.value?.user_id, stationId)
      
      // Если это отсканированная станция, скрываем секцию "Найденная станция"
      if (scannedStation.value && (scannedStation.value.station_id || scannedStation.value.id) === stationId) {
        console.log('Скрываем секцию найденной станции после добавления в избранное');
        scannedStation.value = null
      }
    }
    
    // Автоматическое обновление данных
    await refreshAfterAction()
  } catch (err) {
    console.error('Ошибка в toggleFavorite:', err);
  }
}

const handleTakeBattery = async (station) => {
  try {
    const stationId = station.station_id || station.id
    const userId = user.value?.user_id
    
    if (!stationId) {
      console.error('Отсутствует ID станции')
      return
    }
    
    if (!userId) {
      console.error('Отсутствует ID пользователя')
      return
    }
    
    console.log('Запрос на взятие аккумулятора:', { stationId, userId })
    
    // Вызываем новый API метод для оптимального выбора аккумулятора
    const response = await pythonAPI.requestOptimalBorrowPowerbank({
      station_id: stationId,
      user_id: userId
    })
    
    console.log('Ответ API:', response)
    
    // Здесь можно добавить уведомление об успехе
    alert('Запрос на взятие аккумулятора отправлен успешно!')
    
    // Автоматическое обновление данных
    await refreshAfterAction()
    
  } catch (error) {
    console.error('Ошибка при запросе аккумулятора:', error)
    alert('Ошибка при запросе аккумулятора: ' + (error.message || 'Неизвестная ошибка'))
  }
}



const goToAdmin = () => {
  router.push('/admin')
}

const handleSearch = () => {
  // Очищаем предыдущий таймаут
  if (searchTimeout.value) {
    clearTimeout(searchTimeout.value)
  }
  
  // Устанавливаем новый таймаут для поиска
  searchTimeout.value = setTimeout(async () => {
    if (searchQuery.value.trim()) {
      try {
        await stationsStore.searchStations(searchQuery.value.trim())
      } catch (err) {
        // Error handled silently
      }
    }
  }, 500)
}

const closeQRScanner = () => {
  showQRScanner.value = false
}

const extractStationCode = (input) => {
  try {
    if (!input) return ''
    const raw = typeof input === 'string' ? input : (input.rawValue || '')
    if (!raw) return ''
    
    console.log('Исходный QR код:', raw)
    
    // Берем последнюю часть после слеша, например https://.../DCHEY02504000019
    const lastSegment = raw.split('/').filter(Boolean).pop() || ''
    console.log('Последний сегмент:', lastSegment)
    
    // Оставляем только буквы/цифры в верхнем регистре
    const cleaned = lastSegment.trim().toUpperCase()
    console.log('Очищенный код:', cleaned)
    
    return cleaned
  } catch (e) {
    console.error('Ошибка извлечения кода:', e)
    return ''
  }
}

const handleQRScan = async (payload) => {
  const code = extractStationCode(payload)
  if (!code) {
    scanningError.value = 'Не удалось распознать код станции'
    return
  }

  console.log('QR код извлечен:', code)

  isScanning.value = true
  scanningError.value = ''
  scannedStation.value = null
  try {
    // 1) Пробуем точечный поиск по box_id (правильный параметр API)
    let station = null
    try {
      const response = await pythonAPI.getStations({ box_id: code })
      console.log('Ответ API с фильтром box_id:', response)

      // Извлекаем массив из ответа API
      const stationsArray = response?.data || response || []
      if (Array.isArray(stationsArray) && stationsArray.length > 0) {
        // Берем только точное совпадение по box_id
        const matched = stationsArray.find(s => {
          const boxId = s.box_id || s.station_box_id
          return boxId && String(boxId).toUpperCase() === code
        })
        if (matched) {
          station = matched
          console.log('Найдена станция через фильтр (точное совпадение):', station)
        } else {
          console.log('Ответ API с фильтром не содержит точного совпадения по box_id')
        }
      } else if (response && !Array.isArray(response)) {
        // Если пришел объект, проверяем точное совпадение
        const one = response?.data || response
        const boxId = one?.box_id || one?.station_box_id
        if (boxId && String(boxId).toUpperCase() === code) {
          station = one
          console.log('Найдена станция (объект, точное совпадение):', station)
        }
      }
    } catch (error) {
      console.log('Ошибка при поиске по box_id:', error)
      // игнорируем и идем на полную выборку
    }

    // 2) Фолбэк: загружаем список и ищем по box_id
    if (!station) {
      console.log('Поиск по полному списку станций...')
      const response = await pythonAPI.getStations()
      console.log('Полный ответ API:', response)

      // Извлекаем массив из ответа API
      const stationsArray = response?.data || response || []
      
      if (Array.isArray(stationsArray)) {
        console.log('Ищем среди', stationsArray.length, 'станций')
        station = stationsArray.find(s => {
          // Ищем только по box_id, так как это основное поле для идентификации
          const boxId = s.box_id || s.station_box_id
          const match = boxId && String(boxId).toUpperCase() === code
          if (match) {
            console.log('Найдено совпадение:', s)
          }
          return match
        }) || null
      } else {
        // Если data не массив, а объект
        const stationData = response?.data || response
        if (stationData) {
          const boxId = stationData.box_id || stationData.station_box_id
          if (boxId && String(boxId).toUpperCase() === code) {
            station = stationData
            console.log('Найдена станция (объект):', station)
          }
        }
      }
    }

    if (!station) {
      scanningError.value = `Станция с кодом ${code} не найдена`
      console.log('Станция не найдена для кода:', code)
      return
    }

    console.log('Найденная станция:', station)

    // 3) Загружаем актуальные детали станции через store
    let detailed = station
    if (station && (station.station_id || station.id)) {
      try {
        const stationId = station.station_id || station.id
        console.log('Обновляем данные станции ID:', stationId)
        detailed = await stationsStore.refreshStationData(stationId)
        console.log('Обновленные данные станции:', detailed)
      } catch (error) {
        console.log('Ошибка обновления через store:', error)
        // Если не удалось обновить через store, пробуем напрямую через API
        try {
          const stationId = station.station_id || station.id
          detailed = await pythonAPI.getStation(stationId)
          console.log('Данные станции через API:', detailed)
        } catch (apiError) {
          console.log('Ошибка получения через API:', apiError)
          // оставляем исходные данные станции
        }
      }
    }

    // Проверяем, нужно ли извлечь данные из структуры API
    if (detailed && detailed.success && detailed.data) {
      detailed = detailed.data
      console.log('Извлечены данные из API структуры:', detailed)
    }

    scannedStation.value = detailed
    console.log('Финальная станция для отображения:', scannedStation.value)
  } catch (error) {
    console.error('Ошибка при обработке QR:', error)
    scanningError.value = 'Произошла ошибка при обработке QR-кода'
  } finally {
    isScanning.value = false
    showQRScanner.value = false
  }
}

const getStatusClass = (status) => {
  switch (status) {
    case 'active': return 'status-active'
    case 'inactive': return 'status-inactive'
    case 'maintenance': return 'status-maintenance'
    default: return 'status-unknown'
  }
}

const getStatusText = (status) => {
  switch (status) {
    case 'active': return 'Активна'
    case 'inactive': return 'Неактивна'
    case 'maintenance': return 'Обслуживание'
    default: return 'Неизвестно'
  }
}

const getAvailablePorts = (station) => {
  return station.freePorts || 0
}

const getTotalPorts = (station) => {
  return station.totalPorts || 0
}

const formatTime = (timestamp) => {
  const date = new Date(timestamp)
  return date.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// Жизненный цикл
onMounted(async () => {
  try {
    console.log('onMounted: загружаем избранное для user_id:', user.value?.user_id)
    await stationsStore.fetchFavoriteStations(user.value?.user_id)
    
    // Запускаем автоматическое обновление
    startAutoRefresh()
  } catch (err) {
    console.error('Ошибка при загрузке избранного:', err)
  }
})

onUnmounted(() => {
  if (searchTimeout.value) {
    clearTimeout(searchTimeout.value)
  }
  
  // Останавливаем автоматическое обновление
  stopAutoRefresh()
})
</script>

<style scoped>
.dashboard-content {
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}

.search-section {
  margin-bottom: 30px;
}

.search-input-wrapper {
  display: flex;
  gap: 10px;
}

.search-input {
  flex: 1;
  padding: 15px;
  border: 2px solid #e9ecef;
  border-radius: 10px;
  font-size: 1rem;
  transition: border-color 0.3s ease;
}

.search-input:focus {
  outline: none;
  border-color: #667eea;
}

.btn-qr-search {
  padding: 15px 20px;
  background: #17a2b8;
  color: white;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.btn-qr-search:hover {
  background: #138496;
}

.favorites-section {
  margin-bottom: 40px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.section-header h2 {
  color: #333;
  font-size: 1.5rem;
  margin: 0;
}

.btn-refresh {
  padding: 10px;
  background: #6c757d;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.btn-refresh:hover:not(:disabled) {
  background: #5a6268;
}

.btn-refresh:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.empty-state {
  text-align: center;
  padding: 40px;
  background: white;
  border-radius: 15px;
  border: 2px dashed #dee2e6;
}

.empty-state p {
  color: #666;
  margin-bottom: 20px;
  font-size: 1.1rem;
}

.stations-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.station-card {
  background: white;
  border-radius: 15px;
  padding: 20px;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
  cursor: pointer;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  position: relative;
}

.station-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
}

.station-info h3 {
  color: #333;
  margin: 0 0 10px 0;
  font-size: 1.2rem;
}

.station-code {
  color: #667eea;
  font-weight: 600;
  margin: 0 0 5px 0;
  font-size: 0.9rem;
}

.station-address {
  color: #666;
  margin: 0;
  font-size: 0.9rem;
}

.station-status {
  margin-top: 15px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status-indicator {
  padding: 5px 12px;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
}

.status-active {
  background: #d4edda;
  color: #155724;
}

.status-inactive {
  background: #f8d7da;
  color: #721c24;
}

.status-maintenance {
  background: #fff3cd;
  color: #856404;
}

.status-unknown {
  background: #e2e3e5;
  color: #383d41;
}

.ports-info {
  color: #666;
  font-size: 0.9rem;
}

.available-ports {
  color: #28a745;
  font-weight: 600;
}

.station-actions {
  position: absolute;
  top: 15px;
  right: 15px;
}

.btn-remove-favorite {
  background: none;
  border: none;
  font-size: 1.2rem;
  cursor: pointer;
  opacity: 0.7;
  transition: opacity 0.3s ease;
}

.btn-remove-favorite:hover {
  opacity: 1;
}

.quick-actions {
  margin-bottom: 40px;
}

.scanned-station-section {
  margin-bottom: 30px;
}

.debug-info {
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  padding: 10px;
  margin-bottom: 15px;
  font-size: 0.9rem;
  color: #666;
}

.debug-info p {
  margin: 5px 0;
}

.scan-error {
  margin: 10px 0 20px;
  padding: 12px 16px;
  border-radius: 10px;
  background: #fff5f5;
  color: #c53030;
  border: 1px solid #fed7d7;
}

.quick-actions h2 {
  color: #333;
  font-size: 1.5rem;
  margin-bottom: 20px;
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
}

.action-btn {
  background: white;
  border: 2px solid #e9ecef;
  border-radius: 15px;
  padding: 25px 20px;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 15px;
}

.action-btn:hover {
  border-color: #667eea;
  transform: translateY(-3px);
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
}

.action-icon {
  font-size: 2rem;
}


.btn-primary {
  padding: 12px 24px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: background-color 0.3s ease;
}

.btn-primary:hover {
  background: #5a6fd8;
}


/* Loading overlay */
.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.loading-spinner {
  width: 50px;
  height: 50px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Мобильные стили */
@media (max-width: 768px) {
  .dashboard-content {
    padding: 0 15px;
  }

  .stations-grid {
    grid-template-columns: 1fr;
  }

  .actions-grid {
    grid-template-columns: 1fr;
  }

  .search-input-wrapper {
    flex-direction: column;
  }
}
</style>
