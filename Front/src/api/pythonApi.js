// src/api/pythonApi.js - Unified REST API client for Python backend

import apiClient from './client'

// Валидация параметров (reusing similar validation from extended)
const validateId = (id, name = 'ID') => {
  if (!id || (typeof id !== 'string' && typeof id !== 'number')) {
    throw new Error(`Invalid ${name}`)
  }
}

const validateData = (data, name = 'data') => {
  if (!data || typeof data !== 'object') {
    throw new Error(`Invalid ${name}`)
  }
}

// Helper to handle API responses and errors
const handleResponse = async (requestPromise, operation = 'operation') => {
  try {
    const res = await requestPromise
    return res  // apiClient already returns data
  } catch (error) {
    // Сохраняем стандартизированные поля ошибки из axios перехватчика
    if (error && (error.status !== undefined || error.code !== undefined)) {
      throw error
    }
    // Фолбэк, если пришел неожиданный формат ошибки
    throw {
      message: (error && error.message) || `Failed ${operation}`,
      status: (error && error.status) || 0,
      code: error && error.code,
      originalError: error
    }
  }
}

export const pythonAPI = {
  // СТАНЦИИ
  getStations: (params = {}) => {
    return handleResponse(apiClient.get('/stations', { params }), 'get stations')
  },
  // Привязки станция-повербанк с полями статусов/ошибок
  getStationPowerbanksDetailed: (params = {}) => {
    return handleResponse(apiClient.get('/station-powerbanks', { params }), 'get station-powerbanks detailed')
  },
  getStation: (id) => {
    validateId(id, 'station ID')
    return handleResponse(apiClient.get(`/stations/${id}`), 'get station')
  },
  getStationPowerbanks: (station_id, params = {}) => {
    validateId(station_id, 'station ID')
    return handleResponse(
      apiClient.get(`/borrow/stations/${station_id}/powerbanks`, { params }),
      'get station powerbanks'
    )
  },
  createStation: (data) => {
    validateData(data, 'station data')
    return handleResponse(apiClient.post('/stations', data), 'create station')
  },
  updateStation: (id, data) => {
    validateId(id, 'station ID')
    validateData(data, 'station data')
    return handleResponse(apiClient.put(`/stations/${id}`, data), 'update station')
  },
  deleteStation: (id) => {
    validateId(id, 'station ID')
    return handleResponse(apiClient.delete(`/stations/${id}`), 'delete station')
  },

  // ПОВЕРБАНКИ (полный CRUD)
  getPowerbanks: (params = {}) => handleResponse(apiClient.get('/powerbanks', { params }), 'get powerbanks'),
  getPowerbank: (id) => {
    validateId(id, 'powerbank ID')
    return handleResponse(apiClient.get(`/powerbanks/${id}`), 'get powerbank')
  },
  updatePowerbank: (id, data) => {
    validateId(id, 'powerbank ID')
    validateData(data, 'powerbank data')
    return handleResponse(apiClient.put(`/powerbanks/${id}`, data), 'update powerbank')
  },
  deletePowerbank: (id) => {
    validateId(id, 'powerbank ID')
    return handleResponse(apiClient.delete(`/powerbanks/${id}`), 'delete powerbank')
  },

  // ЗАКАЗЫ (полный CRUD)
  getOrders: (params = {}) => handleResponse(apiClient.get('/orders', { params }), 'get orders'),
  getOrder: (id) => {
    validateId(id, 'order ID')
    return handleResponse(apiClient.get(`/orders/${id}`), 'get order')
  },
  createOrder: (data) => {
    validateData(data, 'order data')
    return handleResponse(apiClient.post('/orders', data), 'create order')
  },
  updateOrder: (id, data) => {
    validateId(id, 'order ID')
    validateData(data, 'order data')
    return handleResponse(apiClient.put(`/orders/${id}`, data), 'update order')
  },
  deleteOrder: (id) => {
    validateId(id, 'order ID')
    return handleResponse(apiClient.delete(`/orders/${id}`), 'delete order')
  },

  // ПОЛЬЗОВАТЕЛИ
  getUsers: (params = {}) => handleResponse(apiClient.get('/users', { params }), 'get users'),
  getUser: (id) => {
    validateId(id, 'user ID')
    return handleResponse(apiClient.get(`/users/${id}`), 'get user')
  },
  getUserOrders: (id) => {
    validateId(id, 'user ID')
    return handleResponse(apiClient.get(`/users/${id}/orders`), 'get user orders')
  },
  createUser: (data) => {
    validateData(data, 'user data')
    return handleResponse(apiClient.post('/users', data), 'create user')
  },
  updateUser: (id, data) => {
    validateId(id, 'user ID')
    validateData(data, 'user data')
    return handleResponse(apiClient.put(`/users/${id}`, data), 'update user')
  },
  deleteUser: (id) => {
    validateId(id, 'user ID')
    return handleResponse(apiClient.delete(`/users/${id}`), 'delete user')
  },

  // МАССОВЫЙ ИМПОРТ ПОЛЬЗОВАТЕЛЕЙ
  downloadBulkImportTemplate: () => {
    return handleResponse(apiClient.get('/users/bulk-import/template', {
      responseType: 'blob'
    }), 'download bulk import template')
  },
  validateBulkImportFile: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return handleResponse(apiClient.post('/users/bulk-import/validate', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    }), 'validate bulk import file')
  },
  bulkImportUsers: (file, orgUnitId = null) => {
    const formData = new FormData()
    formData.append('file', file)
    if (orgUnitId) {
      formData.append('org_unit_id', orgUnitId)
    }
    return handleResponse(apiClient.post('/users/bulk-import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    }), 'bulk import users')
  },

  // ОРГАНИЗАЦИОННЫЕ ЕДИНИЦЫ (полный CRUD)
  getOrgUnits: (params = {}) => handleResponse(apiClient.get('/org-units', { params }), 'get org units'),
  getOrgUnit: (id) => {
    validateId(id, 'org unit ID')
    return handleResponse(apiClient.get(`/org-units/${id}`), 'get org unit')
  },
  // Получение логотипа группы
  getOrgUnitLogo: (logoUrl) => {
    if (!logoUrl) {
      throw new Error('Logo URL is required')
    }
    // Извлекаем имя файла из URL
    const filename = logoUrl.split('/').pop()
    return handleResponse(apiClient.get(`/logos/${filename}`, { responseType: 'blob' }), 'get org unit logo')
  },
  getOrgUnitStations: (id) => {
    validateId(id, 'org unit ID')
    return handleResponse(apiClient.get('/stations', { params: { org_unit_id: id } }), 'get org unit stations')
  },
  createOrgUnit: (data) => {
    validateData(data, 'org unit data')
    return handleResponse(apiClient.post('/org-units', data), 'create org unit')
  },
  updateOrgUnit: (id, data) => {
    validateId(id, 'org unit ID')
    validateData(data, 'org unit data')
    return handleResponse(apiClient.put(`/org-units/${id}`, data), 'update org unit')
  },
  deleteOrgUnit: (id) => {
    validateId(id, 'org unit ID')
    return handleResponse(apiClient.delete(`/org-units/${id}`), 'delete org unit')
  },

  // АДРЕСА (полный CRUD)
  getAddresses: (params = {}) => handleResponse(apiClient.get('/addresses', { params }), 'get addresses'),
  getAddress: (id) => {
    validateId(id, 'address ID')
    return handleResponse(apiClient.get(`/addresses/${id}`), 'get address')
  },
  createAddress: (data) => {
    validateData(data, 'address data')
    return handleResponse(apiClient.post('/addresses', data), 'create address')
  },
  updateAddress: (id, data) => {
    validateId(id, 'address ID')
    validateData(data, 'address data')
    return handleResponse(apiClient.put(`/addresses/${id}`, data), 'update address')
  },
  deleteAddress: (id) => {
    validateId(id, 'address ID')
    return handleResponse(apiClient.delete(`/addresses/${id}`), 'delete address')
  },

  // СЕКРЕТНЫЕ КЛЮЧИ СТАНЦИЙ (полный CRUD)
  getStationSecretKeys: (params = {}) => handleResponse(apiClient.get('/station-secret-keys', { params }), 'get station secret keys'),
  getStationSecretKey: (id) => {
    validateId(id, 'secret key ID')
    return handleResponse(apiClient.get(`/station-secret-keys/${id}`), 'get station secret key')
  },
  createStationSecretKey: (data) => {
    validateData(data, 'secret key data')
    return handleResponse(apiClient.post('/station-secret-keys', data), 'create station secret key')
  },
  updateStationSecretKey: (id, data) => {
    validateId(id, 'secret key ID')
    validateData(data, 'secret key data')
    return handleResponse(apiClient.put(`/station-secret-keys/${id}`, data), 'update station secret key')
  },
  deleteStationSecretKey: (id) => {
    validateId(id, 'secret key ID')
    return handleResponse(apiClient.delete(`/station-secret-keys/${id}`), 'delete station secret key')
  },

  // РОЛИ ПОЛЬЗОВАТЕЛЕЙ (полный CRUD)
  getUserRoles: (params = {}) => handleResponse(apiClient.get('/user-roles', { params }), 'get user roles'),
  getUserRole: (id) => {
    validateId(id, 'role ID')
    return handleResponse(apiClient.get(`/user-roles/${id}`), 'get user role')
  },
  createUserRole: (data) => {
    validateData(data, 'role data')
    return handleResponse(apiClient.post('/user-roles', data), 'create user role')
  },
  updateUserRole: (id, data) => {
    validateId(id, 'role ID')
    validateData(data, 'role data')
    return handleResponse(apiClient.put(`/user-roles/${id}`, data), 'update user role')
  },
  deleteUserRole: (id) => {
    validateId(id, 'role ID')
    return handleResponse(apiClient.delete(`/user-roles/${id}`), 'delete user role')
  },

  // АВТОРИЗАЦИЯ И РЕГИСТРАЦИЯ
  register: (data) => {
    validateData(data, 'registration data')
    return handleResponse(apiClient.post('/auth/register', data), 'register user')
  },
  login: (data) => {
    validateData(data, 'login data')
    return handleResponse(apiClient.post('/auth/login', data), 'login user')
  },
  getProfile: () => handleResponse(apiClient.get('/auth/profile'), 'get profile'),
  updateProfile: (data) => {
    validateData(data, 'profile data')
    return handleResponse(apiClient.put('/auth/profile', data), 'update profile')
  },
  // logout: () => handleResponse(apiClient.post('/logout'), 'logout user'), // JWT logout происходит на клиенте

  // ДЕЙСТВИЯ
  requestBorrowPowerbank: (data) => {
    validateData(data, 'borrow data')
    const { station_id, user_id, slot_number } = data
    
    // Проверяем обязательные поля
    if (!station_id) {
      throw new Error('Отсутствует обязательное поле: station_id')
    }
    if (!user_id) {
      throw new Error('Отсутствует обязательное поле: user_id')
    }
    if (!slot_number) {
      throw new Error('Отсутствует обязательное поле: slot_number')
    }
    
    return handleResponse(apiClient.post(`/borrow/stations/${station_id}/request`, {
      user_id,
      slot_number
    }, { timeout: 90000 }), 'request borrow powerbank')
  },
  requestBorrowPowerbankGet: (params) => {
    return handleResponse(apiClient.get('/borrow-powerbank', { params }), 'request borrow powerbank (GET)')
  },
  requestOptimalBorrowPowerbank: ({ station_id, user_id }) => {
    validateId(station_id, 'station ID')
    validateId(user_id, 'user ID')
    return handleResponse(
      apiClient.post(`/borrow/stations/${station_id}/request-optimal`, { user_id }, { timeout: 90000 }),
      'request optimal borrow powerbank'
    )
  },
  forceExtractPowerbank: (data) => {
    validateData(data, 'force extract data')
    return handleResponse(apiClient.post('/force-extract-powerbank', data), 'force extract powerbank')
  },
  checkPowerbankCompatibility: (stationId) => {
    validateId(stationId, 'station ID')
    return handleResponse(apiClient.post(`/check-powerbank-compatibility/${stationId}`), 'check powerbank compatibility')
  },
  returnPowerbank: (data) => {
    validateData(data, 'return data')
    return handleResponse(apiClient.post('/return-powerbank', data), 'return powerbank')
  },
  returnPowerbankGet: (params) => {
    return handleResponse(apiClient.get('/return-powerbank', { params }), 'return powerbank (GET)')
  },

  // ИЗБРАННЫЕ СТАНЦИИ
  getUserFavoriteStations: (userId) => {
    validateId(userId, 'user ID')
    return handleResponse(apiClient.get(`/user-favorites?user_id=${userId}`), 'get user favorite stations')
  },
  addFavoriteStation: (data) => {
    validateData(data, 'favorite data')
    return handleResponse(apiClient.post('/user-favorites', data), 'add favorite station')
  },
  removeFavoriteStation: (favoriteId) => {
    validateId(favoriteId, 'favorite ID')
    return handleResponse(apiClient.delete(`/user-favorites/${favoriteId}`), 'remove favorite station')
  },

  // АДМИНИСТРАТИВНЫЕ ФУНКЦИИ
  getPendingUsers: () => handleResponse(apiClient.get('/admin/pending-users'), 'get pending users'),
  approveUser: async (userId) => {
    validateId(userId, 'user ID')
    try {
      // Сначала получаем данные пользователя
      const response = await handleResponse(apiClient.get(`/users/${userId}`), 'get user data')
      const userData = response.data || response
      
      // Обновляем только статус, сохраняя остальные данные
      const updateData = {
        fio: userData.fio || '',
        phone_e164: userData.phone_e164 || '',
        email: userData.email || '',
        role: userData.role || 'user',
        parent_org_unit_id: userData.parent_org_unit_id || '',
        status: 'active' // Меняем статус на активный
      }
      
      return handleResponse(apiClient.put(`/users/${userId}`, updateData), 'approve user')
    } catch (error) {
      throw new Error(`Failed to approve user: ${error.message}`)
    }
  },
  rejectUser: async (userId) => {
    validateId(userId, 'user ID')
    try {
      // Сначала получаем данные пользователя
      const response = await handleResponse(apiClient.get(`/users/${userId}`), 'get user data')
      const userData = response.data || response
      
      // Обновляем только статус, сохраняя остальные данные
      const updateData = {
        fio: userData.fio || '',
        phone_e164: userData.phone_e164 || '',
        email: userData.email || '',
        role: userData.role || 'user',
        parent_org_unit_id: userData.parent_org_unit_id || '',
        status: 'blocked' // Меняем статус на заблокированный
      }
      
      return handleResponse(apiClient.put(`/users/${userId}`, updateData), 'reject user')
    } catch (error) {
      throw new Error(`Failed to reject user: ${error.message}`)
    }
  },
  forceEjectPowerbank: (data) => {
    validateData(data, 'force eject data')
    return handleResponse(apiClient.post('/admin/force-eject-powerbank', data), 'force eject powerbank')
  },

  // УПРАВЛЕНИЕ ГРОМКОСТЬЮ
  queryVoiceVolume: (stationId) => {
    validateId(stationId, 'station ID')
    return handleResponse(apiClient.post('/query-voice-volume', { station_id: stationId }), 'query voice volume')
  },
  getVoiceVolume: (stationId) => {
    validateId(stationId, 'station ID')
    return handleResponse(apiClient.get(`/query-voice-volume/station/${stationId}`), 'get voice volume')
  },
  setVoiceVolume: (data) => {
    validateData(data, 'voice volume data')
    const { station_id } = data
    const volume_level = Number(data.volume_level)
    if (!station_id) {
      throw new Error('Отсутствует обязательное поле: station_id')
    }
    if (Number.isNaN(volume_level)) {
      throw new Error('Отсутствует обязательное поле: volume_level')
    }
    return handleResponse(apiClient.post('/set-voice-volume', data), 'set voice volume')
  },

  // УПРАВЛЕНИЕ АДРЕСОМ СЕРВЕРА
  queryServerAddress: (stationId) => {
    validateId(stationId, 'station ID')
    return handleResponse(apiClient.post('/query-server-address', { station_id: stationId }), 'query server address')
  },
  getServerAddress: (stationId) => {
    validateId(stationId, 'station ID')
    return handleResponse(apiClient.get(`/query-server-address/station/${stationId}`), 'get server address')
  },
  setServerAddress: (data) => {
    validateData(data, 'server address data')
    const { station_id, server_address } = data
    let { server_port, heartbeat_interval } = data
    if (!station_id) {
      throw new Error('Отсутствует обязательное поле: station_id')
    }
    if (!server_address || !String(server_address).trim()) {
      throw new Error('Адрес сервера не может быть пустым')
    }
    if (server_port === undefined || server_port === null || server_port === '') {
      throw new Error('Отсутствует обязательное поле: server_port')
    }
    if (heartbeat_interval === undefined || heartbeat_interval === null) {
      throw new Error('Отсутствует обязательное поле: heartbeat_interval')
    }

    // Backend expects port as string, heartbeat in [1..255]
    const normalizedPayload = {
      station_id,
      server_address: String(server_address).trim(),
      server_port: String(server_port).trim(),
      heartbeat_interval: Math.max(1, Math.min(255, Number(heartbeat_interval)))
    }

    return handleResponse(apiClient.post('/set-server-address', normalizedPayload), 'set server address')
  },

  // ИНВЕНТАРЬ СТАНЦИИ
  queryInventory: (stationId) => {
    validateId(stationId, 'station ID')
    return handleResponse(apiClient.post('/query-inventory', { station_id: stationId }), 'query inventory')
  },
  getStationInventory: (stationId) => {
    validateId(stationId, 'station ID')
    return handleResponse(apiClient.get(`/query-inventory/station/${stationId}`), 'get station inventory')
  },

  // ПЕРЕЗАГРУЗКА СТАНЦИИ
  restartCabinet: (data) => {
    validateData(data, 'restart cabinet data')
    const { station_id } = data
    if (!station_id) {
      throw new Error('Отсутствует обязательное поле: station_id')
    }
    return handleResponse(apiClient.post('/restart-cabinet', data), 'restart cabinet')
  },

  // УСТАРЕВШАЯ ФУНКЦИЯ: используйте returnError() вместо этой
  // Оставлена для обратной совместимости
  reportPowerbankError: (data) => {
    console.warn('⚠️ reportPowerbankError() устарела, используйте returnError() вместо неё')
    // Преобразуем старый формат в новый и вызываем returnError
    return pythonAPI.returnError({
      station_id: data.station_id,
      user_id: data.user_id,
      error_type_id: data.error_type || data.error_type_id,
      timeout_seconds: data.timeout_seconds || 30
    })
  },

  // ВОЗВРАТ С ОШИБКОЙ (долгий HTTP запрос ~11 секунд)
  returnDamaged: (data) => {
    validateData(data, 'return damaged data')
    const { station_id, user_id, error_type } = data

    if (!station_id) {
      throw new Error('Отсутствует обязательное поле: station_id')
    }
    if (!user_id) {
      throw new Error('Отсутствует обязательное поле: user_id')
    }
    if (!error_type) {
      throw new Error('Отсутствует обязательное поле: error_type')
    }

    const payload = {
      station_id,
      user_id,
      error_type
    }

    // Долгий HTTP запрос: сервер ждет подтверждения от станции до ~11 секунд
    return handleResponse(
      apiClient.post('/return-damage', payload, { timeout: 15000 }),
      'return damaged powerbank'
    )
  },

  // ПОЛУЧЕНИЕ ТИПОВ ОШИБОК ПОВЕРБАНКОВ
  getPowerbankErrorTypes: () => {
    return handleResponse(apiClient.get('/powerbank-error-types'), 'get powerbank error types')
  },

  // ВОЗВРАТ С ОШИБКОЙ (новый API с типами из БД и Long Polling)
  returnError: (data) => {
    validateData(data, 'return error data')
    const { station_id, user_id, error_type_id, timeout_seconds = 30 } = data

    if (!station_id) {
      throw new Error('Отсутствует обязательное поле: station_id')
    }
    if (!user_id) {
      throw new Error('Отсутствует обязательное поле: user_id')
    }
    if (!error_type_id) {
      throw new Error('Отсутствует обязательное поле: error_type_id')
    }

    const payload = {
      station_id,
      user_id,
      error_type_id,
      timeout_seconds
    }

    // Long Polling: сервер ждет вставки повербанка до timeout_seconds секунд
    return handleResponse(
      apiClient.post('/return-error', payload, { timeout: (timeout_seconds + 5) * 1000 }),
      'return error powerbank with long polling'
    )
  },

  // ОТЧЕТЫ ОБ АНОМАЛИЯХ СЛОТОВ
  getSlotAbnormalReports: (params = {}) => {
    const queryParams = new URLSearchParams()
    if (params.limit) queryParams.append('limit', params.limit)
    if (params.start_date) queryParams.append('start_date', params.start_date)
    if (params.end_date) queryParams.append('end_date', params.end_date)
    
    const queryString = queryParams.toString()
    const url = queryString ? `/slot-abnormal-reports?${queryString}` : '/slot-abnormal-reports'
    return handleResponse(apiClient.get(url), 'get slot abnormal reports')
  },

  getStationSlotAbnormalReports: (stationId, limit = 50) => {
    validateId(stationId, 'station ID')
    return handleResponse(
      apiClient.get(`/slot-abnormal-reports/stations/${stationId}?limit=${limit}`),
      'get station slot abnormal reports'
    )
  },

  getSlotAbnormalReportsByEventType: (eventType, limit = 50) => {
    return handleResponse(
      apiClient.get(`/slot-abnormal-reports/event-type/${eventType}?limit=${limit}`),
      'get slot abnormal reports by event type'
    )
  },

  getSlotAbnormalReportsStatistics: () => {
    return handleResponse(apiClient.get('/slot-abnormal-reports/statistics'), 'get slot abnormal reports statistics')
  },

  deleteSlotAbnormalReport: (reportId) => {
    validateId(reportId, 'report ID')
    return handleResponse(apiClient.delete(`/slot-abnormal-reports/${reportId}`), 'delete slot abnormal report')
  },

  // ПОЛЬЗОВАТЕЛЬСКИЕ ПАУЭРБАНКИ
  getUserPowerbanks: () => handleResponse(apiClient.get('/user/powerbanks'), 'get user powerbanks'),
  borrowPowerbank: (stationId) => {
    validateId(stationId, 'station ID')
    return handleResponse(apiClient.post(`/borrow/stations/${stationId}/borrow`, undefined, { timeout: 90000 }), 'borrow powerbank')
  },
  returnPowerbank: (stationId, powerbankId) => {
    validateId(stationId, 'station ID')
    validateId(powerbankId, 'powerbank ID')
    return handleResponse(apiClient.post(`/return/stations/${stationId}/powerbanks/${powerbankId}`, undefined, { timeout: 90000 }), 'return powerbank')
  },
  waitReturnConfirmation: (payload) => {
    if (!payload || typeof payload !== 'object') {
      throw new Error('Invalid wait confirmation payload')
    }
    const { station_id, user_id } = payload
    if (!station_id || !user_id) {
      throw new Error('waitReturnConfirmation requires station_id and user_id')
    }
    const timeout = Math.max(1000, Math.min(60000, (payload.timeout_seconds || 10) * 1000))
    return handleResponse(apiClient.post('/return/wait-confirmation', payload, { timeout }), 'wait return confirmation')
  },

  // ВОЗВРАТ С ОШИБКОЙ
  requestErrorReturn: (user_id, station_id, error_type) => {
    validateId(user_id, 'user ID')
    validateId(station_id, 'station ID')
    validateId(error_type, 'error type')
    return handleResponse(
      apiClient.post('/return/error', {
        user_id: parseInt(user_id),
        station_id: parseInt(station_id),
        error_type: parseInt(error_type)
      }),
      'request error return'
    )
  },

  getPendingErrorReturns: (user_id = null) => {
    const params = user_id ? { user_id: parseInt(user_id) } : {}
    return handleResponse(apiClient.get('/return/error/pending', { params }), 'get pending error returns')
  },

  cancelErrorReturn: (user_id) => {
    validateId(user_id, 'user ID')
    return handleResponse(apiClient.delete(`/return/error/pending/${user_id}`), 'cancel error return')
  },

  // Алиас для getPowerbankErrorTypes для обратной совместимости
  getErrorTypes: () => {
    return pythonAPI.getPowerbankErrorTypes()
  },

  cleanupExpiredErrorReturns: (max_age_minutes = 30) => {
    return handleResponse(
      apiClient.post('/return/error/cleanup', { max_age_minutes }),
      'cleanup expired error returns'
    )
  },

  // ДРУГОЕ
  getConnections: () => handleResponse(apiClient.get('/connections'), 'get connections')
}

export default pythonAPI
