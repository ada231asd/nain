<template>
  <DefaultLayout title="Главная">
    <div class="dashboard-content">
      <!-- Информация о станции из QR-кода -->
      <div v-if="qrStationData" class="qr-station-section">
        <div class="qr-station-card">
          <div class="qr-station-header">
            <h2>Отсканированная станция</h2>
            <button @click="closeQRStation" class="close-qr-btn">×</button>
          </div>
          <div class="qr-station-info">
            <h3>{{ qrStationData.name || qrStationData.station_name || qrStationData.box_id || `Станция ${qrStationData.station_id || qrStationData.id}` }}</h3>
            <div class="station-meta">
              <div class="meta-item">
                <span class="meta-label">ID станции:</span>
                <span class="meta-value">{{ qrStationData.station_id || qrStationData.id }}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">Статус:</span>
                <span class="meta-value status" :class="qrStationData.status">
                  {{ getStatusText(qrStationData.status) }}
                </span>
              </div>
              <div class="meta-item" v-if="qrStationData.address">
                <span class="meta-label">Адрес:</span>
                <span class="meta-value">{{ qrStationData.address }}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">Доступные слоты:</span>
                <span class="meta-value">{{ qrStationData.available_slots || 0 }} / {{ qrStationData.total_slots || 0 }}</span>
              </div>
            </div>
            <div class="qr-station-actions">
              <button @click="borrowPowerbankFromQR" class="action-btn primary" :disabled="!canBorrowFromQR">
                Взять пауэрбанк
              </button>
              <button @click="returnPowerbankFromQR" class="action-btn secondary" :disabled="!canReturnFromQR">
                Вернуть пауэрбанк
              </button>
              <button @click="viewStationDetailsFromQR" class="action-btn tertiary">
                Подробнее о станции
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Избранные станции -->
      <section class="favorites-section">
        <div class="section-header">
          <h2>Избранные станции</h2>
          
        </div>

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
            :isHighlighted="isStationHighlighted(station)"
            :showFavoriteButton="true"
            :showTakeBatteryButton="true"
            :showAdminActions="isAdmin"
            @toggleFavorite="toggleFavorite"
            @takeBattery="handleTakeBattery"
            @returnWithError="handleReturnWithError"
            @adminClick="handleAdminStationClick"
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
          :showAdminActions="isAdmin"
          @toggleFavorite="toggleFavorite"
          @takeBattery="handleTakeBattery"
          @returnWithError="handleReturnWithError"
          @adminClick="handleAdminStationClick"
        />
      </section>

      <div v-if="scanningError" class="scan-error">
        {{ scanningError }}
      </div>

      <!-- Быстрые действия -->
      <section class="quick-actions">
        <h2>Быстрые действия</h2>
        <div class="actions-grid">
          <button @click="showQRScanner = true" class="action-btn-standard">
            Добавить станцию
          </button>
          <button @click="goToAdmin" v-if="isAdmin" class="action-btn-standard">
            Админ панель
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

    <!-- Station Powerbanks Modal -->
    <StationPowerbanksModal
      :is-visible="showPowerbanksModal"
      :station="selectedStation"
      :powerbanks="selectedStationPowerbanks"
      :is-borrowing="isBorrowing"
      @close="closePowerbanks"
      @borrow-powerbank="borrowPowerbank"
      @force-eject-powerbank="forceEjectPowerbank"
    />

    <!-- Error Report Modal -->
    <ErrorReportModal
      :is-visible="showErrorReportModal"
      :order="errorReportOrder"
      @close="closeErrorReportModal"
      @submit="handleErrorReportSubmit"
    />
  </DefaultLayout>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useStationsStore } from '../stores/stations'
import { useAuthStore } from '../stores/auth'
import { useAdminStore } from '../stores/admin'
import DefaultLayout from '../layouts/DefaultLayout.vue'
import QRScanner from '../components/QRScanner.vue'
import StationCard from '../components/StationCard.vue'
import StationPowerbanksModal from '../components/StationPowerbanksModal.vue'
import ErrorReportModal from '../components/ErrorReportModal.vue'
import { pythonAPI } from '../api/pythonApi'
import { refreshAllDataAfterBorrow } from '../utils/dataSync'
import { formatMoscowTime } from '../utils/timeUtils'
// WebSocket больше не используется для выдачи повербанков

const router = useRouter()
const route = useRoute()
const stationsStore = useStationsStore()
const auth = useAuthStore()
const adminStore = useAdminStore()

// Состояние
const searchQuery = ref('')
const showQRScanner = ref(false)
const searchTimeout = ref(null)
const scannedStation = ref(null)
const isScanning = ref(false)

// QR-станция
const qrStationData = ref(null)
const userPowerbanks = ref([])
const scanningError = ref('')
const highlightedFavoriteId = ref(null)

// Модальное окно для просмотра банков станции
const showPowerbanksModal = ref(false)
const selectedStation = ref(null)
const selectedStationPowerbanks = ref([])
const isBorrowing = ref(false)

// Модальное окно для сообщения об ошибке
const showErrorReportModal = ref(false)
const errorReportStation = ref(null)
const errorReportOrder = ref(null)

// Автоматическое обновление данных
const autoRefreshInterval = ref(null)
const autoRefreshEnabled = ref(false) // Отключаем автоматическое обновление по таймеру
const refreshInterval = 30000 // 30 секунд

// Вычисляемые свойства
const user = computed(() => auth.user)
const isLoading = computed(() => stationsStore.isLoading)
const favoriteStations = computed(() => stationsStore.favoriteStations)
const isAdmin = computed(() => auth.user?.role?.includes('admin') || false)

// QR-станция computed
const canBorrowFromQR = computed(() => {
  return qrStationData.value && qrStationData.value.available_slots > 0
})

const canReturnFromQR = computed(() => {
  return userPowerbanks.value && userPowerbanks.value.length > 0
})

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

// Централизованное обновление всех данных после взятия павербанка
const refreshAllDataAfterBorrowLocal = async (stationId, userId) => {
  try {
    console.log('🔄 Начинаем обновление данных после взятия павербанка...')
    await refreshAllDataAfterBorrow(stationId, userId, user.value, refreshFavorites)
    console.log('✅ Обновление данных завершено')
  } catch (error) {
    console.error('❌ Ошибка при обновлении данных:', error)
    throw error // Пробрасываем ошибку дальше
  }
}

// Обновление данных после действий (упрощенная версия)
const refreshAfterAction = async () => {
  try {
    await refreshFavorites()
    // Обновление конкретных станций происходит в самих функциях действий
    // Здесь обновляем только избранные станции
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

const isStationHighlighted = (station) => {
  if (!station || !highlightedFavoriteId.value) return false
  const stationId = station.station_id || station.id
  return stationId === highlightedFavoriteId.value
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
  const stationId = station.station_id || station.id
  const userId = user.value?.user_id
  let didRefresh = false

  try {
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
    console.log('🔄 Отправляем запрос на сервер...')
    const response = await pythonAPI.requestOptimalBorrowPowerbank({
      station_id: stationId,
      user_id: userId
    })
    
    console.log('✅ Ответ API получен:', response)
    
    // Проверяем успешность ответа
    if (response && response.success) {
      console.log('✅ Сервер подтвердил успешную выдачу:', response.message)
      
      // Централизованное обновление данных после взятия павербанка
      console.log('🔄 Обновляем данные...')
      await refreshAllDataAfterBorrowLocal(stationId, userId)
      didRefresh = true
      console.log('✅ Данные обновлены')
      
      // Показываем успешное сообщение
      alert(`✅ ${response.message}`)
    } else {
      console.error('❌ Сервер вернул ошибку:', response)
      alert('❌ Ошибка: ' + (response?.error || 'Неизвестная ошибка сервера'))
    }
    
  } catch (error) {
    console.error('Ошибка при запросе аккумулятора:', error)

    const readableMessage = (() => {
      if (typeof error?.message === 'string') return error.message
      if (typeof error?.message === 'object') { try { return JSON.stringify(error.message) } catch {} }
      if (typeof error?.error === 'string') return error.error
      if (typeof error?.originalError?.message === 'string') return error.originalError.message
      try { return JSON.stringify(error) } catch { return 'Неизвестная ошибка' }
    })()
    
    // Специальная обработка ошибок доступа
    if (error.status === 403 || (readableMessage && readableMessage.includes('недоступна вашему подразделению'))) {
      alert('❌ Доступ запрещен: ' + (readableMessage || 'Эта станция недоступна вашему подразделению'))
      return
    }

    // Фолбэк при сетевом таймауте/нет ответа: проверяем, не выдался ли повербанк фактически
    const isNetworkTimeout = !error.status || error.status === 0 ||
      (readableMessage && (
        readableMessage.includes('Сервер не отвечает') ||
        readableMessage.toLowerCase().includes('timeout') ||
        readableMessage.includes('Превышено время ожидания')
      ))

    if (isNetworkTimeout) {
      try {
        const confirmed = await confirmBorrowAfterNetworkError(stationId, userId)
        if (confirmed) {
          await refreshAllDataAfterBorrowLocal(stationId, userId)
          didRefresh = true
          alert('✅ Повербанк выдан (подтверждено по данным пользователя). Ответ API не успел прийти.')
          return
        }
      } catch (confirmErr) {
        console.log('Подтверждение выдачи не удалось:', confirmErr)
      }
    }

    if (error.status === 400 && readableMessage) {
      alert('❌ Ошибка: ' + readableMessage)
    } else {
      alert('❌ Ошибка при запросе аккумулятора: ' + (readableMessage || 'Неизвестная ошибка'))
    }
  } finally {
    // Даже если сервер вернул 4xx/5xx, синхронизируем данные — станция могла
    // фактически выдать повербанк
    try {
      if (!didRefresh && stationId && userId) {
        await refreshAllDataAfterBorrowLocal(stationId, userId)
      }
    } catch (e) {
      console.warn('Не удалось обновить данные после ошибки запроса:', e)
    }
  }
}

// Фолбэк: при сетевом таймауте проверяем по данным пользователя, не появилась ли у него выдача
const confirmBorrowAfterNetworkError = async (stationId, userId, timeoutMs = 20000, intervalMs = 2000) => {
  const startedAt = Date.now()
  let initialCount = null

  while (Date.now() - startedAt < timeoutMs) {
    try {
      const res = await pythonAPI.getUserPowerbanks()
      const list = Array.isArray(res?.powerbanks) ? res.powerbanks : (Array.isArray(res) ? res : [])

      if (initialCount === null) {
        initialCount = list.length
      } else if (list.length > initialCount) {
        return true
      }
    } catch (e) {
      // игнорируем ошибки опроса
    }

    await new Promise(r => setTimeout(r, intervalMs))
  }

  return false
}

const handleReturnWithError = async (station) => {
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
    
    console.log('Открытие модального окна для возврата с ошибкой:', { stationId, userId })
    
    // Формируем базовый объект заказа для модального окна
    // Конкретные данные о повербанке будут заполнены при отправке отчета
    errorReportOrder.value = {
      station_id: stationId,
      user_id: userId
    }
    
    errorReportStation.value = station
    showErrorReportModal.value = true
    
  } catch (error) {
    console.error('Ошибка при возврате с ошибкой:', error)
    alert('Ошибка: ' + (error.message || 'Неизвестная ошибка'))
  }
}

const closeErrorReportModal = () => {
  showErrorReportModal.value = false
  errorReportStation.value = null
  errorReportOrder.value = null
}

const handleErrorReportSubmit = async (errorReport) => {
  try {
    console.log('Отправка отчета об ошибке:', errorReport)
    
    // Отправляем отчет об ошибке через API
    const response = await pythonAPI.reportPowerbankError(errorReport)
    
    if (response && response.success) {
      alert('Отчет об ошибке успешно отправлен')
      closeErrorReportModal()
    } else {
      alert('Ошибка при отправке отчета: ' + (response?.error || 'Неизвестная ошибка'))
    }
    
  } catch (error) {
    console.error('Ошибка при отправке отчета об ошибке:', error)
    alert('Ошибка при отправке отчета: ' + (error.message || 'Неизвестная ошибка'))
  }
}



const goToAdmin = () => {
  router.push('/admin')
}

// QR-станция методы
const loadQRStation = async () => {
  const stationName = route.query.stationName
  console.log('loadQRStation called with stationName:', stationName)
  if (!stationName) return
  
  try {
    console.log('Loading stations to find:', stationName)
    // Загружаем все станции и ищем по имени
    const stationsResponse = await pythonAPI.getStations()
    console.log('Stations response:', stationsResponse)
    
    // Проверяем, что ответ содержит массив станций
    const stations = Array.isArray(stationsResponse) ? stationsResponse : 
                    stationsResponse.stations || stationsResponse.data || []
    console.log('Stations array:', stations)
    
    const station = stations.find(s => 
      s.name === stationName || 
      s.station_name === stationName || 
      s.box_id === stationName ||
      s.station_id === stationName ||
      `Станция ${s.station_id || s.id}` === stationName
    )
    
    if (station) {
      console.log('Found station:', station)
      qrStationData.value = station
      await loadUserPowerbanks()
    } else {
      console.log('Station not found:', stationName)
      console.log('Available stations:', stations.map(s => ({
        name: s.name,
        station_name: s.station_name,
        box_id: s.box_id,
        station_id: s.station_id
      })))
    }
  } catch (error) {
    console.error('Ошибка загрузки QR-станции:', error)
  }
}

const loadUserPowerbanks = async () => {
  try {
    const response = await pythonAPI.getUserPowerbanks()
    userPowerbanks.value = response.powerbanks || []
  } catch (error) {
    console.error('Ошибка загрузки пауэрбанков пользователя:', error)
    userPowerbanks.value = []
  }
}

const closeQRStation = () => {
  qrStationData.value = null
  // Очищаем URL параметры
  router.replace('/dashboard')
}

const borrowPowerbankFromQR = async () => {
  if (!canBorrowFromQR.value || !qrStationData.value) return
  
  try {
    const stationId = qrStationData.value.station_id || qrStationData.value.id
    const response = await pythonAPI.borrowPowerbank(stationId)
    alert('Пауэрбанк успешно взят!')
    await loadQRStation() // Обновляем данные
  } catch (error) {
    console.error('Ошибка взятия пауэрбанка:', error)
    alert('Ошибка при взятии пауэрбанка: ' + (error.message || 'Неизвестная ошибка'))
  }
}

const returnPowerbankFromQR = async () => {
  if (!canReturnFromQR.value || !qrStationData.value) return
  
  try {
    const stationId = qrStationData.value.station_id || qrStationData.value.id
    const powerbankId = userPowerbanks.value[0].id
    const response = await pythonAPI.returnPowerbank(stationId, powerbankId)
    alert('Пауэрбанк успешно возвращен!')
    await loadQRStation() // Обновляем данные
  } catch (error) {
    console.error('Ошибка возврата пауэрбанка:', error)
    alert('Ошибка при возврате пауэрбанка: ' + (error.message || 'Неизвестная ошибка'))
  }
}

const viewStationDetailsFromQR = () => {
  if (!qrStationData.value) return
  const stationId = qrStationData.value.station_id || qrStationData.value.id
  router.push(`/address/${stationId}`)
}

// Функции для работы с модальным окном банков станции
const handleAdminStationClick = async (station) => {
  try {
    selectedStation.value = station
    const stationId = station.station_id || station.id
    if (!stationId) return
    
    const res = await pythonAPI.getStationPowerbanks(stationId)
    selectedStationPowerbanks.value = Array.isArray(res?.available_powerbanks) ? res.available_powerbanks : []
    showPowerbanksModal.value = true
  } catch (error) {
    console.error('Ошибка при загрузке банков станции:', error)
    selectedStationPowerbanks.value = []
    showPowerbanksModal.value = true
  }
}

const closePowerbanks = () => {
  showPowerbanksModal.value = false
  selectedStation.value = null
  selectedStationPowerbanks.value = []
}

const borrowPowerbank = async (powerbank) => {
  if (!selectedStation.value || isBorrowing.value) return

  isBorrowing.value = true
  try {
    const userId = user.value?.id || user.value?.user_id

    if (!userId) {
      alert('Не удалось определить пользователя')
      return
    }

    const requestData = {
      station_id: selectedStation.value.station_id || selectedStation.value.id,
      user_id: userId,
      slot_number: powerbank.slot_number
    }

    const result = await pythonAPI.requestBorrowPowerbank(requestData)

    if (result && result.success) {
      alert('Повербанк успешно выдан!')
      
      // Централизованное обновление данных после выдачи павербанка
      const stationId = selectedStation.value.station_id || selectedStation.value.id
      await refreshAllDataAfterBorrowLocal(stationId, userId)
      
      // Обновляем список повербанков в модальном окне
      const updatedResult = await pythonAPI.getStationPowerbanks(stationId)
      selectedStationPowerbanks.value = Array.isArray(updatedResult?.available_powerbanks) ? updatedResult.available_powerbanks : []
    } else {
      alert('❌ Ошибка при выдаче повербанка: ' + (result?.error || 'Неизвестная ошибка сервера'))
    }
  } catch (error) {
    console.error('Ошибка при выдаче повербанка:', error)
    alert('Ошибка при выдаче повербанка: ' + (error.message || 'Неизвестная ошибка'))
  } finally {
    isBorrowing.value = false
  }
}

const forceEjectPowerbank = async (powerbank) => {
  if (!selectedStation.value || isBorrowing.value) return

  const confirmMessage = `Вы уверены, что хотите принудительно извлечь повербанк из слота ${powerbank.slot_number}?`
  if (!confirm(confirmMessage)) return

  isBorrowing.value = true
  try {
    const userId = user.value?.id || user.value?.user_id

    if (!userId) {
      alert('Не удалось определить пользователя')
      return
    }

    const requestData = {
      station_id: selectedStation.value.station_id || selectedStation.value.id,
      slot_number: powerbank.slot_number,
      admin_user_id: userId
    }

    await pythonAPI.forceEjectPowerbank(requestData)
    alert('Повербанк принудительно извлечен!')

    // Централизованное обновление данных после принудительного извлечения
    const stationId = selectedStation.value.station_id || selectedStation.value.id
    await refreshAllDataAfterBorrowLocal(stationId, userId)

    // Обновляем список повербанков в модальном окне
    const updatedResult = await pythonAPI.getStationPowerbanks(stationId)
    selectedStationPowerbanks.value = Array.isArray(updatedResult?.available_powerbanks) ? updatedResult.available_powerbanks : []

  } catch (error) {
    console.error('Ошибка при принудительном извлечении повербанка:', error)
    alert('Ошибка при принудительном извлечении повербанка: ' + (error.message || 'Неизвестная ошибка'))
  } finally {
    isBorrowing.value = false
  }
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

    // Если найденная станция уже в избранном, только подсвечиваем её
    if (isStationFavorite(detailed)) {
      const stationId = detailed.station_id || detailed.id
      highlightedFavoriteId.value = stationId
      
      // Убираем подсветку через 5 секунд
      setTimeout(() => {
        highlightedFavoriteId.value = null
      }, 5000)
      
      // Прокручиваем к секции избранных станций
      setTimeout(() => {
        const favoritesSection = document.querySelector('.favorites-section')
        if (favoritesSection) {
          favoritesSection.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'center' 
          })
        }
      }, 1000)
      
      // НЕ показываем станцию в секции "Найденная станция"
      scannedStation.value = null
    } else {
      // Проверяем доступ к станции (только для пользователей с ролью 'user')
      if (user.value?.role === 'user') {
        try {
          const stationId = detailed.station_id || detailed.id
          
          // Проверяем доступ через API (пробуем получить повербанки станции)
          const powerbanksResponse = await pythonAPI.getStationPowerbanks(stationId)
          
          // Если получили ошибку доступа, показываем требуемое сообщение
          if (powerbanksResponse && powerbanksResponse.error) {
            if (powerbanksResponse.error.includes('недоступна вашему подразделению') || 
                powerbanksResponse.error.includes('не привязана к организационной единице')) {
              scanningError.value = 'Ограничения доступа: Вы можете сканировать и использовать только станции, принадлежащие вашему подразделению.'
              return
            }
          }
        } catch (accessError) {
          console.log('Ошибка проверки доступа к станции:', accessError)
          // Если ошибка связана с доступом, показываем требуемое сообщение
          if (accessError.status === 403 || (accessError.message && accessError.message.includes('недоступна вашему подразделению'))) {
            scanningError.value = 'Ограничения доступа: Вы можете сканировать и использовать только станции, принадлежащие вашему подразделению.'
            return
          }
        }
      }
      
      // Показываем станцию в секции "Найденная станция" только если её нет в избранном
      scannedStation.value = detailed
    }
    
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

const formatTime = (timestamp) => formatMoscowTime(timestamp, {
  day: '2-digit',
  month: '2-digit',
  hour: '2-digit',
  minute: '2-digit'
})

// WebSocket уведомления удалены; фронтенд ожидает ответ API

// Жизненный цикл
onMounted(async () => {
  try {
    console.log('onMounted: загружаем избранное для user_id:', user.value?.user_id)
    await stationsStore.fetchFavoriteStations(user.value?.user_id)
    
    // Загружаем QR-станцию если есть параметры
    await loadQRStation()
    
    // WebSocket больше не используется — полагаемся на синхронные ответы API
    
    // Не запускаем автоматическое обновление по таймеру
    // Обновление происходит только после действий
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
  
  // WebSocket не используется
})
</script>

<style scoped>
.dashboard-content {
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}

.search-section {
  margin-bottom: 20px;
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

.user-info-message {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 15px 20px;
  background: #e3f2fd;
  border: 1px solid #bbdefb;
  border-radius: 10px;
  margin-bottom: 25px;
  color: #1565c0;
}

.info-icon {
  font-size: 1.2rem;
  flex-shrink: 0;
}

.info-text {
  font-size: 0.95rem;
  line-height: 1.4;
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

.action-btn-standard {
  background: #667eea;
  color: white;
  border: none;
  border-radius: 10px;
  padding: 12px 24px;
  cursor: pointer;
  transition: all 0.3s ease;
  font-weight: 600;
  font-size: 1rem;
}

.action-btn-standard:hover {
  background: #5a6fd8;
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
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

  .action-btn-standard {
    width: 100%;
  }

  .search-input-wrapper {
    flex-direction: column;
  }
}

/* QR-станция стили */
.qr-station-section {
  margin-bottom: 2rem;
}

.qr-station-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  padding: 1.5rem;
  color: white;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.qr-station-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.qr-station-header h2 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
}

.close-qr-btn {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  cursor: pointer;
  font-size: 1.2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s;
}

.close-qr-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

.qr-station-info h3 {
  margin: 0 0 1rem 0;
  font-size: 1.25rem;
  font-weight: 500;
}

.station-meta {
  display: grid;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.meta-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  backdrop-filter: blur(10px);
}

.meta-label {
  font-weight: 500;
  opacity: 0.9;
}

.meta-value {
  font-weight: 600;
}

.status.active {
  color: #10b981;
}

.status.inactive {
  color: #6b7280;
}

.status.maintenance {
  color: #f59e0b;
}

.status.error {
  color: #ef4444;
}

.status.pending {
  color: #8b5cf6;
}

.qr-station-actions {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.action-btn {
  flex: 1;
  min-width: 150px;
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn.primary {
  background-color: #10b981;
  color: white;
}

.action-btn.primary:hover:not(:disabled) {
  background-color: #059669;
  transform: translateY(-1px);
}

.action-btn.secondary {
  background-color: #3b82f6;
  color: white;
}

.action-btn.secondary:hover:not(:disabled) {
  background-color: #2563eb;
  transform: translateY(-1px);
}

.action-btn.tertiary {
  background-color: rgba(255, 255, 255, 0.2);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.action-btn.tertiary:hover:not(:disabled) {
  background-color: rgba(255, 255, 255, 0.3);
  transform: translateY(-1px);
}

.action-btn:disabled {
  background-color: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.5);
  cursor: not-allowed;
  transform: none;
}

@media (max-width: 768px) {
  .qr-station-actions {
    flex-direction: column;
  }
  
  .action-btn {
    min-width: auto;
  }
}
</style>
