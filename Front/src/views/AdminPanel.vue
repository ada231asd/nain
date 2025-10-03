<template>
  <div class="admin-panel">
    <NotificationToast
      v-if="showServerResting"
      :message="serverRestingMessage"
      type="warning"
      position="top-center"
      :duration="5000"
    />
    <!-- Header -->
    <header class="admin-header">
      <div class="header-content">
        <button @click="goBack" class="btn-back">← Назад</button>
        <h1>Админ панель</h1>
        <div class="user-info">
          <div class="auto-refresh-control">
            <button 
              @click="toggleAutoRefresh" 
              :class="['auto-refresh-btn', { active: autoRefreshEnabled }]"
              :title="autoRefreshEnabled ? 'Отключить автообновление' : 'Включить автообновление'"
            >
              {{ autoRefreshEnabled ? '🔄' : '⏸️' }}
            </button>
          </div>
          <span class="user-role">{{ userRoleText }}</span>
          <span class="user-name">{{ getUserDisplayName(user) }}</span>
        </div>
      </div>
    </header>

    <!-- Основной контент -->
    <main class="admin-main">
      <div class="admin-layout">
        <aside class="admin-sidebar">
          <button 
            v-for="tab in availableTabs"
            :key="tab.id"
            :class="['sidebar-item', { active: activeTab === tab.id }]"
            @click="activeTab = tab.id"
          >
            {{ tab.name }}
          </button>
        </aside>

        <div class="admin-content">
          <div class="tab-content">

            <!-- Управление пользователями -->
            <div v-if="activeTab === 'users'" class="tab-pane">
              <div class="section-header">
                <h2>Управление пользователями</h2>
                <div class="header-actions">
                  <input type="text" v-model="userSearch" placeholder="Поиск..." class="search-input" />
                  <button @click="showAddUserModal = true" class="btn-primary">
                    + Добавить пользователя
                  </button>
                </div>
              </div>

              <table class="users-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>ФИО</th>
                    <th>Телефон</th>
                    <th>Email</th>
                    <th>Роль</th>
                    <th>Группа</th>
                    <th>Статус</th>
                    <th>Создан</th>
                    <th>Последний вход</th>
                    <th>Действия</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="user in filteredUsers" :key="user.user_id || user.id">
                    <td class="user-cell" :class="`user-status-${getUserStatusClass(user.статус || user.status)}`">
                      <span class="user-name-text">{{ user.user_id || user.id || 'N/A' }}</span>
                    </td>
                    <td>{{ user.fio || 'N/A' }}</td>
                    <td>{{ user.phone_e164 || 'N/A' }}</td>
                    <td>{{ user.email || 'N/A' }}</td>
                    <td>
                      <span class="role-badge" :class="getUserRoleClass(user.role)">
                        {{ getUserRoleText(user.role) }}
                      </span>
                    </td>
                    <td>
                      <span class="group-badge">
                        {{ getUserGroupName(user.parent_org_unit_id || user.org_unit_id) }}
                      </span>
                    </td>
                    <td>
                      <span class="status-badge" :class="getUserStatusClass(user.статус || user.status)">
                        {{ getUserStatusText(user.статус || user.status) }}
                      </span>
                    </td>
                    <td>{{ user.created_at ? formatTime(user.created_at) : 'N/A' }}</td>
                    <td>{{ user.last_login_at ? formatTime(user.last_login_at) : 'N/A' }}</td>
                    <td>
                      <select class="filter-select" @change="handleUserAction(user, $event)">
                        <option value="">Выбрать действие</option>
                        <option value="edit">Редактировать</option>
                        <option v-if="(user.статус || user.status) === 'ожидает' || (user.статус || user.status) === 'pending'" value="approve">Одобрить</option>
                        <option v-if="(user.статус || user.status) === 'активный' || (user.статус || user.status) === 'active'" value="block">Заблокировать</option>
                        <option v-if="(user.статус || user.status) === 'заблокирован' || (user.статус || user.status) === 'blocked'" value="unblock">Разблокировать</option>
                        <option value="delete">Удалить</option>
                      </select>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Управление станциями -->
            <div v-if="activeTab === 'stations'" class="tab-pane">
              <div class="section-header">
                <h2>Управление станциями</h2>
                <div class="header-actions">
                  <input type="text" v-model="stationSearch" placeholder="Поиск станций..." class="search-input" />
                  <button @click="() => { editingStation = null; showAddStationModal = true }" class="btn-primary">
                    + Добавить станцию
                  </button>
                </div>
              </div>

              <div class="stations-grid">
                <div v-for="station in filteredStations" :key="station.station_id || station.id" :class="['station-card', getStationCardClass(station.status)]">
                  <div class="station-card-header">
                    <div class="station-status">
                      <span class="status-indicator" :class="`status-${station.status}`"></span>
                      <span class="status-text">{{ getStationStatusText(station.status) }}</span>
                    </div>
                    <div class="station-actions">
                      <button @click="openPowerbanks(station)" class="btn-action btn-powerbanks" title="Просмотр павербанков">
                        🔋
                      </button>
                      <button @click="openVoiceVolume(station)" class="btn-action btn-volume" title="Управление громкостью">
                        🔊
                      </button>
                      <button @click="openServerAddress(station)" class="btn-action btn-server" title="Управление адресом сервера">
                        🌐
                      </button>
                      <button @click="restartStation(station)" class="btn-action btn-restart" title="Перезагрузить станцию">
                        🔄
                      </button>
                      <button @click="editStation(station)" class="btn-action btn-edit" title="Редактировать">
                        ✏️
                      </button>
                      <button @click="deleteStation(station.station_id || station.id)" class="btn-action btn-delete" title="Удалить">
                        🗑️
                      </button>
                    </div>
                  </div>
                  
                  <div class="station-card-content">
                    <div class="station-main-info">
                      <h3 class="station-title">{{ station.box_id || 'N/A' }}</h3>
                      <p class="station-org" v-if="station.org_unit_name">{{ station.org_unit_name }}</p>
                    </div>
                    
                    <div class="station-details">
                      <div class="detail-row">
                        <span class="detail-label">ICCID:</span>
                        <span class="detail-value">{{ station.iccid || '—' }}</span>
                      </div>
                      <div class="detail-row">
                        <span class="detail-label">Слотов:</span>
                        <span class="detail-value">{{ station.slots_declared || station.totalPorts || 0 }}</span>
                      </div>
                      <div class="detail-row">
                        <span class="detail-label">Свободно:</span>
                        <span class="detail-value">{{ station.freePorts || station.remain_num || 0 }}</span>
                      </div>
                      <div class="detail-row">
                        <span class="detail-label">Занято:</span>
                        <span class="detail-value">{{ station.occupiedPorts || ((station.slots_declared || 0) - (station.remain_num || 0)) }}</span>
                      </div>
                      <div class="detail-row">
                        <span class="detail-label">Последний сигнал:</span>
                        <span class="detail-value">{{ station.last_seen ? formatTime(station.last_seen) : '—' }}</span>
                      </div>
                      <div class="detail-row">
                        <span class="detail-label">Создана:</span>
                        <span class="detail-value">{{ station.created_at ? formatTime(station.created_at) : '—' }}</span>
                      </div>
                      <div class="detail-row">
                        <span class="detail-label">Обновлена:</span>
                        <span class="detail-value">{{ station.updated_at ? formatTime(station.updated_at) : '—' }}</span>
                      </div>
                    </div>
                  </div>
                  
                </div>
              </div>
              
              <div v-if="filteredStations.length === 0" class="empty-state">
                <div class="empty-icon">🏢</div>
                <h3>Станции не найдены</h3>
                <p>Попробуйте изменить поисковый запрос или добавьте новую станцию</p>
              </div>
            </div>

            <!-- Управление павербанками -->
            <div v-if="activeTab === 'powerbanks'" class="tab-pane">
              <PowerbankList />
            </div>

            <!-- Управление группами -->
            <div v-if="activeTab === 'org-units'" class="tab-pane">
              <div class="section-header">
                <h2>Управление группами</h2>
                <div class="header-actions">
                  <input type="text" v-model="orgUnitSearch" placeholder="Поиск групп..." class="search-input" />
                  <button @click="() => { editingOrgUnit = null; showAddOrgUnitModal = true }" class="btn-primary">
                    + Добавить группу
                  </button>
                </div>
              </div>

              <div class="org-units-list">
                <div v-for="orgUnit in filteredOrgUnits" :key="orgUnit.org_unit_id" class="org-unit-item">
                  <OrgUnitCard 
                    :org-unit="orgUnit"
                    @edit="editOrgUnit"
                    @delete="deleteOrgUnit"
                    @view-stations="viewOrgUnitStations"
                  />
                </div>
              </div>
            </div>


            <!-- Все заказы -->
            <div v-if="activeTab === 'orders'" class="tab-pane">
              <div class="section-header">
                <h2>Все заказы</h2>
                <div class="header-actions">
                  <div class="order-filters">
                    <select v-model="orderFilter.status" class="filter-select">
                      <option value="">Все статусы</option>
                      <option value="pending">В ожидании</option>
                      <option value="completed">Завершены</option>
                      <option value="cancelled">Отменены</option>
                    </select>
                  </div>
                  <button @click="refreshOrders" class="btn-primary" :disabled="isLoading">
                    {{ isLoading ? '🔄' : '↻' }} Обновить
                  </button>
                </div>
              </div>

              <div v-if="isLoading" class="loading-state">
                <div class="loading-spinner"></div>
                <p>Загрузка заказов...</p>
              </div>

              <div v-else-if="filteredOrders.length === 0" class="empty-state">
                <div class="empty-icon">📋</div>
                <h3>Заказы не найдены</h3>
                <p v-if="orders.length === 0">Заказов пока нет в системе</p>
                <p v-else>Попробуйте изменить фильтр или обновить данные</p>
              </div>

              <div v-else>
                <!-- Переключатель вида -->
                <div class="view-toggle">
                  <button 
                    @click="ordersViewMode = 'cards'" 
                    :class="['view-btn', { active: ordersViewMode === 'cards' }]"
                  >
                    📋 Карточки
                  </button>
                  <button 
                    @click="ordersViewMode = 'table'" 
                    :class="['view-btn', { active: ordersViewMode === 'table' }]"
                  >
                    📊 Таблица
                  </button>
                </div>

                <!-- Карточный вид -->
                <div v-if="ordersViewMode === 'cards'" class="orders-list">
                  <div v-for="order in filteredOrders" :key="order.id || order.order_id" class="order-card">
                    <div class="order-info">
                      <div class="order-main">
                        <h3>Заказ #{{ order.id || order.order_id }}</h3>
                        <p class="order-user">Пользователь: {{ order.user_fio || order.user_phone || 'N/A' }}</p>
                        <p class="order-station">Станция: {{ order.station_box_id || order.station_name || order.station_id || 'N/A' }}</p>
                        <p class="order-action">Действие: {{ getOrderActionText(order.status) }}</p>
                      </div>
                      <div class="order-status">
                        <span class="status-badge" :class="getOrderStatusClass(order.status)">
                          {{ getOrderStatusText(order.status) }}
                        </span>
                      </div>
                    </div>
                    <div class="order-details">
                      <p class="order-time">Создан: {{ formatTime(order.timestamp) }}</p>
                      <p class="order-completed" v-if="order.completed_at">
                        Завершен: {{ formatTime(order.completed_at) }}
                      </p>
                      <p class="order-powerbank" v-if="order.powerbank_serial || order.powerbank_id">
                        Повербанк: {{ order.powerbank_serial || order.powerbank_id }}
                      </p>
                    </div>
                  </div>
                </div>

                <!-- Табличный вид -->
                <div v-else class="orders-table-container">
                  <table class="orders-table">
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>Пользователь</th>
                        <th>Станция</th>
                        <th>Действие</th>
                        <th>Статус</th>
                        <th>Создан</th>
                        <th>Завершен</th>
                        <th>Повербанк</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="order in filteredOrders" :key="order.id || order.order_id">
                        <td class="order-id">#{{ order.id || order.order_id }}</td>
                        <td>{{ order.user_fio || order.user_phone || 'N/A' }}</td>
                        <td>{{ order.station_box_id || order.station_name || order.station_id || 'N/A' }}</td>
                        <td>{{ getOrderActionText(order.status) }}</td>
                        <td>
                          <span class="status-badge" :class="getOrderStatusClass(order.status)">
                            {{ getOrderStatusText(order.status) }}
                          </span>
                        </td>
                        <td>{{ formatTime(order.timestamp) }}</td>
                        <td>{{ order.completed_at ? formatTime(order.completed_at) : '—' }}</td>
                        <td>{{ order.powerbank_serial || order.powerbank_id || '—' }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
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
    <AddUserModal 
      :is-visible="showAddUserModal"
      @close="showAddUserModal = false"
      @user-added="handleUserAdded"
    />
    <EditUserModal
      :is-visible="showEditUserModal"
      :user="selectedUser"
      @close="closeEditUser"
      @save="saveEditedUser"
      @approve="approveSelectedUser"
      @reject="rejectSelectedUser"
    />
    
    <AddStationModal 
      :is-visible="showAddStationModal"
      :station="editingStation"
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

    <VoiceVolumeModal
      :is-visible="showVoiceVolumeModal"
      :station="selectedStationForVolume"
      @close="closeVoiceVolume"
      @volume-updated="handleVolumeUpdated"
    />

    <ServerAddressModal
      :is-visible="showServerAddressModal"
      :station="selectedStationForServerAddress"
      @close="closeServerAddress"
      @address-updated="handleServerAddressUpdated"
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
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAdminStore } from '../stores/admin'
import { useAuthStore } from '../stores/auth'
import { pythonAPI } from '../api/pythonApi'



import EditUserModal from '../components/EditUserModal.vue'
import AddUserModal from '../components/AddUserModal.vue'
import AddStationModal from '../components/AddStationModal.vue'
import StationPowerbanksModal from '../components/StationPowerbanksModal.vue'
import StationActivationModal from '../components/StationActivationModal.vue'
import VoiceVolumeModal from '../components/VoiceVolumeModal.vue'
import ServerAddressModal from '../components/ServerAddressModal.vue'
 
import AddOrgUnitModal from '../components/AddOrgUnitModal.vue'
import OrgUnitCard from '../components/OrgUnitCard.vue'
import OrgUnitStationsModal from '../components/OrgUnitStationsModal.vue'
import PowerbankList from '../components/PowerbankList.vue'

const router = useRouter()
const adminStore = useAdminStore()
const authStore = useAuthStore()

// Состояние
const activeTab = ref('users')
const orderFilter = ref({
  status: ''
})
const ordersViewMode = ref('cards') // 'cards' или 'table'

// Модальные окна
const showAddUserModal = ref(false)
const showAddStationModal = ref(false)
const editingStation = ref(null)
const showEditUserModal = ref(false)
const showStationActivationModal = ref(false)
const stationToActivate = ref(null)
const selectedUser = ref(null)
const showPowerbanksModal = ref(false)
const selectedStation = ref(null)
const selectedStationPowerbanks = ref([])
const isBorrowing = ref(false)

// Модальное окно управления громкостью
const showVoiceVolumeModal = ref(false)
const selectedStationForVolume = ref(null)

// Модальное окно управления адресом сервера
const showServerAddressModal = ref(false)
const selectedStationForServerAddress = ref(null)

// Модальные окна для групп
const showAddOrgUnitModal = ref(false)
const editingOrgUnit = ref(null)
const showOrgUnitStationsModal = ref(false)
const selectedOrgUnit = ref(null)

// Глобальное уведомление, если сервер не отвечает
const showServerResting = ref(false)
const serverRestingMessage = ref('')

// Автоматическое обновление данных
const autoRefreshInterval = ref(null)
const autoRefreshEnabled = ref(false) // Отключаем автоматическое обновление по таймеру
const refreshInterval = 30000 // 30 секунд

if (typeof window !== 'undefined') {
  window.addEventListener('api:server-down', (e) => {
    serverRestingMessage.value = (e && e.detail && e.detail.message) || 'Подождите, сервер отдыхает'
    showServerResting.value = true
    // Скрыть через 5 секунд
    setTimeout(() => { showServerResting.value = false }, 5000)
  })
}

// Вычисляемые свойства
const user = computed(() => authStore.user || { phone: 'Администратор' })
const userRole = computed(() => authStore.user?.role || 'service_admin')

const userRoleText = computed(() => {
  switch (userRole.value) {
    case 'service_admin': return 'Администратор сервиса'
    case 'group_admin': return 'Администратор группы'
    case 'subgroup_admin': return 'Администратор подгруппы'
    default: return 'Пользователь'
  }
})

const availableTabs = computed(() => {
  const tabs = [
    { id: 'users', name: 'Пользователи' },
    { id: 'stations', name: 'Станции' },
    { id: 'powerbanks', name: 'Павербанки' },
    { id: 'org-units', name: 'Группы' },
    { id: 'orders', name: 'Все заказы' },
    { id: 'stats', name: 'Статистика' }
  ]

  // Ограничиваем доступ в зависимости от роли
  if (userRole.value === 'subgroup_admin') {
    return tabs.filter(tab => ['users', 'stations', 'org-units', 'stats'].includes(tab.id))
  } else if (userRole.value === 'group_admin') {
    return tabs.filter(tab => tab.id !== 'stats')
  }

  return tabs
})

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

const filteredOrders = computed(() => {
  if (!orderFilter.value.status) return orders.value
  return orders.value.filter(order => order.status === orderFilter.value.status)
})

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

const userSearch = ref('')
const orgUnitSearch = ref('')
const stationSearch = ref('')

const filteredUsers = computed(() => {
  const list = users.value || []
  const query = (userSearch.value || '').toString().trim().toLowerCase()
  if (!query) return list

  return list.filter(user => {
    const phone = (user.phone_e164 || '').toString().toLowerCase()
    const email = (user.email || '').toString().toLowerCase()
    const fio = (user.fio || '').toString().toLowerCase()
    const userId = (user.user_id || user.id || '').toString().toLowerCase()
    const role = getUserRoleText(user.role).toLowerCase()
    return (
      phone.includes(query) ||
      email.includes(query) ||
      fio.includes(query) ||
      userId.includes(query) ||
      role.includes(query)
    )
  })
})

const filteredOrgUnits = computed(() => {
  const list = orgUnits.value || []
  const query = (orgUnitSearch.value || '').toString().trim().toLowerCase()
  if (!query) return list

  return list.filter(orgUnit => {
    const name = (orgUnit.name || '').toString().toLowerCase()
    const description = (orgUnit.description || '').toString().toLowerCase()
    const unitType = (orgUnit.unit_type || '').toString().toLowerCase()
    const parentName = (orgUnit.parent_name || '').toString().toLowerCase()
    return (
      name.includes(query) ||
      description.includes(query) ||
      unitType.includes(query) ||
      parentName.includes(query)
    )
  })
})

const filteredStations = computed(() => {
  const list = stations.value || []
  const query = (stationSearch.value || '').toString().trim().toLowerCase()
  if (!query) return list

  return list.filter(station => {
    const boxId = (station.box_id || '').toString().toLowerCase()
    const iccid = (station.iccid || '').toString().toLowerCase()
    const orgUnitName = (station.org_unit_name || '').toString().toLowerCase()
    const status = (station.status || '').toString().toLowerCase()
    return (
      boxId.includes(query) ||
      iccid.includes(query) ||
      orgUnitName.includes(query) ||
      status.includes(query)
    )
  })
})

const getUserRoleText = (role) => {
  switch(role) {
    case 'service_admin': return 'Сервис-администратор'
    case 'group_admin': return 'Администратор группы'
    case 'subgroup_admin': return 'Администратор подгруппы'
    case 'user': return 'Пользователь'
    default: return 'Пользователь'
  }
}

const getUserRoleClass = (role) => {
  switch(role) {
    case 'service_admin': return 'role-service-admin'
    case 'group_admin': return 'role-group-admin'
    case 'subgroup_admin': return 'role-subgroup-admin'
    case 'user': return 'role-user'
    default: return 'role-user'
  }
}

const formatDate = (date) => {
  return new Date(date).toLocaleDateString('ru-RU')
}

// Методы
const goBack = () => {
  router.back()
}

const getUserStatusClass = (status) => {
  switch (status) {
    case 'active':
    case 'активный': return 'status-active'
    case 'pending':
    case 'ожидает': return 'status-pending'
    case 'blocked':
    case 'заблокирован': return 'status-blocked'
    case 'rejected':
    case 'отклонен': return 'status-error'
    default: return 'status-unknown'
  }
}

const getUserStatusText = (status) => {
  switch (status) {
    case 'active':
    case 'активный': return 'Активен'
    case 'pending':
    case 'ожидает': return 'Ожидает'
    case 'blocked':
    case 'заблокирован': return 'Заблокирован'
    case 'rejected':
    case 'отклонен': return 'Отклонен'
    default: return 'Неизвестно'
  }
}

const getUserGroupName = (orgUnitId) => {
  if (!orgUnitId) return 'Без группы'
  const group = adminStore.orgUnits.find(ou => ou.org_unit_id === orgUnitId)
  return group ? group.name : 'Неизвестная группа'
}

const getUserDisplayName = (user) => {
  if (!user) return 'Администратор'
  
  // Определяем имя пользователя из доступных полей
  if (user.fio && user.fio.trim()) {
    return user.fio.trim()
  } else if (user.first_name && user.last_name) {
    return `${user.first_name} ${user.last_name}`.trim()
  } else if (user.name && user.name.trim()) {
    return user.name.trim()
  } else if (user.phone_e164) {
    return user.phone_e164
  } else {
    return 'Администратор'
  }
}

const getStationStatusClass = (status) => {
  switch (status) {
    case 'active': return 'status-active'
    case 'pending': return 'status-pending'
    case 'inactive': return 'status-inactive'
    case 'maintenance': return 'status-maintenance'
    default: return 'status-unknown'
  }
}

const getStationStatusText = (status) => {
  switch (status) {
    case 'active': return 'Активна'
    case 'pending': return 'Ожидает'
    case 'inactive': return 'Неактивна'
    case 'maintenance': return 'Сервис'
    default: return 'Неизвестно'
  }
}

const getStationCardClass = (status) => {
  switch (status) {
    case 'active': return 'status-active'
    case 'pending': return 'status-pending'
    case 'inactive': return 'status-inactive'
    case 'maintenance': return 'status-maintenance'
    default: return 'status-unknown'
  }
}

const getOrderStatusClass = (status) => {
  switch (status) {
    case 'pending': return 'status-pending'
    case 'borrow': return 'status-active'
    case 'return': return 'status-success'
    case 'completed': return 'status-success'
    case 'cancelled': return 'status-error'
    default: return 'status-unknown'
  }
}

const getOrderStatusText = (status) => {
  switch (status) {
    case 'pending': return 'В ожидании'
    case 'borrow': return 'Взято'
    case 'return': return 'Возвращено'
    case 'completed': return 'Завершен'
    case 'cancelled': return 'Отменен'
    default: return status || 'Неизвестно'
  }
}

const getOrderActionText = (action) => {
  switch (action) {
    case 'take': return 'Получение аккумулятора'
    case 'return': return 'Возврат аккумулятора'
    case 'borrow': return 'Взятие повербанка'
    case 'eject': return 'Извлечение повербанка'
    default: return action || 'Неизвестное действие'
  }
}

const refreshOrders = async () => {
  try {
    await adminStore.fetchOrders()
  } catch (error) {
    console.error('Ошибка при обновлении заказов:', error)
  }
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

const openEditUser = (user) => {
  selectedUser.value = user
  showEditUserModal.value = true
}
const closeEditUser = () => {
  showEditUserModal.value = false
  selectedUser.value = null
}
const saveEditedUser = async (updates) => {
  if (!selectedUser.value) return
  const id = selectedUser.value.user_id || selectedUser.value.id
  try {
    console.log('Отправляем данные пользователя:', { id, updates })
    await adminStore.updateUser(id, updates)
    closeEditUser()
    // Автоматическое обновление данных
    await refreshAfterAction()
  } catch (error) {
    console.error('Ошибка при обновлении пользователя:', error)
    alert('Ошибка при обновлении пользователя: ' + (error.message || 'Неизвестная ошибка'))
  }
}
const approveSelectedUser = async () => {
  if (!selectedUser.value) return
  const id = selectedUser.value.user_id || selectedUser.value.id
  try {
    await adminStore.approveUser(id)
    closeEditUser()
    // Автоматическое обновление данных
    await refreshAfterAction()
  } catch (error) {
    // Ошибка при одобрении пользователя
  }
}
const rejectSelectedUser = async () => {
  if (!selectedUser.value) return
  const id = selectedUser.value.user_id || selectedUser.value.id
  try {
    await adminStore.rejectUser(id)
    closeEditUser()
    // Автоматическое обновление данных
    await refreshAfterAction()
  } catch (error) {
    // Ошибка при отклонении пользователя
  }
}

const handleUserAction = (user, event) => {
  const action = event?.target?.value
  if (!action) return
  switch (action) {
    case 'edit':
      openEditUser(user)
      break
    case 'approve':
      approveUser(user)
      break
    case 'block':
      blockUser(user)
      break
    case 'unblock':
      unblockUser(user)
      break
    case 'delete':
      deleteUser(user.user_id || user.id)
      break
    default:
      break
  }
  if (event && event.target) {
    event.target.value = ''
  }
}

const deleteUser = async (userId) => {
  if (confirm('Вы уверены, что хотите удалить этого пользователя?')) {
    try {
      await adminStore.deleteUser(userId)
      // Автоматическое обновление данных
      await refreshAfterAction()
    } catch (error) {
      // Ошибка при удалении пользователя
    }
  }
}

const approveUser = async (user) => {
  const id = user.user_id || user.id
  try {
    await adminStore.approveUser(id)
    // Автоматическое обновление данных
    await refreshAfterAction()
  } catch (error) {
    // Error handled silently
  }
}
const rejectUser = async (user) => {
  const id = user.user_id || user.id
  try {
    await adminStore.rejectUser(id)
    // Автоматическое обновление данных
    await refreshAfterAction()
  } catch (error) {
    // Error handled silently
  }
}

const blockUser = async (user) => {
  const id = user.user_id || user.id
  try {
    await adminStore.blockUser(id)
    // Автоматическое обновление данных
    await refreshAfterAction()
  } catch (error) {
    // Error handled silently
  }
}

const unblockUser = async (user) => {
  const id = user.user_id || user.id
  try {
    await adminStore.unblockUser(id)
    // Автоматическое обновление данных
    await refreshAfterAction()
  } catch (error) {
    // Error handled silently
  }
}

const deleteStation = async (stationId) => {
  if (confirm('Вы уверены, что хотите удалить эту станцию?')) {
    try {
      await adminStore.deleteStation(stationId)
      // Автоматическое обновление данных
      await refreshAfterAction()
    } catch (error) {
      // Ошибки синхронизации с сервером обрабатываются в сторе; UI остаётся консистентным
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



const handleUserAdded = async (userData) => {
  try {
    await adminStore.createUser(userData)
    showAddUserModal.value = false
    // Автоматическое обновление данных
    await refreshAfterAction()
  } catch (error) {
    // Error handled silently
  }
}

const handleStationAdded = async (stationData) => {
  try {
    await adminStore.createStation(stationData)
    showAddStationModal.value = false
    editingStation.value = null
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
    editingStation.value = null
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
    editingStation.value = null
    
    // Автоматическое обновление данных
    await refreshAfterAction()
  } catch (error) {
    // Error handled silently
  }
}

const handleStationActivationRequired = (station) => {
  // Закрываем модальное окно редактирования
  showAddStationModal.value = false
  editingStation.value = null
  
  // Показываем модальное окно активации
  stationToActivate.value = station
  showStationActivationModal.value = true
}

const openEditStation = (station) => {
  editingStation.value = station
  showAddStationModal.value = true
}

const editStation = (station) => {
  editingStation.value = station
  showAddStationModal.value = true
}


const closeStationModal = () => {
  showAddStationModal.value = false
  editingStation.value = null
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
    const res = await pythonAPI.getStationPowerbanks(stationId)
    selectedStationPowerbanks.value = Array.isArray(res?.available_powerbanks) ? res.available_powerbanks : []
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

const openVoiceVolume = (station) => {
  selectedStationForVolume.value = station
  showVoiceVolumeModal.value = true
}

const closeVoiceVolume = () => {
  showVoiceVolumeModal.value = false
  selectedStationForVolume.value = null
}

const handleVolumeUpdated = (data) => {
  // Можно добавить уведомление об успешном обновлении громкости
  console.log('Громкость обновлена:', data)
}

const openServerAddress = (station) => {
  selectedStationForServerAddress.value = station
  showServerAddressModal.value = true
}

const closeServerAddress = () => {
  showServerAddressModal.value = false
  selectedStationForServerAddress.value = null
}

const handleServerAddressUpdated = (data) => {
  // Можно добавить уведомление об успешном обновлении адреса сервера
  console.log('Адрес сервера обновлен:', data)
}

const restartStation = async (station) => {
  const stationId = station.station_id || station.id
  if (!stationId) {
    alert('Не удалось определить ID станции')
    return
  }

  const confirmMessage = `Вы уверены, что хотите перезагрузить станцию "${station.box_id || 'N/A'}"?`
  if (!confirm(confirmMessage)) return

  try {
    const result = await pythonAPI.restartCabinet({ station_id: stationId })
    
    if (result && result.message) {
      alert(`Команда перезагрузки отправлена: ${result.message}`)
      if (result.station_box_id) {
        console.log('Station Box ID:', result.station_box_id)
      }
      if (result.packet_hex) {
        console.log('Packet HEX:', result.packet_hex)
      }
    } else {
      alert('Команда перезагрузки отправлена')
    }
  } catch (error) {
    console.error('Ошибка при перезагрузке станции:', error)
    alert('Ошибка при перезагрузке станции: ' + (error.message || 'Неизвестная ошибка'))
  }
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
      station_id: selectedStation.value.station_id,
      user_id: userId,
      slot_number: powerbank.slot_number
    }

    const result = await pythonAPI.requestBorrowPowerbank(requestData)

    if (result && (result.status === 'success' || result.status === 'accepted')) {
      // Обновляем данные станции в админ панели
      const stationId = selectedStation.value.station_id
      await adminStore.refreshStationData(stationId)
      
      // Обновляем список повербанков в модальном окне
      const updatedResult = await pythonAPI.getStationPowerbanks(stationId)
      selectedStationPowerbanks.value = Array.isArray(updatedResult?.available_powerbanks) ? updatedResult.available_powerbanks : []
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
  if (!confirm(confirmMessage)) return

  isBorrowing.value = true
  try {
    const userId = user.value?.id || user.value?.user_id

    if (!userId) {
      alert('Не удалось определить пользователя')
      return
    }

    const requestData = {
      station_id: selectedStation.value.station_id,
      slot_number: powerbank.slot_number,
      admin_user_id: userId
    }

    await adminStore.forceEjectPowerbank(requestData)

    // Данные станции уже обновлены в store через forceEjectPowerbank
    // Обновляем список повербанков в модальном окне
    const stationId = selectedStation.value.station_id
    const updatedResult = await pythonAPI.getStationPowerbanks(stationId)
    selectedStationPowerbanks.value = Array.isArray(updatedResult?.available_powerbanks) ? updatedResult.available_powerbanks : []

  } catch (error) {
    // Ошибка при принудительном извлечении повербанка
  } finally {
    isBorrowing.value = false
  }
}

// Методы для работы с группами
const editOrgUnit = (orgUnit) => {
  editingOrgUnit.value = orgUnit
  showAddOrgUnitModal.value = true
}

const deleteOrgUnit = async (orgUnitId) => {
  if (confirm('Вы уверены, что хотите удалить эту группу?')) {
    try {
      await adminStore.deleteOrgUnit(orgUnitId)
    } catch (error) {
      // Error handled silently
    }
  }
}

const viewOrgUnitStations = (orgUnit) => {
  selectedOrgUnit.value = orgUnit
  showOrgUnitStationsModal.value = true
}

const closeOrgUnitModal = () => {
  showAddOrgUnitModal.value = false
  editingOrgUnit.value = null
}

const closeOrgUnitStationsModal = () => {
  showOrgUnitStationsModal.value = false
  selectedOrgUnit.value = null
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

// Функции автоматического обновления данных
const startAutoRefresh = () => {
  if (autoRefreshInterval.value) {
    clearInterval(autoRefreshInterval.value)
  }
  
  if (autoRefreshEnabled.value) {
    autoRefreshInterval.value = setInterval(async () => {
      try {
        await refreshCurrentTabData()
      } catch (error) {
        console.warn('Ошибка при автоматическом обновлении данных:', error)
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

const refreshCurrentTabData = async () => {
  try {
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
    console.warn('Ошибка при обновлении данных для вкладки:', activeTab.value, error)
  }
}

// Обновление данных после действий
const refreshAfterAction = async () => {
  try {
    await refreshCurrentTabData()
    // Обновление конкретных станций происходит в самих функциях действий
    // Здесь обновляем только общие данные для текущей вкладки
  } catch (error) {
    console.warn('Ошибка при обновлении данных после действия:', error)
  }
}

// Переключение автоматического обновления
const toggleAutoRefresh = () => {
  autoRefreshEnabled.value = !autoRefreshEnabled.value
  if (autoRefreshEnabled.value) {
    startAutoRefresh()
  } else {
    stopAutoRefresh()
  }
}

// Watcher для отслеживания изменений активной вкладки
watch(activeTab, (newTab, oldTab) => {
  if (newTab !== oldTab) {
    // Не перезапускаем автообновление по таймеру
    // Обновление происходит только после действий
  }
})

// Жизненный цикл
onMounted(async () => {
  // Загружаем данные без проверки роли
  try {
    const results = await Promise.all([
      adminStore.fetchUsers(),
      adminStore.fetchStations(),
      adminStore.fetchOrders(),
      adminStore.fetchOrgUnits()
    ])

    // Не запускаем автоматическое обновление по таймеру
    // Обновление происходит только после действий
  } catch (error) {
    // Error handled silently
  }
})

onUnmounted(() => {
  // Останавливаем автоматическое обновление при размонтировании
  stopAutoRefresh()
})
</script>

<style scoped>
.admin-panel {
  min-height: 100vh;
  background: #f5f5f5;
}

.admin-header {
  background: white;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 20px;
}

.btn-back {
  padding: 10px 20px;
  background: #6c757d;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.3s ease;
  font-size: 1rem;
}

.btn-back:hover {
  background: #5a6268;
}

.header-content h1 {
  color: #333;
  font-size: 1.8rem;
  font-weight: 700;
  margin: 0;
  flex: 1;
}

.user-info {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 5px;
}

.auto-refresh-control {
  margin-bottom: 5px;
}

.auto-refresh-btn {
  background: #f8f9fa;
  border: 2px solid #e9ecef;
  border-radius: 50%;
  width: 35px;
  height: 35px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 16px;
}

.auto-refresh-btn:hover {
  background: #e9ecef;
  transform: scale(1.1);
}

.auto-refresh-btn.active {
  background: #667eea;
  border-color: #667eea;
  color: white;
}

.auto-refresh-btn.active:hover {
  background: #5a6fd8;
  border-color: #5a6fd8;
}

.user-role {
  color: #667eea;
  font-weight: 600;
  font-size: 0.9rem;
}

.user-name {
  color: #666;
  font-size: 0.9rem;
}

.admin-main {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

.admin-layout {
  display: flex;
  gap: 20px;
}

.admin-sidebar {
  width: 250px;
  background: white;
  border-radius: 15px;
  padding: 20px;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.sidebar-item {
  padding: 15px;
  background: #f8f9fa;
  border: none;
  border-radius: 8px;
  text-align: left;
  cursor: pointer;
  transition: all 0.3s;
}

.sidebar-item.active {
  background: #667eea;
  color: white;
}

.sidebar-item:hover {
  background: #e9ecef;
}

.admin-content {
  flex: 1;
}

.header-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.search-input {
  padding: 10px;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  width: 300px;
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

/* Users */
.users-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 20px;
}

.users-table th,
.users-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #e9ecef;
  vertical-align: middle;
  color: #333;
}

.users-table th {
  background: #f8f9fa;
  font-weight: 600;
}

/* User status strip in name cell */
.user-cell {
  position: relative;
  border-left: 6px solid transparent;
  padding-left: 10px;
}
.user-cell.user-status-active { border-left-color: #28a745; }
.user-cell.user-status-pending { border-left-color: #ffc107; }
.user-cell.user-status-blocked { border-left-color: #dc3545; }
.user-name-text { display: inline-block; }

/* Stations */
.stations-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 20px;
  margin-top: 20px;
}

.station-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  border: 2px solid transparent;
  transition: all 0.3s ease;
  overflow: hidden;
}

.station-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}

.station-card.status-active {
  border-color: #28a745;
}

.station-card.status-pending {
  border-color: #ffc107;
}

.station-card.status-inactive {
  border-color: #dc3545;
}

.station-card.status-maintenance {
  border-color: #fd7e14;
}

.station-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
}

.station-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-indicator.status-active {
  background: #28a745;
  box-shadow: 0 0 8px rgba(40, 167, 69, 0.5);
}

.status-indicator.status-pending {
  background: #ffc107;
  box-shadow: 0 0 8px rgba(255, 193, 7, 0.5);
}

.status-indicator.status-inactive {
  background: #dc3545;
  box-shadow: 0 0 8px rgba(220, 53, 69, 0.5);
}

.status-indicator.status-maintenance {
  background: #fd7e14;
  box-shadow: 0 0 8px rgba(253, 126, 20, 0.5);
}

.status-text {
  font-size: 12px;
  font-weight: 600;
  color: #333;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.station-actions {
  display: flex;
  gap: 8px;
}

.btn-action {
  background: none;
  border: none;
  padding: 8px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 16px;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-action:hover {
  background: #e9ecef;
  transform: scale(1.1);
}

.btn-powerbanks:hover {
  background: #d4edda;
}

.btn-edit:hover {
  background: #fff3cd;
}

.btn-delete:hover {
  background: #f8d7da;
}

.btn-volume:hover {
  background: #d1ecf1;
}

.btn-server:hover {
  background: #e8f5e8;
}

.btn-restart:hover {
  background: #fff3cd;
}

.station-card-content {
  padding: 20px;
}

.station-main-info {
  margin-bottom: 16px;
}

.station-title {
  font-size: 18px;
  font-weight: 700;
  color: #333;
  margin: 0 0 4px 0;
  font-family: 'Courier New', monospace;
}

.station-org {
  font-size: 14px;
  color: #667eea;
  margin: 0;
  font-weight: 500;
}

.station-details {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
}

.detail-label {
  font-size: 13px;
  color: #666;
  font-weight: 500;
}

.detail-value {
  font-size: 13px;
  color: #333;
  font-weight: 600;
  text-align: right;
  max-width: 60%;
  word-break: break-word;
}

.station-card-footer {
  padding: 16px 20px;
  background: #f8f9fa;
  border-top: 1px solid #e9ecef;
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

/* Orders */
.order-filters {
  display: flex;
  gap: 15px;
  align-items: center;
}

.filter-select {
  padding: 10px;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  font-size: 0.9rem;
  min-width: 150px;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #666;
}

.loading-state .loading-spinner {
  margin-bottom: 15px;
}

.view-toggle {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  padding: 10px;
  background: #f8f9fa;
  border-radius: 8px;
}

.view-btn {
  padding: 8px 16px;
  background: white;
  border: 2px solid #e9ecef;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 0.9rem;
}

.view-btn:hover {
  background: #e9ecef;
}

.view-btn.active {
  background: #667eea;
  color: white;
  border-color: #667eea;
}

.orders-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.orders-table-container {
  overflow-x: auto;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

.orders-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
}

.orders-table th,
.orders-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #e9ecef;
  vertical-align: middle;
}

.orders-table th {
  background: #f8f9fa;
  font-weight: 600;
  color: #333;
  position: sticky;
  top: 0;
  z-index: 10;
}

.orders-table tbody tr:hover {
  background: #f8f9fa;
}

.order-id {
  font-weight: 600;
  color: #667eea;
}

.order-card {
  padding: 20px;
  background: #f8f9fa;
  border-radius: 10px;
  border-left: 4px solid #6f42c1;
  transition: all 0.3s ease;
}

.order-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
}

.order-info {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 15px;
}

.order-main h3 {
  color: #333;
  margin: 0 0 10px 0;
  font-size: 1.1rem;
}

.order-user,
.order-station,
.order-action {
  color: #666;
  margin: 0 0 5px 0;
  font-size: 0.9rem;
}

.order-status {
  margin-left: 20px;
}

.order-details {
  border-top: 1px solid #e9ecef;
  padding-top: 15px;
}

.order-time,
.order-completed,
.order-powerbank,
.order-slot {
  color: #666;
  margin: 0 0 5px 0;
  font-size: 0.8rem;
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

/* Role badges */
.role-badge {
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.role-service-admin {
  background: transparent;
  color: #333;
}

.role-group-admin {
  background: transparent;
  color: #333;
}

.role-subgroup-admin {
  background: transparent;
  color: #333;
}

.role-user {
  background: transparent;
  color: #333;
}

/* Group badges */
.group-badge {
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  background: transparent;
  color: #333;
  border: none;
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
  .header-content {
    padding: 15px;
    flex-direction: column;
    gap: 15px;
    text-align: center;
  }
  
  .header-content h1 {
    font-size: 1.5rem;
  }
  
  .admin-main {
    padding: 15px;
  }
  
  .admin-layout {
    flex-direction: column;
    gap: 15px;
  }

  .admin-sidebar {
    width: 100%;
    padding: 15px;
  }

  .sidebar-item {
    flex: 1;
    min-width: 120px;
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
  
  .order-filters {
    flex-direction: column;
    align-items: stretch;
  }
  
  .order-info {
    flex-direction: column;
    gap: 15px;
  }
  
  .order-status {
    margin-left: 0;
  }
  
  .stations-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }
  
  .station-card-header {
    padding: 12px 16px;
  }
  
  .station-card-content {
    padding: 16px;
  }
  
  .station-card-footer {
    padding: 12px 16px;
  }
  
  .station-actions {
    gap: 6px;
  }
  
  .btn-action {
    padding: 6px;
    font-size: 14px;
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

