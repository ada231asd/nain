/**
 * Утилиты для синхронизации данных между фронтендом и бекендом
 * Централизованное управление обновлением данных после операций с аккумуляторами
 */

import { useStationsStore } from '../stores/stations'
import { useAdminStore } from '../stores/admin'
import { useAuthStore } from '../stores/auth'
import { pythonAPI } from '../api/pythonApi'

/**
 * Централизованное обновление всех данных после возврата аккумулятора
 * @param {Object} orderData - Данные заказа { station_id, user_id, powerbank_id }
 * @param {Object} user - Данные пользователя
 * @param {Function} loadUserOrders - Функция загрузки заказов пользователя
 */
export const refreshAllDataAfterReturn = async (orderData, user, loadUserOrders) => {
  try {
    console.log('🔄 Начинаем централизованное обновление данных после возврата аккумулятора')
    
    const stationsStore = useStationsStore()
    const adminStore = useAdminStore()
    const authStore = useAuthStore()
    
    // Параллельно обновляем все необходимые данные
    const updatePromises = []
    
    // 1. Обновляем данные станции
    if (orderData.station_id) {
      updatePromises.push(
        stationsStore.refreshStationData(orderData.station_id).catch(error => {
          console.warn('Не удалось обновить данные станции:', error)
        })
      )
    }
    
    // 2. Обновляем историю заказов пользователя
    if (loadUserOrders && typeof loadUserOrders === 'function') {
      updatePromises.push(
        loadUserOrders().catch(error => {
          console.warn('Не удалось обновить историю заказов:', error)
        })
      )
    }
    
    // 3. Обновляем лимиты пользователя
    updatePromises.push(
      authStore.fetchUserLimits().catch(error => {
        console.warn('Не удалось обновить лимиты пользователя:', error)
      })
    )
    
    // 4. Обновляем данные в админском store (если пользователь админ)
    if (user?.role && ['subgroup_admin', 'group_admin', 'service_admin'].includes(user.role)) {
      updatePromises.push(
        adminStore.fetchOrders().catch(error => {
          console.warn('Не удалось обновить заказы в админском store:', error)
        })
      )
    }
    
    // Ждем завершения всех обновлений
    await Promise.allSettled(updatePromises)
    
    console.log('✅ Централизованное обновление данных после возврата аккумулятора завершено')
    
  } catch (error) {
    console.error('Ошибка при централизованном обновлении данных после возврата аккумулятора:', error)
  }
}

/**
 * Централизованное обновление всех данных после взятия аккумулятора
 * @param {number} stationId - ID станции
 * @param {number} userId - ID пользователя
 * @param {Object} user - Данные пользователя
 * @param {Function} refreshFavorites - Функция обновления избранных станций
 */
export const refreshAllDataAfterBorrow = async (stationId, userId, user, refreshFavorites) => {
  try {
    console.log('🔄 Начинаем централизованное обновление данных после взятия аккумулятора')
    
    const stationsStore = useStationsStore()
    const adminStore = useAdminStore()
    const authStore = useAuthStore()
    
    // Параллельно обновляем все необходимые данные
    const updatePromises = []
    
    // 1. Обновляем данные станции
    updatePromises.push(
      stationsStore.refreshStationData(stationId).catch(error => {
        console.warn('Не удалось обновить данные станции:', error)
      })
    )
    
    // 2. Обновляем избранные станции
    if (refreshFavorites && typeof refreshFavorites === 'function') {
      updatePromises.push(
        refreshFavorites().catch(error => {
          console.warn('Не удалось обновить избранные станции:', error)
        })
      )
    }
    
    // 3. Обновляем лимиты пользователя
    updatePromises.push(
      authStore.fetchUserLimits().catch(error => {
        console.warn('Не удалось обновить лимиты пользователя:', error)
      })
    )
    
    // 4. Обновляем данные в админском store (если пользователь админ)
    if (user?.role && ['subgroup_admin', 'group_admin', 'service_admin'].includes(user.role)) {
      updatePromises.push(
        adminStore.fetchOrders().catch(error => {
          console.warn('Не удалось обновить заказы в админском store:', error)
        })
      )
    }
    
    // Ждем завершения всех обновлений
    await Promise.allSettled(updatePromises)
    
    console.log('✅ Централизованное обновление данных после взятия аккумулятора завершено')
    
  } catch (error) {
    console.error('Ошибка при централизованном обновлении данных после взятия аккумулятора:', error)
  }
}

/**
 * Обновление данных станции с получением актуальной информации об аккумуляторах
 * @param {number} stationId - ID станции
 * @returns {Object} Обновленные данные станции
 */
export const refreshStationWithPowerbanks = async (stationId) => {
  try {
    console.log('🔄 Обновляем данные станции с аккумуляторами:', stationId)
    
    const stationsStore = useStationsStore()
    
    // Получаем актуальные детали станции
    const stationResponse = await pythonAPI.getStation(stationId)
    let stationDetails = stationResponse?.data || stationResponse
    
    if (stationDetails && stationDetails.success && stationDetails.data) {
      stationDetails = stationDetails.data
    }
    
    // Получаем актуальные данные об аккумуляторах
    const powerbanksResponse = await pythonAPI.getStationPowerbanks(stationId)
    let powerbanksData = powerbanksResponse?.data || powerbanksResponse
    
    if (powerbanksData && powerbanksData.success && powerbanksData.data) {
      powerbanksData = powerbanksData.data
    }
    
    // Обновляем данные станции актуальной информацией о портах
    // ВАЖНО: Используем ТОЛЬКО данные из API powerbanks
    if (powerbanksData && powerbanksData.success) {
      // API возвращает: { success, available_powerbanks, count, free_slots, total_slots }
      const availablePowerbanks = powerbanksData.available_powerbanks || [];
      stationDetails.ports = availablePowerbanks;
      
      // Используем ТОЛЬКО актуальные данные из API powerbanks
      stationDetails.freePorts = powerbanksData.free_slots; // Пустые слоты для возврата
      stationDetails.totalPorts = powerbanksData.total_slots; // Всего слотов
      stationDetails.occupiedPorts = powerbanksData.count; // Powerbank'и в станции (можно взять)
      stationDetails.remain_num = powerbanksData.free_slots; // Обновляем remain_num актуальными данными
    } else {
      // Если нет данных об аккумуляторах, используем 0 (безопаснее чем неактуальный remain_num)
      const totalSlots = stationDetails.slots_declared || 20
      
      stationDetails.freePorts = 0
      stationDetails.totalPorts = totalSlots
      stationDetails.occupiedPorts = 0
      
      console.warn('⚠️ Не удалось получить актуальные данные о портах (dataSync). Используем заглушки.')
    }
    
    console.log('✅ Данные станции с аккумуляторами обновлены')
    return stationDetails
    
  } catch (error) {
    console.error('Ошибка при обновлении данных станции с аккумуляторами:', error)
    throw error
  }
}

/**
 * Проверка синхронизации данных между фронтендом и бекендом
 * @param {number} stationId - ID станции для проверки
 * @returns {Object} Результат проверки синхронизации
 */
export const checkDataSync = async (stationId) => {
  try {
    console.log('🔍 Проверяем синхронизацию данных для станции:', stationId)
    
    const stationsStore = useStationsStore()
    
    // Получаем данные станции из store
    const storeStation = stationsStore.stations.find(s => (s.station_id || s.id) === stationId)
    
    // Получаем актуальные данные с сервера
    const serverStation = await refreshStationWithPowerbanks(stationId)
    
    // Сравниваем данные
    const syncResult = {
      stationId,
      isSynced: true,
      differences: [],
      storeData: storeStation,
      serverData: serverStation
    }
    
    if (storeStation) {
      // Проверяем основные поля
      const fieldsToCheck = ['remain_num', 'freePorts', 'occupiedPorts', 'totalPorts']
      
      fieldsToCheck.forEach(field => {
        if (storeStation[field] !== serverStation[field]) {
          syncResult.isSynced = false
          syncResult.differences.push({
            field,
            storeValue: storeStation[field],
            serverValue: serverStation[field]
          })
        }
      })
    } else {
      syncResult.isSynced = false
      syncResult.differences.push({
        field: 'station_in_store',
        storeValue: 'not_found',
        serverValue: 'found'
      })
    }
    
    console.log('📊 Результат проверки синхронизации:', syncResult)
    return syncResult
    
  } catch (error) {
    console.error('Ошибка при проверке синхронизации данных:', error)
    return {
      stationId,
      isSynced: false,
      error: error.message,
      differences: []
    }
  }
}
