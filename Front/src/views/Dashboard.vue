<template>
  <DefaultLayout 
    :title="userOrgUnit?.name || 'Главная'"
    :org-unit="userOrgUnit"
    :org-unit-logo="orgUnitLogo"
    :is-loading-org-unit="isLoadingOrgUnit"
    @logo-error="handleLogoError"
  >
    <div class="dashboard-content">

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
              placeholder="Поиск по адресу станции, box_id, названию..."
              class="search-input"
              @input="handleSearch"
              @focus="showSearchDropdown = true"
              @blur="hideSearchDropdown"
              autocomplete="off"
            />
            <div v-if="isSearching" class="search-loading">
              <div class="loading-spinner"></div>
            </div>
            <button 
              v-if="searchQuery && !isSearching" 
              @click="clearSearch"
              class="search-clear-btn"
              title="Очистить поиск"
            >
              ✕
            </button>
          </div>
          
          <!-- Выпадающий список результатов поиска -->
          <div v-if="showSearchDropdown && searchResults.length > 0" class="search-dropdown">
            <div class="search-dropdown-header">
              <span>Найдено: {{ searchResults.length }}</span>
            </div>
            <div class="search-dropdown-list">
              <div
                v-for="station in searchResults"
                :key="station.station_id || station.id"
                class="search-dropdown-item"
                @mousedown="selectSearchResult(station)"
              >
                <div class="search-item-main">
                  <div class="search-item-title" :class="{ 'highlighted-nickname': isNicknameMatch(station) }">
                    {{ station.nickname || station.nik || station.box_id || station.station_box_id || 'Без ID' }}
                  </div>
                  <div v-if="station.nickname || station.nik" class="search-item-box-id">
                    {{ station.box_id || station.station_box_id }}
                  </div>
                  <div class="search-item-subtitle" :class="{ 'highlighted-address': isAddressMatch(station) }">
                    {{ station.address || station.station_address || 'Адрес не указан' }}
                  </div>
                </div>
                <div class="search-item-meta">
                  <span class="search-item-status" :class="getStatusClass(station.status)">
                    {{ getStatusText(station.status) }}
                  </span>
                  <span class="search-item-ports">
                    {{ station.freePorts || station.remain_num || 0 }}/{{ station.totalPorts || station.slots_declared || 0 }}
                  </span>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Сообщение "ничего не найдено" -->
          <div v-if="showSearchDropdown && searchResults.length === 0 && searchQuery && !isSearching" class="search-dropdown">
            <div class="search-no-results">
              <p>По запросу "{{ searchQuery }}" ничего не найдено</p>
            </div>
          </div>
        </div>
        
        <div v-if="favoriteStations.length === 0" class="empty-state">
          <p>У Вас пока нет избранных станций</p>
          <p class="empty-state-hint">Чтобы добавить станцию, нажмите "Найти станцию"</p>
        </div>
        
        <div v-else class="stations-grid">
          <StationCard
            v-for="station in favoriteStations"
            :key="station.station_id"
            :station="station"
            :isFavorite="true"
            :isHighlighted="isStationHighlighted(station)"
            :isExpanded="isStationExpanded(station)"
            :showFavoriteButton="true"
            :showTakeBatteryButton="true"
            :showAdminActions="isAdmin"
            @toggleFavorite="toggleFavorite"
            @takeBattery="handleTakeBattery"
            @returnWithError="handleReturnWithError"
            @adminClick="handleAdminStationClick"
            @toggleExpansion="toggleStationExpansion"
            @nicknameChanged="handleNicknameChanged"
          />
        </div>
      </section>


      <!-- Результат сканирования: показ карточки станции -->
      <section v-if="scannedStation" class="scanned-station-section">
        <h2>Найденная станция</h2>
        <StationCard
          :station="scannedStation"
          :isFavorite="isStationFavorite(scannedStation)"
          :isExpanded="isStationExpanded(scannedStation)"
          :showFavoriteButton="true"
          :showTakeBatteryButton="true"
          :showAdminActions="isAdmin"
          @toggleFavorite="toggleFavorite"
          @takeBattery="handleTakeBattery"
          @returnWithError="handleReturnWithError"
          @adminClick="handleAdminStationClick"
          @toggleExpansion="toggleStationExpansion"
          @nicknameChanged="handleNicknameChanged"
        />
      </section>

      <div v-if="scanningError" class="scan-error">
        {{ scanningError }}
      </div>

      <!-- Быстрые действия -->
      <section class="quick-actions">
        <div class="actions-grid">
          <button @click="showQRScanner = true" class="action-btn-standard">
            Найти станцию
          </button>
          <PWAInstallButton />
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

    <!-- Индикатор ожидания возврата -->
    <div v-if="isWaitingForReturn" class="return-waiting-overlay">
      <div class="return-waiting-content">
        <div class="return-spinner"></div>
        <p class="return-waiting-text">Ожидаем подтверждения возврата...</p>
        <p class="return-waiting-hint">Пожалуйста, вставьте повербанк в станцию</p>
      </div>
    </div>
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
import PWAInstallButton from '../components/PWAInstallButton.vue'
import { pythonAPI } from '../api/pythonApi'
import { refreshAllDataAfterBorrow, refreshAllDataAfterReturn } from '../utils/dataSync'
import { formatMoscowTime } from '../utils/timeUtils'
import { showSuccess, showError, showWarning, showInfo, showConfirm } from '../utils/notifications'
import websocketNotificationService from '../utils/websocketNotifications'

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

// Состояние для поиска
const searchResults = ref([])
const isSearching = ref(false)
const showSearchDropdown = ref(false)

// Состояние для развернутых карточек станций
const expandedStations = ref(new Set())

// Сканирование
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
const isWaitingForReturn = ref(false)

// Состояние для данных группы и логотипа
const userOrgUnit = ref(null)
const orgUnitLogo = ref(null)
const isLoadingOrgUnit = ref(true) // Изначально true, чтобы показать индикатор загрузки

// Автоматическое обновление данных
const autoRefreshInterval = ref(null)
const autoRefreshEnabled = ref(false) // Отключаем автоматическое обновление по таймеру
const refreshInterval = 30000 // 30 секунд

// WebSocket обновления
const wsUnsubscribe = ref(null)

// Вычисляемые свойства
const user = computed(() => auth.user)
const isLoading = computed(() => stationsStore.isLoading)
const favoriteStations = computed(() => stationsStore.favoriteStations)
const isAdmin = computed(() => auth.user?.role?.includes('admin') || false)

// Получение org_unit_id пользователя
const userOrgUnitId = computed(() => {
  if (!user.value) return null
  
  // Проверяем все возможные поля для ID группы
  return user.value.parent_org_unit_id || user.value.org_unit_id || user.value.group_id || user.value.organization_id
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

// Загрузка данных группы пользователя
const loadUserOrgUnit = async () => {
  if (!userOrgUnitId.value) {
    console.log('Нет org_unit_id для пользователя')
    isLoadingOrgUnit.value = false
    return
  }

  isLoadingOrgUnit.value = true
  try {
    console.log('Загружаем данные группы для org_unit_id:', userOrgUnitId.value)
    
    // Получаем данные группы
    const orgUnitResponse = await pythonAPI.getOrgUnit(userOrgUnitId.value)
    console.log('Ответ API группы:', orgUnitResponse)
    
    // Извлекаем данные группы
    const orgUnitData = orgUnitResponse?.data || orgUnitResponse
    if (orgUnitData) {
      userOrgUnit.value = orgUnitData
      console.log('Данные группы загружены:', orgUnitData)
      
      // Если есть логотип, загружаем его
      if (orgUnitData.logo_url) {
        try {
          const logoUrl = orgUnitData.logo_url
          console.log('Обрабатываем логотип:', logoUrl)
          
          // Проверяем, является ли это внешней ссылкой
          if (logoUrl.startsWith('http://') || logoUrl.startsWith('https://')) {
            // Внешняя ссылка - используем напрямую
            console.log('Используем внешнюю ссылку на логотип:', logoUrl)
            orgUnitLogo.value = logoUrl
          } else {
            // Локальный файл на сервере - запрашиваем через API
            console.log('Загружаем логотип с сервера:', logoUrl)
            const logoBlob = await pythonAPI.getOrgUnitLogo(logoUrl)
            
            // Создаем URL для blob
            const blobUrl = URL.createObjectURL(logoBlob)
            orgUnitLogo.value = blobUrl
            console.log('Логотип загружен:', blobUrl)
          }
        } catch (logoError) {
          console.error('Ошибка загрузки логотипа:', logoError)
          orgUnitLogo.value = null
        }
      } else {
        console.log('У группы нет логотипа')
        orgUnitLogo.value = null
      }
    }
  } catch (error) {
    console.error('Ошибка загрузки данных группы:', error)
    userOrgUnit.value = null
    orgUnitLogo.value = null
  } finally {
    isLoadingOrgUnit.value = false
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

// Централизованное обновление всех данных после взятия аккумулятора
const refreshAllDataAfterBorrowLocal = async (stationId, userId) => {
  try {
    console.log('🔄 Начинаем обновление данных после взятия аккумулятора...')
    await refreshAllDataAfterBorrow(stationId, userId, user.value, refreshFavorites)
    console.log('✅ Обновление данных завершено')
  } catch (error) {
    console.error('❌ Ошибка при обновлении данных:', error)
    throw error // Пробрасываем ошибку дальше
  }
}

// Централизованное обновление всех данных после возврата аккумулятора
const refreshAllDataAfterReturnLocal = async (orderData) => {
  try {
    console.log('🔄 Начинаем обновление данных после возврата аккумулятора...')
    // Создаем пустую функцию загрузки заказов, так как в Dashboard.vue нет истории заказов
    const loadUserOrders = async () => {
      // В Dashboard нет истории заказов, просто обновляем избранные станции
      await refreshFavorites()
    }
    await refreshAllDataAfterReturn(orderData, user.value, loadUserOrders)
    console.log('✅ Обновление данных после возврата завершено')
  } catch (error) {
    console.error('❌ Ошибка при обновлении данных после возврата:', error)
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

// Функции для управления развернутыми карточками
const isStationExpanded = (station) => {
  if (!station) return false
  const stationId = station.station_id || station.id
  return expandedStations.value.has(stationId)
}

const toggleStationExpansion = (station) => {
  if (!station) return
  const stationId = station.station_id || station.id
  if (expandedStations.value.has(stationId)) {
    expandedStations.value.delete(stationId)
  } else {
    expandedStations.value.add(stationId)
  }
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
      
      // Разворачиваем карточку при добавлении в избранное
      expandedStations.value.add(stationId)
      
      // Перемещаем станцию в начало списка избранных
      stationsStore.moveStationToTop(stationId)
      
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
      
      // Сначала показываем успешное сообщение
      showSuccess(response.message)
      
      // Затем выполняем централизованное обновление данных после взятия аккумулятора
      console.log('🔄 Обновляем данные...')
      await refreshAllDataAfterBorrowLocal(stationId, userId)
      didRefresh = true
      console.log('✅ Данные обновлены')
    } else {
      console.error('❌ Сервер вернул ошибку:', response)
      showError('Ошибка: ' + (response?.error || 'Неизвестная ошибка сервера'))
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
      showError('Доступ запрещен: ' + (readableMessage || 'Эта станция недоступна вашему подразделению'))
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
          // Сначала показываем успешное сообщение
          showSuccess('Аккумулятор выдан (подтверждено по данным пользователя). Ответ API не успел прийти.')
          
          // Затем обновляем данные
          await refreshAllDataAfterBorrowLocal(stationId, userId)
          didRefresh = true
          return
        }
      } catch (confirmErr) {
        console.log('Подтверждение выдачи не удалось:', confirmErr)
      }
    }

    if (error.status === 400 && readableMessage) {
      showError('Ошибка: ' + readableMessage)
    } else {
      showError('Ошибка при запросе аккумулятора: ' + (readableMessage || 'Неизвестная ошибка'))
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
    const stationBoxId = station.box_id || station.station_box_id
    const userPhone = user.value?.phone_e164
    
    if (!stationBoxId) {
      console.error('Отсутствует box_id станции:', station)
      showError(`Ошибка: У станции отсутствует box_id.\nID станции: ${station.station_id || station.id}`)
      return
    }
    
    if (!userPhone) {
      console.error('Отсутствует телефон пользователя')
      showError('Ошибка: Не удалось получить телефон пользователя')
      return
    }
    
    console.log('Открытие модального окна для возврата с ошибкой:', { stationBoxId, userPhone })
    
    // Формируем базовый объект заказа для модального окна
    // Конкретные данные о повербанке будут заполнены при отправке отчета
    errorReportOrder.value = {
      station_box_id: stationBoxId,
      user_phone: userPhone,
      station_id: station.station_id || station.id,
      user_id: user.value?.user_id
    }
    
    errorReportStation.value = station
    showErrorReportModal.value = true
    
  } catch (error) {
    console.error('Ошибка при возврате с ошибкой:', error)
    showError('Ошибка: ' + (error.message || 'Неизвестная ошибка'))
  }
}

const closeErrorReportModal = () => {
  showErrorReportModal.value = false
  errorReportStation.value = null
  errorReportOrder.value = null
}

const handleErrorReportSubmit = async (errorReport) => {
  try {
    console.log('Получен отчет об ошибке:', errorReport)
    
    // Закрываем модалку и показываем индикатор ожидания
    closeErrorReportModal()
    isWaitingForReturn.value = true
    
    // Показываем уведомление об ожидании
    showInfo('⏳ Ожидаем вставки аккумулятора в станцию (до 30 секунд)...')
    
    // Отправляем запрос на возврат с ошибкой через Long Polling API
    const response = await pythonAPI.returnError({
      station_box_id: errorReport.station_box_id,
      user_phone: errorReport.user_phone,
      error_type_id: errorReport.error_type_id,
      timeout_seconds: 30 // 30 секунд ожидания
    })
    
    isWaitingForReturn.value = false
    
    if (response.success) {
      // Успешно обработан возврат с ошибкой
      showSuccess('✅ Возврат с ошибкой успешно обработан!\n' + (response.message || ''))
      
      // Обновляем данные по станции/пользователю
      try {
        const orderData = {
          station_box_id: response.station_box_id || errorReport.station_box_id,
          user_phone: response.user_phone || errorReport.user_phone,
          powerbank_serial: response.powerbank_serial || errorReport.powerbank_serial
        }
        
        // Используем правильную функцию для обновления данных после возврата
        await refreshAllDataAfterReturnLocal(orderData)
      } catch (refreshErr) {
        console.warn('Ошибка обновления данных после возврата:', refreshErr)
      }
    } else {
      // Произошла ошибка при возврате
      showError('❌ Ошибка при возврате с ошибкой: ' + (response.error || 'Неизвестная ошибка'))
    }
    
  } catch (error) {
    console.error('Ошибка при обработке отчета об ошибке:', error)
    isWaitingForReturn.value = false
    showError('❌ Ошибка: ' + (error.message || 'Неизвестная ошибка'))
  }
}

// Обработка изменения nickname станции
const handleNicknameChanged = async ({ station, nickname, action }) => {
  try {
    const userId = user.value?.user_id
    const stationId = station.station_id || station.id
    const favoriteId = station.favorite_id
    
    console.log('handleNicknameChanged вызван:', { station, nickname, action, userId, stationId, favoriteId })
    console.log('stationsStore:', stationsStore)
    console.log('stationsStore.setStationNickname:', stationsStore.setStationNickname)
    
    if (!userId || !stationId || !favoriteId) {
      console.error('Недостаточно данных для изменения nickname:', { userId, stationId, favoriteId })
      showError('Ошибка: недостаточно данных для изменения имени станции')
      return
    }
    
    if (action === 'set') {
      // Установка нового nickname
      console.log('Устанавливаем nickname:', { favoriteId, userId, stationId, nickname })
      
      // Проверяем, что метод существует
      if (typeof stationsStore.setStationNickname !== 'function') {
        console.error('stationsStore.setStationNickname не является функцией!')
        console.error('Доступные методы:', Object.keys(stationsStore))
        showError('Ошибка: метод setStationNickname недоступен. Перезагрузите страницу.')
        return
      }
      
      await stationsStore.setStationNickname(favoriteId, userId, stationId, nickname)
      
      // Обновляем локальные данные станции
      const localStation = favoriteStations.value.find(s => s.favorite_id === favoriteId)
      if (localStation) {
        localStation.nickname = nickname
        localStation.nik = nickname
      }
      
      console.log('✅ Nickname успешно установлен')
    } else if (action === 'delete') {
      // Удаление nickname
      console.log('Удаляем nickname для favorite_id:', favoriteId)
      
      // Проверяем, что метод существует
      if (typeof stationsStore.deleteStationNickname !== 'function') {
        console.error('stationsStore.deleteStationNickname не является функцией!')
        console.error('Доступные методы:', Object.keys(stationsStore))
        showError('Ошибка: метод deleteStationNickname недоступен. Перезагрузите страницу.')
        return
      }
      
      await stationsStore.deleteStationNickname(favoriteId)
      
      // Обновляем локальные данные станции
      const localStation = favoriteStations.value.find(s => s.favorite_id === favoriteId)
      if (localStation) {
        localStation.nickname = null
        localStation.nik = null
      }
      
      console.log('✅ Nickname успешно удален')
    }
  } catch (error) {
    console.error('Ошибка при изменении nickname:', error)
    showError('Ошибка при изменении имени станции: ' + (error.message || 'Неизвестная ошибка'))
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
    // Загружаем все станции и ищем по имени или box_id
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
      console.log('Found station from URL:', station)
      
      // Загружаем актуальные данные станции
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
      
      // Если найденная станция уже в избранном, подсвечиваем и разворачиваем её
      if (isStationFavorite(detailed)) {
        const stationId = detailed.station_id || detailed.id
        highlightedFavoriteId.value = stationId
        
        // Разворачиваем карточку при повторном нахождении
        expandedStations.value.add(stationId)
        
        // Перемещаем станцию в начало списка избранных
        stationsStore.moveStationToTop(stationId)
        
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
        // Показываем станцию в секции "Найденная станция" только если её нет в избранном
        scannedStation.value = detailed
        
        // Прокручиваем к секции найденной станции
        setTimeout(() => {
          const scannedSection = document.querySelector('.scanned-station-section')
          if (scannedSection) {
            scannedSection.scrollIntoView({ 
              behavior: 'smooth', 
              block: 'start' 
            })
          }
        }, 500)
      }
      
      // Очищаем URL параметры
      router.replace('/dashboard')
    } else {
      console.log('Station not found:', stationName)
      console.log('Available stations:', stations.map(s => ({
        name: s.name,
        station_name: s.station_name,
        box_id: s.box_id,
        station_id: s.station_id
      })))
      scanningError.value = `Станция "${stationName}" не найдена`
      
      // Очищаем URL параметры
      router.replace('/dashboard')
    }
  } catch (error) {
    console.error('Ошибка загрузки QR-станции:', error)
    scanningError.value = 'Произошла ошибка при загрузке станции'
    
    // Очищаем URL параметры
    router.replace('/dashboard')
  }
}

// Функции для работы с модальным окном банков станции
const handleAdminStationClick = async (station) => {
  try {
    selectedStation.value = station
    const stationId = station.station_id || station.id
    if (!stationId) return
    
    // 1) Тригерим запрос инвентаря на сервер (обновление показаний)
    try { await pythonAPI.queryInventory(stationId) } catch {}
    
    // 2) Получаем инвентарь из кэша соединения (в нём есть terminal_id, soh и ошибки)
    let inv = null
    try {
      inv = await pythonAPI.getStationInventory(stationId)
    } catch {}
    
    if (inv && Array.isArray(inv.inventory)) {
      selectedStationPowerbanks.value = inv.inventory
    } else {
      // Фолбэк: детальный список из station_powerbank (включает паверbanки с ошибками)
      const res = await pythonAPI.getStationPowerbanksDetailed({ station_id: stationId })
      selectedStationPowerbanks.value = Array.isArray(res?.data) ? res.data : []
    }
    
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
      showError('Не удалось определить пользователя')
      return
    }

    const requestData = {
      station_id: selectedStation.value.station_id || selectedStation.value.id,
      user_id: userId,
      slot_number: powerbank.slot_number
    }

    const result = await pythonAPI.requestBorrowPowerbank(requestData)

    if (result && result.success) {
      // Сначала показываем успешное сообщение
      showSuccess('Аккумулятор успешно выдан!')
      
      // Затем выполняем централизованное обновление данных после выдачи аккумулятора
      const stationId = selectedStation.value.station_id || selectedStation.value.id
      await refreshAllDataAfterBorrowLocal(stationId, userId)
      
      // Обновляем список повербанков в модальном окне (через инвентарь)
      try { await pythonAPI.queryInventory(stationId) } catch {}
      const inv = await pythonAPI.getStationInventory(stationId)
      selectedStationPowerbanks.value = Array.isArray(inv?.inventory) ? inv.inventory : []
    } else {
      showError('Ошибка при выдаче аккумулятора: ' + (result?.error || 'Неизвестная ошибка сервера'))
    }
  } catch (error) {
    console.error('Ошибка при выдаче повербанка:', error)
    showError('Ошибка при выдаче аккумулятора: ' + (error.message || 'Неизвестная ошибка'))
  } finally {
    isBorrowing.value = false
  }
}

const forceEjectPowerbank = async (powerbank) => {
  if (!selectedStation.value || isBorrowing.value) return

  const confirmMessage = `Вы уверены, что хотите принудительно извлечь аккумулятор из слота ${powerbank.slot_number}?`
  if (!await showConfirm(confirmMessage)) return

  isBorrowing.value = true
  try {
    const userId = user.value?.id || user.value?.user_id

    if (!userId) {
      showError('Не удалось определить пользователя')
      return
    }

    const requestData = {
      station_id: selectedStation.value.station_id || selectedStation.value.id,
      slot_number: powerbank.slot_number,
      admin_user_id: userId
    }

    await pythonAPI.forceEjectPowerbank(requestData)
    
    // Сначала показываем успешное сообщение
    showSuccess('Аккумулятор принудительно извлечен!')

    // Затем выполняем централизованное обновление данных после принудительного извлечения
    const stationId = selectedStation.value.station_id || selectedStation.value.id
    await refreshAllDataAfterBorrowLocal(stationId, userId)

    // Обновляем список повербанков в модальном окне (через инвентарь)
    try { await pythonAPI.queryInventory(stationId) } catch {}
    const inv = await pythonAPI.getStationInventory(stationId)
    selectedStationPowerbanks.value = Array.isArray(inv?.inventory) ? inv.inventory : []

  } catch (error) {
    console.error('Ошибка при принудительном извлечении повербанка:', error)
    showError('Ошибка при принудительном извлечении аккумулятора: ' + (error.message || 'Неизвестная ошибка'))
  } finally {
    isBorrowing.value = false
  }
}

const handleSearch = async () => {
  // Очищаем предыдущий таймаут
  if (searchTimeout.value) {
    clearTimeout(searchTimeout.value)
  }
  
  // Устанавливаем новый таймаут для поиска
  searchTimeout.value = setTimeout(async () => {
    const query = searchQuery.value.trim()
    
    if (query) {
      isSearching.value = true
      showSearchDropdown.value = true
      
      try {
        const results = await stationsStore.searchStations(query)
        searchResults.value = results
      } catch (err) {
        console.error('Ошибка поиска:', err)
        searchResults.value = []
      } finally {
        isSearching.value = false
      }
    } else {
      // Если поисковый запрос пустой, скрываем результаты
      showSearchDropdown.value = false
      searchResults.value = []
    }
  }, 300) // Уменьшили задержку для более быстрого отклика
}

const clearSearch = () => {
  searchQuery.value = ''
  showSearchDropdown.value = false
  searchResults.value = []
  isSearching.value = false
  
  if (searchTimeout.value) {
    clearTimeout(searchTimeout.value)
    searchTimeout.value = null
  }
}

// Функции для работы с выпадающим списком
const hideSearchDropdown = () => {
  // Небольшая задержка, чтобы клик по элементу успел сработать
  setTimeout(() => {
    showSearchDropdown.value = false
  }, 150)
}

const selectSearchResult = async (station) => {
  console.log('Выбрана станция из поиска:', station)
  
  // Очищаем поиск
  clearSearch()
  
  // Если станция уже в избранном, перемещаем её наверх и подсвечиваем
  if (isStationFavorite(station)) {
    const stationId = station.station_id || station.id
    highlightedFavoriteId.value = stationId
    
    // Разворачиваем карточку
    expandedStations.value.add(stationId)
    
    // Перемещаем станцию в начало списка избранных
    stationsStore.moveStationToTop(stationId)
    
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
    }, 100)
  } else {
    // Если станция не в избранном, добавляем её
    try {
      const stationId = station.station_id || station.id
      const userId = user.value?.user_id
      
      if (stationId && userId) {
        await stationsStore.addFavorite(userId, stationId)
        
        // Разворачиваем карточку при добавлении в избранное
        expandedStations.value.add(stationId)
        
        // Перемещаем станцию в начало списка избранных
        stationsStore.moveStationToTop(stationId)
        
        // Подсвечиваем добавленную станцию
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
        }, 100)
        
        // Обновляем данные
        await refreshAfterAction()
      }
    } catch (error) {
      console.error('Ошибка при добавлении станции в избранное:', error)
    }
  }
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

    // Если найденная станция уже в избранном, подсвечиваем и разворачиваем её
    if (isStationFavorite(detailed)) {
      const stationId = detailed.station_id || detailed.id
      highlightedFavoriteId.value = stationId
      
      // Разворачиваем карточку при повторном нахождении
      expandedStations.value.add(stationId)
      
      // Перемещаем станцию в начало списка избранных
      stationsStore.moveStationToTop(stationId)
      
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
  const normalizedStatus = (status || '').toLowerCase()

  switch (normalizedStatus) {
    case 'active':
    case 'online':
      return 'status-active'
    case 'inactive':
    case 'offline':
      return 'status-inactive'
    case 'maintenance':
      return 'status-maintenance'
    default:
      return 'status-unknown'
  }
}

const getStatusText = (status) => {
  const normalizedStatus = (status || '').toLowerCase()

  switch (normalizedStatus) {
    case 'active':
    case 'online':
      return 'В сети'
    case 'inactive':
    case 'offline':
      return 'Не в сети'
    case 'maintenance':
      return 'Обслуживание'
    default:
      return 'Неизвестно'
  }
}

// Проверяем, является ли совпадение по адресу
const isAddressMatch = (station) => {
  if (!searchQuery.value) return false
  
  const query = searchQuery.value.trim().toLowerCase()
  const address = station.address || station.station_address || ''
  
  return address.toLowerCase().includes(query)
}

// Проверяем, является ли совпадение по нику
const isNicknameMatch = (station) => {
  if (!searchQuery.value) return false
  
  const query = searchQuery.value.trim().toLowerCase()
  const nickname = station.nickname || station.nik || ''
  
  return nickname.toLowerCase().includes(query)
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

// Функция для обработки ошибки логотипа
const handleLogoError = () => {
  console.error('Ошибка загрузки логотипа группы')
  orgUnitLogo.value = null
}


// Watch для отслеживания изменений userOrgUnitId
watch(
  () => userOrgUnitId.value,
  async (newId) => {
    if (newId && !userOrgUnit.value) {
      console.log('userOrgUnitId изменился, загружаем данные группы:', newId)
      await loadUserOrgUnit()
    } else if (!newId && user.value) {
      // Если пользователь есть, но нет org_unit_id, останавливаем индикатор загрузки
      console.log('У пользователя нет org_unit_id')
      isLoadingOrgUnit.value = false
    }
  },
  { immediate: true } // Выполнить сразу при монтировании, если значение уже есть
)

// Watch для отслеживания изменений пользователя
watch(
  () => user.value,
  async (newUser) => {
    if (newUser) {
      if (userOrgUnitId.value && !userOrgUnit.value) {
        console.log('Пользователь загружен, загружаем данные группы')
        await loadUserOrgUnit()
      } else if (!userOrgUnitId.value) {
        // Если у пользователя нет org_unit_id, останавливаем индикатор загрузки
        console.log('Пользователь загружен, но нет org_unit_id')
        isLoadingOrgUnit.value = false
      }
    }
  },
  { immediate: true }
)

// Жизненный цикл
onMounted(async () => {
  try {
    // Загружаем лимиты пользователя
    await auth.fetchUserLimits()
    
    await stationsStore.fetchFavoriteStations(user.value?.user_id)
    
    // Загружаем QR-станцию если есть параметры
    await loadQRStation()
    
    // Загружаем данные группы пользователя (если еще не загружены через watch)
    if (userOrgUnitId.value && !userOrgUnit.value) {
      await loadUserOrgUnit()
    }
    
    // 🔔 Подписываемся на обновления от WebSocket (для мобильных устройств)
    wsUnsubscribe.value = websocketNotificationService.onDataUpdate(async (updateInfo) => {
      console.log('📱 Dashboard: Получено обновление от WebSocket:', updateInfo)
      
      try {
        if (updateInfo.type === 'powerbank_returned') {
          // Обновляем данные после возврата powerbank
          console.log('📱 Dashboard: Обновляем данные после возврата powerbank')
          
          // Закрываем индикатор ожидания возврата
          isWaitingForReturn.value = false
          
          // Обновляем избранные станции
          await stationsStore.fetchFavoriteStations(user.value?.user_id)
          
          // Обновляем лимиты пользователя
          await auth.fetchUserLimits()
          
          showSuccess('Powerbank успешно возвращен! Данные обновлены.')
        } else if (updateInfo.type === 'page_visible') {
          // Пользователь вернулся на страницу - обновляем все данные
          console.log('📱 Dashboard: Пользователь вернулся на страницу, обновляем данные')
          
          await stationsStore.fetchFavoriteStations(user.value?.user_id)
          await auth.fetchUserLimits()
        } else if (updateInfo.type === 'network_restored') {
          // Сеть восстановлена - обновляем все данные
          console.log('📱 Dashboard: Сеть восстановлена, обновляем данные')
          
          await stationsStore.fetchFavoriteStations(user.value?.user_id)
          await auth.fetchUserLimits()
          
          showInfo('Соединение восстановлено. Данные обновлены.')
        }
      } catch (error) {
        console.error('❌ Dashboard: Ошибка при обновлении данных:', error)
      }
    })
    
    console.log('✅ Dashboard: Подписка на WebSocket обновления создана')
    
    // Не запускаем автоматическое обновление по таймеру
    // Обновление происходит только после действий и WebSocket уведомлений
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
  
  // 🔔 Отписываемся от WebSocket обновлений
  if (wsUnsubscribe.value) {
    wsUnsubscribe.value()
    console.log('✅ Dashboard: Отписка от WebSocket обновлений выполнена')
  }
  
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
  position: relative;
}

.search-input-wrapper {
  display: flex;
  gap: 10px;
  align-items: center;
  position: relative;
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

.empty-state-hint {
  color: #999;
  font-size: 0.9rem;
  font-style: italic;
  margin-top: 10px;
}

.stations-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 12px;
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
  grid-template-columns: 1fr;
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
  width: 100%;
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

  .search-section {
    margin-left: 0;
    margin-right: 0px;
  }

  .search-input-wrapper {
    flex-direction: column;
    width: 100%;
  }

  .search-input {
    width: 100%;
    box-sizing: border-box;
  }

  .search-dropdown {
    left: 0;
    right: 0;
    width: 100%;
  }
}


/* Стили для поиска */
.search-loading {
  position: absolute;
  right: 15px;
  top: 50%;
  transform: translateY(-50%);
}

.search-clear-btn {
  position: absolute;
  right: 15px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  font-size: 1.2rem;
  color: #999;
  cursor: pointer;
  padding: 5px;
  border-radius: 50%;
  transition: all 0.3s ease;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.search-clear-btn:hover {
  background: #f8f9fa;
  color: #666;
}

/* Стили для выпадающего списка поиска */
.search-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #e9ecef;
  border-radius: 10px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  z-index: 1000;
  max-height: 400px;
  overflow: hidden;
}

.search-dropdown-header {
  padding: 12px 16px;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
  font-size: 0.9rem;
  color: #666;
  font-weight: 600;
}

.search-dropdown-list {
  max-height: 320px;
  overflow-y: auto;
}

.search-dropdown-item {
  padding: 12px 16px;
  border-bottom: 1px solid #f1f3f4;
  cursor: pointer;
  transition: background-color 0.2s ease;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.search-dropdown-item:hover {
  background: #f8f9fa;
}

.search-dropdown-item:last-child {
  border-bottom: none;
}

.search-item-main {
  flex: 1;
  min-width: 0;
}

.search-item-title {
  font-weight: 600;
  color: #333;
  font-size: 0.95rem;
  margin-bottom: 2px;
}

.search-item-subtitle {
  color: #666;
  font-size: 0.85rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.search-item-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  flex-shrink: 0;
  margin-left: 12px;
}

.search-item-status {
  font-size: 0.75rem;
  padding: 2px 8px;
  border-radius: 12px;
  font-weight: 600;
  text-transform: uppercase;
}

.search-item-ports {
  font-size: 0.8rem;
  color: #666;
  font-weight: 600;
}

.search-no-results {
  padding: 20px;
  text-align: center;
  color: #666;
}

.search-no-results p {
  margin: 0;
  font-size: 0.9rem;
}

/* Подсветка адреса в результатах поиска */
.search-item-subtitle.highlighted-address {
  color: #667eea;
  font-weight: 600;
  background: rgba(102, 126, 234, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
  display: inline-block;
}

/* Подсветка ника в результатах поиска */
.search-item-title.highlighted-nickname {
  color: #667eea;
  font-weight: 700;
  background: rgba(102, 126, 234, 0.15);
  padding: 2px 6px;
  border-radius: 4px;
  display: inline-block;
}

/* Box ID под ником в результатах поиска */
.search-item-box-id {
  font-size: 0.75rem;
  color: #999;
  margin-top: 2px;
  font-family: monospace;
}

/* Оверлей ожидания возврата */
.return-waiting-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.return-waiting-content {
  background: white;
  border-radius: 20px;
  padding: 40px;
  text-align: center;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  animation: slideUp 0.3s ease-out;
}

@keyframes slideUp {
  from {
    transform: translateY(30px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.return-spinner {
  width: 60px;
  height: 60px;
  border: 5px solid #f0f0f0;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.return-waiting-text {
  font-size: 1.2rem;
  font-weight: 600;
  color: #333;
  margin: 0 0 10px 0;
}

.return-waiting-hint {
  font-size: 1rem;
  color: #666;
  margin: 0;
  font-style: italic;
}

</style>
