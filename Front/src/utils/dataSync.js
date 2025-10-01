/**
 * Утилиты для синхронизации данных между фронтендом и бекендом
 * Централизованное управление обновлением данных после операций с павербанками
 */

import { useStationsStore } from '../stores/stations'
import { useAdminStore } from '../stores/admin'
import { pythonAPI } from '../api/pythonApi'

/**
 * Централизованное обновление всех данных после возврата павербанка
 * @param {Object} orderData - Данные заказа { station_id, user_id, powerbank_id }
 * @param {Object} user - Данные пользователя
 * @param {Function} loadUserOrders - Функция загрузки заказов пользователя
 */
export const refreshAllDataAfterReturn = async (orderData, user, loadUserOrders) => {
  try {
    console.log('🔄 Начинаем централизованное обновление данных после возврата павербанка')
    
    const stationsStore = useStationsStore()
    const adminStore = useAdminStore()
    
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
    
    // 3. Обновляем данные в админском store (если пользователь админ)
    if (user?.role && ['subgroup_admin', 'group_admin', 'service_admin'].includes(user.role)) {
      updatePromises.push(
        adminStore.fetchOrders().catch(error => {
          console.warn('Не удалось обновить заказы в админском store:', error)
        })
      )
    }
    
    // Ждем завершения всех обновлений
    await Promise.allSettled(updatePromises)
    
    console.log('✅ Централизованное обновление данных после возврата павербанка завершено')
    
  } catch (error) {
    console.error('Ошибка при централизованном обновлении данных после возврата павербанка:', error)
  }
}

/**
 * Централизованное обновление всех данных после взятия павербанка
 * @param {number} stationId - ID станции
 * @param {number} userId - ID пользователя
 * @param {Object} user - Данные пользователя
 * @param {Function} refreshFavorites - Функция обновления избранных станций
 */
export const refreshAllDataAfterBorrow = async (stationId, userId, user, refreshFavorites) => {
  try {
    console.log('🔄 Начинаем централизованное обновление данных после взятия павербанка')
    
    const stationsStore = useStationsStore()
    const adminStore = useAdminStore()
    
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
    
    // 3. Обновляем данные в админском store (если пользователь админ)
    if (user?.role && ['subgroup_admin', 'group_admin', 'service_admin'].includes(user.role)) {
      updatePromises.push(
        adminStore.fetchOrders().catch(error => {
          console.warn('Не удалось обновить заказы в админском store:', error)
        })
      )
    }
    
    // Ждем завершения всех обновлений
    await Promise.allSettled(updatePromises)
    
    console.log('✅ Централизованное обновление данных после взятия павербанка завершено')
    
  } catch (error) {
    console.error('Ошибка при централизованном обновлении данных после взятия павербанка:', error)
  }
}

/**
 * Обновление данных станции с получением актуальной информации о павербанках
 * @param {number} stationId - ID станции
 * @returns {Object} Обновленные данные станции
 */
export const refreshStationWithPowerbanks = async (stationId) => {
  try {
    console.log('🔄 Обновляем данные станции с павербанками:', stationId)
    
    const stationsStore = useStationsStore()
    
    // Получаем актуальные детали станции
    const stationResponse = await pythonAPI.getStation(stationId)
    let stationDetails = stationResponse?.data || stationResponse
    
    if (stationDetails && stationDetails.success && stationDetails.data) {
      stationDetails = stationDetails.data
    }
    
    // Получаем актуальные данные о павербанках
    const powerbanksResponse = await pythonAPI.getStationPowerbanks(stationId)
    let powerbanksData = powerbanksResponse?.data || powerbanksResponse
    
    if (powerbanksData && powerbanksData.success && powerbanksData.data) {
      powerbanksData = powerbanksData.data
    }
    
    // Обновляем данные станции актуальной информацией о портах
    if (powerbanksData && Array.isArray(powerbanksData)) {
      stationDetails.ports = powerbanksData
      stationDetails.freePorts = powerbanksData.filter(port => port.status === 'free').length
      stationDetails.totalPorts = powerbanksData.length
      stationDetails.occupiedPorts = powerbanksData.filter(port => port.status === 'occupied').length
    } else {
      // Если нет данных о павербанках, создаем числовые свойства на основе remain_num
      const totalSlots = stationDetails.slots_declared || 20
      const freeSlots = stationDetails.remain_num || 0
      const occupiedSlots = totalSlots - freeSlots
      
      stationDetails.freePorts = freeSlots
      stationDetails.totalPorts = totalSlots
      stationDetails.occupiedPorts = occupiedSlots
    }
    
    console.log('✅ Данные станции с павербанками обновлены')
    return stationDetails
    
  } catch (error) {
    console.error('Ошибка при обновлении данных станции с павербанками:', error)
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
