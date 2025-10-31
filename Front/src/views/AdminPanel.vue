<template>
  <div class="admin-panel">
    <!-- Основной контент -->
    <main class="admin-main">
      <div class="admin-layout">
        <AdminSidebar 
          :active-tab="activeTab"
          @tab-change="activeTab = $event"
          @go-home="goToHome"
        />

        <div class="admin-content">
          <div class="tab-content">

            <!-- Управление пользователями -->
            <div v-if="activeTab === 'users'" class="tab-pane">
              <UsersTable
                :users="users"
                :org-units="orgUnits"
                @bulk-import="() => showBulkImportModal = true"
                @user-updated="handleUserUpdated"
                @approve-user="approveUser"
                @block-user="blockUser"
                @unblock-user="unblockUser"
                @delete-user="deleteUser"
                @restore-user="restoreUser"
                @bulk-approve="bulkApproveUsers"
                @bulk-block="bulkBlockUsers"
                @bulk-delete="bulkDeleteUsers"
              />
            </div>

            <!-- Управление станциями -->
            <div v-if="activeTab === 'stations'" class="tab-pane">
              <StationsTable 
                :stations="stations"
                :org-units="orgUnits"
                @add-station="() => { showAddStationModal = true }"
                @view-powerbanks="openPowerbanks"
                @restart-station="restartStation"
                @delete-station="deleteStation"
                @restore-station="restoreStation"
                @station-updated="refreshAfterAction"
              />
            </div>

            <!-- Управление аккумуляторами -->
            <div v-if="activeTab === 'powerbanks'" class="tab-pane">
              <PowerbanksTable
                :powerbanks="adminStore.powerbanks"
                :org-units="orgUnits"
              />
            </div>

            <!-- Управление группами -->
            <div v-if="activeTab === 'org-units'" class="tab-pane">
              <OrgUnitsTable
                :org-units="orgUnits"
                @add-org-unit="() => { editingOrgUnit = null; showAddOrgUnitModal = true }"
                @edit="editOrgUnit"
                @delete="deleteOrgUnit"
                @restore="restoreOrgUnit"
                @view-stations="viewOrgUnitStations"
                @view-details="viewOrgUnitDetails"
              />
            </div>

            <!-- Все заказы -->
            <div v-if="activeTab === 'orders'" class="tab-pane">
              <OrdersTable
                :orders="orders"
                :org-units="orgUnits"
                :is-loading="isLoading"
                @refresh="refreshOrders"
              />
            </div>

            <!-- Отчеты об аномалиях слотов -->
            <div v-if="activeTab === 'slot-abnormal-reports'" class="tab-pane">
              <SlotAbnormalReports :stations="stations" :active-tab="activeTab" />
            </div>

            <!-- Статистика -->
            <div v-if="activeTab === 'stats'" class="tab-pane">
              <h2>Статистика сервиса</h2>
              
              <div class="stats-grid">
                <div class="stat-card">
                  <h3>Общая статистика</h3>
                  <div class="stat-item">
                    <span class="stat-label">Всего станций:</span>
                    <span class="stat-value">{{ totalStations }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">Активных станций:</span>
                    <span class="stat-value">{{ activeStations.length }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">Всего групп:</span>
                    <span class="stat-value">{{ totalOrgUnits }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">Всего заказов:</span>
                    <span class="stat-value">{{ totalOrders }}</span>
                  </div>
                </div>

                <div class="stat-card">
                  <h3>Пользователи</h3>
                  <div class="stat-item">
                    <span class="stat-label">Всего пользователей:</span>
                    <span class="stat-value">{{ totalUsers }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">Ожидают подтверждения:</span>
                    <span class="stat-value">{{ pendingUsers.length }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">Подтверждены:</span>
                    <span class="stat-value">{{ totalUsers - pendingUsers.length }}</span>
                  </div>
                </div>

                <div class="stat-card">
                  <h3>Активность</h3>
                  <div class="stat-item">
                    <span class="stat-label">Заказов сегодня:</span>
                    <span class="stat-value">{{ todayOrders.length }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">Заказов за неделю:</span>
                    <span class="stat-value">{{ weekOrders.length }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">Заказов за месяц:</span>
                    <span class="stat-value">{{ monthOrders.length }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- Модальные окна -->
    <BulkImportModal
      :is-visible="showBulkImportModal"
      :org-units="orgUnits"
      @close="showBulkImportModal = false"
      @import-completed="handleBulkImportCompleted"
    />

    <AddStationModal 
      :is-visible="showAddStationModal"
      @close="closeStationModal"
      @station-added="handleStationAdded"
      @station-edited="handleStationEdited"
      @station-activation-required="handleStationActivationRequired"
    />
    
    <StationActivationModal 
      :is-visible="showStationActivationModal"
      :station="stationToActivate"
      @close="() => { showStationActivationModal = false; stationToActivate = null }"
      @station-activated="handleStationActivated"
    />
    

    <StationPowerbanksModal
      :is-visible="showPowerbanksModal"
      :station="selectedStation"
      :powerbanks="selectedStationPowerbanks"
      :is-borrowing="isBorrowing"
      @close="closePowerbanks"
      @borrow-powerbank="borrowPowerbank"
      @force-eject-powerbank="forceEjectPowerbank"
    />


    <StationQRModal
      :show="showStationQRModal"
      :station="selectedStationForQR"
      @close="() => { showStationQRModal = false; selectedStationForQR = null }"
    />

    <!-- Модальные окна для групп -->
    <AddOrgUnitModal 
      :is-visible="showAddOrgUnitModal"
      :org-unit="editingOrgUnit"
      @close="closeOrgUnitModal"
      @org-unit-added="handleOrgUnitAdded"
      @org-unit-edited="handleOrgUnitEdited"
    />
    
    <OrgUnitStationsModal
      :is-visible="showOrgUnitStationsModal"
      :org-unit="selectedOrgUnit"
      @close="closeOrgUnitStationsModal"
    />

    <OrgUnitDetailsModal
      :is-visible="showOrgUnitDetailsModal"
      :org-unit="selectedOrgUnit"
      :auto-edit="autoEditOrgUnit"
      @close="closeOrgUnitDetailsModal"
      @updated="handleOrgUnitUpdated"
      @view-stations="viewOrgUnitStations"
    />

    <!-- New User History Modal -->
    <div v-if="showUserHistoryModal" class="modal-overlay" @click="closeUserHistoryModal">
      <div class="modal-content" @click.stop>
        <h2>История пользователя: {{ selectedUser?.login || 'N/A' }}</h2>
        <div class="history-list">
          <div v-for="(log, index) in selectedUserHistory" :key="index" class="history-item">
            <p><strong>{{ formatDate(log.timestamp) }}:</strong> {{ log.message || 'No message' }}</p>
          </div>
          <div v-if="selectedUserHistory.length === 0">Нет записей в истории.</div>
        </div>
        <button @click="closeUserHistoryModal" class="btn-close">Закрыть</button>
      </div>
    </div>

    <!-- Loading overlay -->
    <div v-if="isLoading" class="loading-overlay">
      <div class="loading-spinner"></div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAdminStore } from '../stores/admin'
import { useAuthStore } from '../stores/auth'
import { pythonAPI } from '../api/pythonApi'
import { formatMoscowTime } from '../utils/timeUtils'
import { showSuccess, showError, showWarning, showInfo, showConfirm } from '../utils/notifications'



import BulkImportModal from '../components/BulkImportModal.vue'
import AddStationModal from '../components/AddStationModal.vue'
import StationPowerbanksModal from '../components/StationPowerbanksModal.vue'
import StationActivationModal from '../components/StationActivationModal.vue'
 
import AddOrgUnitModal from '../components/AddOrgUnitModal.vue'
import OrgUnitStationsModal from '../components/OrgUnitStationsModal.vue'
import OrgUnitDetailsModal from '../components/OrgUnitDetailsModal.vue'
import SlotAbnormalReports from '../components/SlotAbnormalReports.vue'
import StationQRModal from '../components/StationQRModal.vue'
import StationsTable from '../components/AdminComponents/StationsTable.vue'
import UsersTable from '../components/AdminComponents/UsersTable.vue'
import OrgUnitsTable from '../components/AdminComponents/OrgUnitsTable.vue'
import PowerbanksTable from '../components/AdminComponents/PowerbanksTable.vue'
import OrdersTable from '../components/AdminComponents/OrdersTable.vue'
import AdminSidebar from '../components/AdminComponents/AdminSidebar.vue'

const router = useRouter()
const adminStore = useAdminStore()
const authStore = useAuthStore()

// Состояние
const activeTab = ref('users')

// Модальные окна
const showBulkImportModal = ref(false)
const showAddStationModal = ref(false)
const showStationActivationModal = ref(false)
const stationToActivate = ref(null)
const showPowerbanksModal = ref(false)
const selectedStation = ref(null)
const selectedStationPowerbanks = ref([])
const isBorrowing = ref(false)
const showStationQRModal = ref(false)
const selectedStationForQR = ref(null)


// Модальные окна для групп
const showAddOrgUnitModal = ref(false)
const editingOrgUnit = ref(null)
const showOrgUnitStationsModal = ref(false)
const showOrgUnitDetailsModal = ref(false)
const selectedOrgUnit = ref(null)
const autoEditOrgUnit = ref(false)

// Глобальное уведомление, если сервер не отвечает
// Удалено - больше не используется




// Данные из store
const users = computed(() => adminStore.users)
const stations = computed(() => adminStore.stations)
const orders = computed(() => adminStore.orders)
const orgUnits = computed(() => adminStore.orgUnits)
const isLoading = computed(() => adminStore.isLoading)
const totalUsers = computed(() => adminStore.totalUsers)
const totalStations = computed(() => adminStore.totalStations)
const totalOrders = computed(() => adminStore.totalOrders)
const totalOrgUnits = computed(() => adminStore.totalOrgUnits)
const pendingUsers = computed(() => adminStore.pendingUsers)
const activeStations = computed(() => adminStore.activeStations)
const todayOrders = computed(() => adminStore.todayOrders)

const weekOrders = computed(() => {
  const weekAgo = new Date()
  weekAgo.setDate(weekAgo.getDate() - 7)
  return orders.value.filter(order => new Date(order.created_at) >= weekAgo)
})

const monthOrders = computed(() => {
  const monthAgo = new Date()
  monthAgo.setMonth(monthAgo.getMonth() - 1)
  return orders.value.filter(order => new Date(order.created_at) >= monthAgo)
})


const formatDate = (date) => {
  return new Date(date).toLocaleDateString('ru-RU')
}

// Методы

const refreshOrders = async () => {
  try {
    await adminStore.fetchOrders()
  } catch (error) {
    console.error('Ошибка при обновлении заказов:', error)
  }
}

const formatTime = (timestamp) => formatMoscowTime(timestamp, {
  day: '2-digit',
  month: '2-digit',
  hour: '2-digit',
  minute: '2-digit'
})

// User management methods
const deleteUser = async (deleteData) => {
  // deleteData может быть объектом { userId, hardDelete, userName } или просто userId (для обратной совместимости)
  const userId = typeof deleteData === 'object' ? deleteData.userId : deleteData
  const hardDelete = typeof deleteData === 'object' ? deleteData.hardDelete : false
  const userName = typeof deleteData === 'object' ? deleteData.userName : ''
  
  const confirmMessage = hardDelete 
    ? `Вы уверены, что хотите НАВСЕГДА удалить пользователя "${userName}"?\n\nЭто действие необратимо!`
    : `Вы уверены, что хотите удалить пользователя "${userName || 'этого'}"?`
    
  if (await showConfirm(confirmMessage, hardDelete ? 'Удалить навсегда' : 'Удалить', 'Отмена')) {
    try {
      await adminStore.deleteUser(userId, hardDelete)
      if (hardDelete) {
        showSuccess('Пользователь удалён навсегда')
      } else {
        showSuccess('Пользователь успешно удалён')
      }
      await refreshAfterAction()
    } catch (error) {
      console.error('Ошибка при удалении пользователя:', error)
      showError('Ошибка при удалении пользователя: ' + (error.message || 'Неизвестная ошибка'))
    }
  }
}

const approveUser = async (user) => {
  const id = user.user_id || user.id
  try {
    await adminStore.approveUser(id)
    await refreshAfterAction()
  } catch (error) {
    console.error('Ошибка при одобрении пользователя:', error)
  }
}

const blockUser = async (user) => {
  const id = user.user_id || user.id
  try {
    await adminStore.blockUser(id)
    await refreshAfterAction()
  } catch (error) {
    console.error('Ошибка при блокировке пользователя:', error)
  }
}

const unblockUser = async (user) => {
  const id = user.user_id || user.id
  try {
    await adminStore.unblockUser(id)
    await refreshAfterAction()
  } catch (error) {
    console.error('Ошибка при разблокировке пользователя:', error)
  }
}

const restoreUser = async (restoreData) => {
  // restoreData = { userId, userName }
  const userId = restoreData.userId
  const userName = restoreData.userName || ''
  
  const confirmMessage = `Вы уверены, что хотите восстановить пользователя "${userName}"?`
  if (await showConfirm(confirmMessage, 'Восстановить', 'Отмена')) {
    try {
      await adminStore.restoreUser(userId)
      showSuccess('Пользователь успешно восстановлен')
      await refreshAfterAction()
    } catch (error) {
      console.error('Ошибка при восстановлении пользователя:', error)
      showError('Ошибка при восстановлении пользователя: ' + (error.message || 'Неизвестная ошибка'))
    }
  }
}

// Bulk user operations
const bulkApproveUsers = async (userIds) => {
  try {
    for (const userId of userIds) {
      await adminStore.approveUser(userId)
    }
    await refreshAfterAction()
  } catch (error) {
    console.error('Ошибка при массовом одобрении пользователей:', error)
    showError('Ошибка при одобрении пользователей: ' + (error.message || 'Неизвестная ошибка'))
  }
}

const bulkBlockUsers = async (userIds) => {
  try {
    for (const userId of userIds) {
      await adminStore.blockUser(userId)
    }
    await refreshAfterAction()
  } catch (error) {
    console.error('Ошибка при массовой блокировке пользователей:', error)
    showError('Ошибка при блокировке пользователей: ' + (error.message || 'Неизвестная ошибка'))
  }
}

const bulkDeleteUsers = async (userIds) => {
  try {
    for (const userId of userIds) {
      await adminStore.deleteUser(userId)
    }
    await refreshAfterAction()
  } catch (error) {
    console.error('Ошибка при массовом удалении пользователей:', error)
    showError('Ошибка при удалении пользователей: ' + (error.message || 'Неизвестная ошибка'))
  }
}

const deleteStation = async (deleteData) => {
  // deleteData может быть объектом { stationId, hardDelete, stationName } или просто stationId (для обратной совместимости)
  const stationId = typeof deleteData === 'object' ? deleteData.stationId : deleteData
  const hardDelete = typeof deleteData === 'object' ? deleteData.hardDelete : false
  const stationName = typeof deleteData === 'object' ? deleteData.stationName : ''
  
  const confirmMessage = hardDelete 
    ? `Вы уверены, что хотите НАВСЕГДА удалить станцию "${stationName}"?\n\nЭто действие необратимо!`
    : `Вы уверены, что хотите удалить станцию "${stationName || 'эту'}"?`
    
  if (await showConfirm(confirmMessage, hardDelete ? 'Удалить навсегда' : 'Удалить', 'Отмена')) {
    try {
      await adminStore.deleteStation(stationId, hardDelete)
      if (hardDelete) {
        showSuccess('Станция удалена навсегда')
      } else {
        showSuccess('Станция успешно удалена')
      }
      // Автоматическое обновление данных
      await refreshAfterAction()
    } catch (error) {
      console.error('Ошибка при удалении станции:', error)
      showError('Ошибка при удалении станции: ' + (error.message || 'Неизвестная ошибка'))
      // Ошибки синхронизации с сервером обрабатываются в сторе; UI остаётся консистентным
    }
  }
}

const restoreStation = async (restoreData) => {
  // restoreData = { stationId, stationName }
  const stationId = restoreData.stationId
  const stationName = restoreData.stationName || ''
  
  const confirmMessage = `Вы уверены, что хотите восстановить станцию "${stationName}"?`
  if (await showConfirm(confirmMessage, 'Восстановить', 'Отмена')) {
    try {
      await adminStore.restoreStation(stationId)
      showSuccess('Станция успешно восстановлена')
      await refreshAfterAction()
    } catch (error) {
      console.error('Ошибка при восстановлении станции:', error)
      showError('Ошибка при восстановлении станции: ' + (error.message || 'Неизвестная ошибка'))
    }
  }
}

const handleStationAction = async (station, event) => {
  const value = event?.target?.value || ''
  if (!value) return
  try {
    if (value.startsWith('status:')) {
      const newStatus = value.split(':')[1]
      
      // Если пытаемся изменить статус с "pending" на "active", показываем модальное окно активации
      if (station.status === 'pending' && newStatus === 'active') {
        stationToActivate.value = station
        showStationActivationModal.value = true
      } else {
        // Для других изменений статуса обновляем напрямую
        await adminStore.updateStation(station.station_id || station.id, { status: newStatus })
      }
    } else if (value === 'edit') {
      openEditStation(station)
    } else if (value === 'delete') {
      await deleteStation(station.station_id || station.id)
    }
  } catch (error) {
    // Ошибки синхронизации с сервером обрабатываются в сторе; UI остаётся консистентным
  } finally {
    if (event && event.target) {
      event.target.value = ''
    }
  }
}



// add-user flow removed

const handleBulkImportCompleted = async (importResult) => {
  try {
    showBulkImportModal.value = false
    // Автоматическое обновление данных пользователей
    await refreshAfterAction()
    // Можно добавить уведомление об успешном импорте
    console.log('Импорт завершен:', importResult)
  } catch (error) {
    console.error('Ошибка после импорта:', error)
  }
}

const handleUserUpdated = async (user) => {
  try {
    const id = user.user_id || user.id
    const updates = {
      fio: user.fio,
      phone_e164: user.phone_e164,
      email: user.email,
      role: user.role,
      parent_org_unit_id: user.parent_org_unit_id,
      status: user.status
    }
    
    // ВАЖНО: всегда передаем powerbank_limit, даже если null (для возможности сброса лимита)
    // Явно добавляем поле, чтобы гарантировать обновление лимита
    updates.powerbank_limit = user.powerbank_limit !== undefined ? user.powerbank_limit : null
    
    // Сервер ожидает поле "status" с английскими значениями (pending/active/blocked)
    // Статус уже в правильном формате, никаких преобразований не требуется
    
    console.log('Обновление пользователя:', { id, updates })
    await adminStore.updateUser(id, updates)
    await refreshAfterAction()
  } catch (error) {
    console.error('Ошибка при обновлении пользователя:', error)
    showError('Ошибка при обновлении пользователя: ' + (error.message || 'Неизвестная ошибка'))
  }
}

const handleStationAdded = async (stationData) => {
  try {
    await adminStore.createStation(stationData)
    showAddStationModal.value = false
    // Автоматическое обновление данных
    await refreshAfterAction()
  } catch (error) {
    // Error handled silently
  }
}

const handleStationEdited = async ({ id, data }) => {
  try {
    await adminStore.updateStation(id, data)
    showAddStationModal.value = false
    // Автоматическое обновление данных
    await refreshAfterAction()
  } catch (error) {
    // Error handled silently
  }
}

const handleStationActivated = async ({ stationId, secretKey, orgUnitId }) => {
  try {
    // Станция уже активирована в модальном окне, просто закрываем его
    showStationActivationModal.value = false
    stationToActivate.value = null

    // Закрываем модальное окно редактирования станции
    showAddStationModal.value = false
    
    // Автоматическое обновление данных
    await refreshAfterAction()
  } catch (error) {
    // Error handled silently
  }
}

const handleStationActivationRequired = (station) => {
  // Закрываем модальное окно редактирования
  showAddStationModal.value = false
  
  // Показываем модальное окно активации
  stationToActivate.value = station
  showStationActivationModal.value = true
}

const closeStationModal = () => {
  showAddStationModal.value = false
}



const showUserHistoryModal = ref(false)
const selectedUserHistory = ref([])

const viewHistory = async (user) => {
  selectedUser.value = user
  const id = user.user_id || user.id
  selectedUserHistory.value = await adminStore.fetchUserHistory(id)
  showUserHistoryModal.value = true
}

const closeUserHistoryModal = () => {
  showUserHistoryModal.value = false
  selectedUserHistory.value = []
  selectedUser.value = null
}

const openPowerbanks = async (station) => {
  try {
    selectedStation.value = station
    const stationId = station.station_id || station.id
    if (!stationId) return
    // 1) Тригерим запрос инвентаря на сервер (обновление показаний)
    try { await pythonAPI.queryInventory(stationId) } catch {}
    // 2) Получаем инвентарь из кэша соединения (в нём есть terminal_id и soh)
    let inv = null
    try {
      inv = await pythonAPI.getStationInventory(stationId)
    } catch {}
    if (inv && Array.isArray(inv.inventory)) {
      selectedStationPowerbanks.value = inv.inventory
    } else {
      // Фолбэк: детальный список из station_powerbank
      const res = await pythonAPI.getStationPowerbanksDetailed({ station_id: stationId })
      selectedStationPowerbanks.value = Array.isArray(res?.data) ? res.data : []
    }
    showPowerbanksModal.value = true
  } catch (error) {
    selectedStationPowerbanks.value = []
    showPowerbanksModal.value = true
  }
}

const closePowerbanks = () => {
  showPowerbanksModal.value = false
  selectedStation.value = null
  selectedStationPowerbanks.value = []
}


const restartStation = async (station) => {
  const stationId = station.station_id || station.id
  if (!stationId) {
    showError('Не удалось определить ID станции')
    return
  }

  const confirmMessage = `Вы уверены, что хотите перезагрузить станцию "${station.box_id || 'N/A'}"?`
  if (!await showConfirm(confirmMessage, 'Перезагрузить', 'Отмена')) return

  try {
    const result = await pythonAPI.restartCabinet({ station_id: stationId })
    
    if (result && result.message) {
      showSuccess(`Команда перезагрузки отправлена: ${result.message}`)
      if (result.station_box_id) {
        console.log('Station Box ID:', result.station_box_id)
      }
      if (result.packet_hex) {
        console.log('Packet HEX:', result.packet_hex)
      }
    } else {
      showSuccess('Команда перезагрузки отправлена')
    }
  } catch (error) {
    console.error('Ошибка при перезагрузке станции:', error)
    showError('Ошибка при перезагрузке станции: ' + (error.message || 'Неизвестная ошибка'))
  }
}

const generateQRCode = (station) => {
  selectedStationForQR.value = station
  showStationQRModal.value = true
}

const borrowPowerbank = async (powerbank) => {
  if (!selectedStation.value || isBorrowing.value) return

  isBorrowing.value = true
  try {
    const userId = authStore.user?.id || authStore.user?.user_id

    if (!userId) {
      showError('Не удалось определить пользователя')
      return
    }

    const requestData = {
      station_id: selectedStation.value.station_id,
      user_id: userId,
      slot_number: powerbank.slot_number
    }

    const result = await pythonAPI.requestBorrowPowerbank(requestData)

    if (result && (result.status === 'success' || result.status === 'accepted' || result.success)) {
      // Обновляем данные станции в панели администратора
      const stationId = selectedStation.value.station_id
      await adminStore.refreshStationData(stationId)
      
      // Обновляем список повербанков в модальном окне
      try { await pythonAPI.queryInventory(stationId) } catch {}
      const inv = await pythonAPI.getStationInventory(stationId)
      selectedStationPowerbanks.value = Array.isArray(inv?.inventory) ? inv.inventory : []
    } else {
      // Ошибка при взятии повербанка
    }
  } catch (error) {
    // Ошибка при взятии повербанка
  } finally {
    isBorrowing.value = false
  }
}

const forceEjectPowerbank = async (powerbank) => {
  if (!selectedStation.value || isBorrowing.value) return

  const confirmMessage = `Вы уверены, что хотите принудительно извлечь повербанк из слота ${powerbank.slot_number}?`
  if (!await showConfirm(confirmMessage, 'Извлечь', 'Отмена')) return

  isBorrowing.value = true
  try {
    const userId = authStore.user?.id || authStore.user?.user_id

    if (!userId) {
      showError('Не удалось определить пользователя')
      return
    }

    const requestData = {
      station_id: selectedStation.value.station_id,
      slot_number: powerbank.slot_number,
      admin_user_id: userId
    }

    await adminStore.forceEjectPowerbank(requestData)

    // Данные станции уже обновлены в store через forceEjectPowerbank
    // Обновляем список повербанков в модальном окне (через инвентарь)
    const stationId = selectedStation.value.station_id
    try { await pythonAPI.queryInventory(stationId) } catch {}
    const inv = await pythonAPI.getStationInventory(stationId)
    selectedStationPowerbanks.value = Array.isArray(inv?.inventory) ? inv.inventory : []

  } catch (error) {
    // Ошибка при принудительном извлечении повербанка
  } finally {
    isBorrowing.value = false
  }
}


const goToHome = () => {
  router.push('/dashboard')
}

// Простая функция обновления данных после действий
const refreshAfterAction = async () => {
  try {
    // Обновляем данные в зависимости от активной вкладки
    switch (activeTab.value) {
      case 'users':
        await adminStore.fetchUsers()
        break
      case 'stations':
        await adminStore.fetchStations()
        break
      case 'powerbanks':
        await adminStore.fetchPowerbanks()
        break
      case 'org-units':
        await adminStore.fetchOrgUnits()
        break
      case 'orders':
        await adminStore.fetchOrders()
        break
      case 'stats':
        // Для статистики обновляем все данные
        await Promise.all([
          adminStore.fetchUsers(),
          adminStore.fetchStations(),
          adminStore.fetchOrders(),
          adminStore.fetchOrgUnits()
        ])
        break
    }
  } catch (error) {
    console.warn('Ошибка при обновлении данных после действия:', error)
  }
}
const editOrgUnit = (orgUnit) => {
  selectedOrgUnit.value = orgUnit
  autoEditOrgUnit.value = true
  showOrgUnitDetailsModal.value = true
}

const deleteOrgUnit = async (deleteData) => {
  // deleteData может быть объектом { orgUnitId, hardDelete, orgUnitName } или просто orgUnitId (для обратной совместимости)
  const orgUnitId = typeof deleteData === 'object' ? deleteData.orgUnitId : deleteData
  const hardDelete = typeof deleteData === 'object' ? deleteData.hardDelete : false
  const orgUnitName = typeof deleteData === 'object' ? deleteData.orgUnitName : ''
  
  const confirmMessage = hardDelete 
    ? `Вы уверены, что хотите НАВСЕГДА удалить группу "${orgUnitName}"?\n\nЭто действие необратимо!`
    : `Вы уверены, что хотите удалить группу "${orgUnitName || 'эту'}"?`
    
  if (await showConfirm(confirmMessage, hardDelete ? 'Удалить навсегда' : 'Удалить', 'Отмена')) {
    try {
      if (hardDelete) {
        await pythonAPI.hardDelete('org_unit', orgUnitId)
        showSuccess('Группа удалена навсегда')
      } else {
        await pythonAPI.softDelete('org_unit', orgUnitId)
        showSuccess('Группа успешно удалена')
      }
      await adminStore.fetchOrgUnits()
    } catch (error) {
      console.error('Ошибка при удалении группы:', error)
      showError('Ошибка при удалении группы: ' + (error.message || 'Неизвестная ошибка'))
    }
  }
}

const restoreOrgUnit = async (restoreData) => {
  // restoreData = { orgUnitId, orgUnitName }
  const orgUnitId = restoreData.orgUnitId
  const orgUnitName = restoreData.orgUnitName || ''
  
  const confirmMessage = `Вы уверены, что хотите восстановить группу "${orgUnitName}"?`
  if (await showConfirm(confirmMessage, 'Восстановить', 'Отмена')) {
    try {
      await pythonAPI.restoreDeleted('org_unit', orgUnitId)
      showSuccess('Группа успешно восстановлена')
      await adminStore.fetchOrgUnits()
    } catch (error) {
      console.error('Ошибка при восстановлении группы:', error)
      showError('Ошибка при восстановлении группы: ' + (error.message || 'Неизвестная ошибка'))
    }
  }
}

const viewOrgUnitStations = (orgUnit) => {
  selectedOrgUnit.value = orgUnit
  showOrgUnitStationsModal.value = true
}

const viewOrgUnitDetails = (orgUnit) => {
  selectedOrgUnit.value = orgUnit
  autoEditOrgUnit.value = false
  showOrgUnitDetailsModal.value = true
}

const closeOrgUnitModal = () => {
  showAddOrgUnitModal.value = false
  editingOrgUnit.value = null
}

const closeOrgUnitStationsModal = () => {
  showOrgUnitStationsModal.value = false
  selectedOrgUnit.value = null
}

const closeOrgUnitDetailsModal = () => {
  showOrgUnitDetailsModal.value = false
  selectedOrgUnit.value = null
  autoEditOrgUnit.value = false
}

const handleOrgUnitUpdated = async () => {
  // Обновляем список групп после редактирования
  await adminStore.fetchOrgUnits()
}

const handleOrgUnitAdded = async (data) => {
  try {
    // Группа уже добавлена в store через createOrgUnit
    closeOrgUnitModal()
    // Автоматическое обновление данных
    await refreshAfterAction()
  } catch (error) {
    // Error handled silently
  }
}

const handleOrgUnitEdited = async (data) => {
  try {
    // Группа уже обновлена в store через updateOrgUnit
    closeOrgUnitModal()
    // Автоматическое обновление данных
    await refreshAfterAction()
  } catch (error) {
    // Error handled silently
  }
}


// Жизненный цикл
onMounted(async () => {
  // Загружаем данные при монтировании компонента
  try {
    console.log('🚀 AdminPanel: Starting data loading...')
    console.log('🚀 AdminPanel: Current user:', authStore.user)
    console.log('🚀 AdminPanel: Current orgUnits:', adminStore.orgUnits)
    
    const results = await Promise.all([
      adminStore.fetchUsers(),
      adminStore.fetchStations(),
      adminStore.fetchOrders(),
      adminStore.fetchOrgUnits()
    ])
    
    console.log('🚀 AdminPanel: Data loaded successfully:', results)
    console.log('🚀 AdminPanel: Final user:', authStore.user)
    console.log('🚀 AdminPanel: Final orgUnits:', adminStore.orgUnits)
  } catch (error) {
    console.error('🚀 AdminPanel: Error loading data:', error)
  }
})

</script>

<style scoped>
.admin-panel {
  min-height: 100vh;
  background: #f5f5f5;
}


.admin-main {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px 20px 20px 5px;
}

.admin-layout {
  display: flex;
  gap: 12px;
}


.admin-content {
  flex: 1;
}

.header-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.tab-content {
  background: white;
  border-radius: 15px;
  padding: 30px;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
}

.section-header h2 {
  color: #333;
  font-size: 1.8rem;
  margin: 0;
}

.btn-primary {
  padding: 10px 24px;
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

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #666;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-state h3 {
  margin: 0 0 8px 0;
  color: #333;
  font-size: 18px;
}

.empty-state p {
  margin: 0;
  font-size: 14px;
}

/* Org Units */
.org-units-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.org-unit-item {
  width: 100%;
}

/* Addresses */
.addresses-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.address-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 10px;
  border-left: 4px solid #17a2b8;
}

.address-info {
  display: flex;
  align-items: center;
  gap: 20px;
}

.address-main h3 {
  color: #333;
  margin: 0 0 5px 0;
  font-size: 1.1rem;
}

.address-city,
.address-postal {
  color: #666;
  margin: 0 0 5px 0;
  font-size: 0.9rem;
}

.address-stats {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.stat-item {
  color: #666;
  font-size: 0.9rem;
}

.address-actions {
  display: flex;
  gap: 10px;
}

/* Status badges */
.status-badge {
  padding: 5px 12px;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
}

.status-active {
  background: transparent;
  color: #333;
}

.status-pending {
  background: transparent;
  color: #333;
}

.status-blocked {
  background: transparent;
  color: #333;
}

.status-inactive {
  background: transparent;
  color: #333;
}

.status-maintenance {
  background: transparent;
  color: #333;
}

.status-error {
  background: transparent;
  color: #333;
}

.status-unknown {
  background: transparent;
  color: #333;
}

/* Stats */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
}

.stat-card {
  background: #f8f9fa;
  border-radius: 10px;
  padding: 20px;
  border-left: 4px solid #667eea;
}

.stat-card h3 {
  color: #333;
  margin: 0 0 20px 0;
  font-size: 1.2rem;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.stat-label {
  color: #666;
  font-size: 0.9rem;
}

.stat-value {
  color: #333;
  font-weight: 700;
  font-size: 1.1rem;
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
  .admin-main {
    padding: 15px 15px 15px 4px;
  }
  
  .admin-layout {
    flex-direction: column;
    gap: 10px;
  }


  .admin-content {
    padding: 0;
  }

  .tab-content {
    padding: 20px;
  }
  
  .section-header {
    flex-direction: column;
    gap: 15px;
    align-items: flex-start;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
}

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
  padding: 20px;
  border-radius: 8px;
  max-width: 600px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
}

.history-list {
  margin: 20px 0;
}

.history-item {
  padding: 10px;
  border-bottom: 1px solid #eee;
  color: #333;
}

.btn-close {
  padding: 10px 20px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
</style>

