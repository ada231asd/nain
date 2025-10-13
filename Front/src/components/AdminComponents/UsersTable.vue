<template>
  <div class="users-table-container">
    <!-- Заголовок с поиском и действиями -->
    <div class="users-table-header">
      <div class="users-table-title">
        <h2>Пользователи</h2>
      </div>
      <div class="users-table-actions">
        <div class="search-container">
          <input 
            type="text" 
            v-model="searchQuery" 
            placeholder="Поиск по ФИО, телефону, email, роли..." 
            class="search-input"
          />
          <span class="search-icon">🔍</span>
        </div>
        <button @click="$emit('add-user')" class="btn-add-user">
          + Добавить пользователя
        </button>
        <button @click="$emit('bulk-import')" class="btn-bulk-import">
          Импорт из Excel
        </button>
        <FilterButton 
          filter-type="users"
          :org-units="orgUnits"
          :show-role-filter="true"
          @filter-change="handleFilterChange"
        />
      </div>
    </div>

    <!-- Панель массовых действий -->
    <div v-if="selectedUsers.length > 0" class="bulk-actions-bar">
      <div class="bulk-actions-info">
        <span class="bulk-selected-text">Выбрано: {{ selectedUsers.length }}</span>
        <button @click="clearSelection" class="btn-clear-selection">
          ✕ Снять выделение
        </button>
      </div>
      <div class="bulk-actions-buttons">
        <button @click="handleBulkAction('approve')" class="btn-bulk-action btn-approve">
          ✅ Одобрить выбранных
        </button>
        <button @click="handleBulkAction('block')" class="btn-bulk-action btn-block">
          🚫 Заблокировать выбранных
        </button>
        <button @click="handleBulkAction('delete')" class="btn-bulk-action btn-delete">
          🗑️ Удалить выбранных
        </button>
      </div>
    </div>

    <!-- Таблица пользователей -->
    <div class="table-wrapper">
      <table class="users-table">
        <thead>
          <tr>
            <th class="col-checkbox">
              <input 
                type="checkbox" 
                :checked="isAllSelected"
                @change="toggleSelectAll"
                class="checkbox-input"
              />
            </th>
            <th class="col-fio">ФИО</th>
            <th class="col-phone">Телефон</th>
            <th class="col-email">Email</th>
            <th class="col-role">Роль</th>
            <th class="col-group">Группа</th>
            <th class="col-status">Статус</th>
            <th class="col-created">Создан</th>
            <th class="col-last-login">Последний вход</th>
          </tr>
        </thead>
        <tbody>
          <tr 
            v-for="user in paginatedUsers" 
            :key="user.user_id || user.id"
            class="user-row"
            :class="[getUserRowClass(user.status), { 'row-selected': isUserSelected(user) }]"
          >
            <!-- Чекбокс -->
            <td class="col-checkbox user-cell" :class="`user-status-${getUserStatusClass(user.status)}`" @click.stop>
              <input 
                type="checkbox" 
                :checked="isUserSelected(user)"
                @change="toggleUserSelection(user)"
                class="checkbox-input"
              />
            </td>

            <!-- ФИО -->
            <td class="col-fio" @click="openUserModal(user)">
              <div class="user-name-info">
                <span class="user-name" :title="user.fio || 'N/A'">{{ truncateText(user.fio || 'N/A', 9) }}</span>      
              </div>
            </td>

            <!-- Телефон -->
            <td class="col-phone" @click="openUserModal(user)">
              <span class="phone-text">{{ user.phone_e164 || 'N/A' }}</span>
            </td>

            <!-- Email -->
            <td class="col-email" @click="openUserModal(user)">
              <span class="email-text" :title="user.email || 'N/A'">{{ truncateText(user.email || 'N/A', 19) }}</span>
            </td>

            <!-- Роль -->
            <td class="col-role" @click="openUserModal(user)">
              <span class="role-badge" :class="getUserRoleClass(user.role)">
                {{ getUserRoleText(user.role) }}
              </span>
            </td>

            <!-- Группа -->
            <td class="col-group" @click="openUserModal(user)">
              <span class="group-badge">
                {{ getUserGroupName(user.parent_org_unit_id || user.org_unit_id) }}
              </span>
            </td>

            <!-- Статус -->
            <td class="col-status" @click="openUserModal(user)">
              <div class="status-container">
                <span class="status-indicator" :class="getUserStatusClass(user.status)"></span>
                <span class="status-text">{{ getUserStatusText(user.status) }}</span>
              </div>
            </td>

            <!-- Создан -->
            <td class="col-created" @click="openUserModal(user)">
              <span class="date-text">{{ user.created_at ? formatTime(user.created_at) : 'N/A' }}</span>
            </td>

            <!-- Последний вход -->
            <td class="col-last-login" @click="openUserModal(user)">
              <span class="date-text">{{ user.last_login_at ? formatTime(user.last_login_at) : 'N/A' }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Пагинация -->
    <div v-if="totalPages > 1" class="pagination">
      <button 
        @click="currentPage = Math.max(1, currentPage - 1)"
        :disabled="currentPage === 1"
        class="pagination-btn pagination-prev"
      >
        ← Предыдущая
      </button>
      
      <div class="pagination-pages">
        <button 
          v-for="page in visiblePages" 
          :key="page"
          @click="currentPage = page"
          :class="['pagination-page', { active: page === currentPage }]"
        >
          {{ page }}
        </button>
      </div>
      
      <button 
        @click="currentPage = Math.min(totalPages, currentPage + 1)"
        :disabled="currentPage === totalPages"
        class="pagination-btn pagination-next"
      >
        Следующая →
      </button>
    </div>

    <!-- Пустое состояние -->
    <div v-if="filteredUsers.length === 0" class="empty-state">
      <div class="empty-icon">👥</div>
      <h3>Пользователи не найдены</h3>
      <p v-if="searchQuery">Попробуйте изменить поисковый запрос</p>
      <p v-else>Добавьте первого пользователя</p>
    </div>

    <!-- Модальное окно с детальной информацией о пользователе -->
    <div v-if="isModalOpen" class="modal-overlay" @click="closeUserModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>Детальная информация о пользователе</h3>
          <button @click="closeUserModal" class="modal-close-btn">×</button>
        </div>
        
        <div class="modal-body" v-if="selectedUser">
          <div class="user-details">
            <!-- Основная информация -->
            <div class="detail-section">
              <h4>Основная информация</h4>
              <div class="detail-rows">
                <div class="detail-row" :class="{ 'editable-field': isEditing }">
                  <span class="detail-label">ФИО:</span>
                  <span v-if="!isEditing" class="detail-value">{{ selectedUser.fio || 'N/A' }}</span>
                  <input v-else v-model="editForm.fio" class="edit-input" type="text" placeholder="Введите ФИО" />
                </div>
                <div class="detail-row" :class="{ 'editable-field': isEditing }">
                  <span class="detail-label">Телефон:</span>
                  <span v-if="!isEditing" class="detail-value">{{ selectedUser.phone_e164 || 'N/A' }}</span>
                  <input v-else v-model="editForm.phone_e164" class="edit-input" type="tel" placeholder="Введите телефон" />
                </div>
                <div class="detail-row" :class="{ 'editable-field': isEditing }">
                  <span class="detail-label">Email:</span>
                  <span v-if="!isEditing" class="detail-value">{{ selectedUser.email || 'N/A' }}</span>
                  <input v-else v-model="editForm.email" class="edit-input" type="email" placeholder="Введите email" />
                </div>
              </div>
            </div>

            <!-- Роль и статус -->
            <div class="detail-section">
              <h4>Роль и статус</h4>
              <div class="detail-rows">
                <div class="detail-row" :class="{ 'editable-field': isEditing }">
                  <span class="detail-label">Роль:</span>
                  <span v-if="!isEditing" class="detail-value">{{ getUserRoleText(selectedUser.role) }}</span>
                  <select v-else v-model="editForm.role" class="edit-input">
                    <option value="user">Пользователь</option>
                    <option value="subgroup_admin">Администратор подгруппы</option>
                    <option value="group_admin">Администратор группы</option>
                    <option value="service_admin">Сервис-администратор</option>
                  </select>
                </div>
                <div class="detail-row" :class="{ 'editable-field': isEditing }">
                  <span class="detail-label">Статус:</span>
                  <span v-if="!isEditing" class="detail-value">{{ getUserStatusText(selectedUser.status) }}</span>
                  <select v-else v-model="editForm.status" class="edit-input">
                    <option value="pending">Ожидает</option>
                    <option value="active">Активен</option>
                    <option value="blocked">Заблокирован</option>
                  </select>
                </div>
                <div class="detail-row" :class="{ 'editable-field': isEditing }">
                  <span class="detail-label">Группа:</span>
                  <span v-if="!isEditing" class="detail-value">{{ getUserGroupName(selectedUser.parent_org_unit_id || selectedUser.org_unit_id) }}</span>
                  <select v-else v-model="editForm.parent_org_unit_id" class="edit-input">
                    <option value="">Без группы</option>
                    <option v-for="orgUnit in orgUnits" :key="orgUnit.org_unit_id" :value="orgUnit.org_unit_id">
                      {{ orgUnit.name }}
                    </option>
                  </select>
                </div>
              </div>
            </div>

            <!-- Дополнительная информация -->
            <div class="detail-section" v-if="selectedUser.user_id || selectedUser.id">
              <h4>Дополнительная информация</h4>
              <div class="detail-rows">
                <div class="detail-row">
                  <span class="detail-label">ID пользователя:</span>
                  <span class="detail-value">{{ selectedUser.user_id || selectedUser.id }}</span>
                </div>
                <div class="detail-row" v-if="selectedUser.created_at">
                  <span class="detail-label">Дата создания:</span>
                  <span class="detail-value">{{ formatTime(selectedUser.created_at) }}</span>
                </div>
                <div class="detail-row" v-if="selectedUser.last_login_at">
                  <span class="detail-label">Последний вход:</span>
                  <span class="detail-value">{{ formatTime(selectedUser.last_login_at) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <div v-if="isEditing" class="edit-actions">
            <button @click="saveChanges" class="btn-action btn-save">
              💾 Сохранить
            </button>
            <button @click="cancelEdit" class="btn-action btn-cancel">
              ❌ Отменить
            </button>
          </div>
          <div v-else class="view-actions">
            <button @click="toggleEditMode" class="btn-action">
              ✏️ Редактировать
            </button>
            <button 
              v-if="selectedUser.status === 'pending'"
              @click="handleModalAction('approve')" 
              class="btn-action btn-approve"
            >
              ✅ Одобрить
            </button>
            <button 
              v-if="selectedUser.status === 'active'"
              @click="handleModalAction('block')" 
              class="btn-action btn-block"
            >
              🚫 Заблокировать
            </button>
            <button 
              v-if="selectedUser.status === 'blocked'"
              @click="handleModalAction('unblock')" 
              class="btn-action btn-unblock"
            >
              ✅ Разблокировать
            </button>
            <button @click="closeUserModal" class="btn-close">
              Закрыть
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import FilterButton from './FilterButton.vue'

const props = defineProps({
  users: {
    type: Array,
    default: () => []
  },
  orgUnits: {
    type: Array,
    default: () => []
  },
  itemsPerPage: {
    type: Number,
    default: 10
  }
})

const emit = defineEmits([
  'add-user',
  'approve-user',
  'block-user',
  'unblock-user',
  'delete-user',
  'user-clicked',
  'user-updated',
  'bulk-approve',
  'bulk-block',
  'bulk-delete'
])

// Состояние компонента
const searchQuery = ref('')
const currentPage = ref(1)
const itemsPerPage = ref(props.itemsPerPage)
const selectedUser = ref(null)
const isModalOpen = ref(false)
const selectedUsers = ref([])
const activeFilters = ref({
  orgUnits: [],
  statuses: [],
  roles: []
})

// Состояние редактирования
const isEditing = ref(false)
const editForm = ref({
  fio: '',
  phone_e164: '',
  email: '',
  role: 'user',
  parent_org_unit_id: '',
  status: 'pending'
})

// Вычисляемые свойства
const filteredUsers = computed(() => {
  let filtered = [...props.users]
  
  // Фильтрация по группам/подгруппам
  if (activeFilters.value.orgUnits.length > 0) {
    filtered = filtered.filter(user => {
      const userOrgUnit = user.parent_org_unit_id || user.org_unit_id
      return activeFilters.value.orgUnits.includes(userOrgUnit)
    })
  }
  
  // Фильтрация по статусу
  if (activeFilters.value.statuses.length > 0) {
    filtered = filtered.filter(user => {
      const userStatus = user.status
      return activeFilters.value.statuses.includes(userStatus)
    })
  }
  
  // Фильтрация по роли
  if (activeFilters.value.roles.length > 0) {
    filtered = filtered.filter(user => {
      return activeFilters.value.roles.includes(user.role)
    })
  }
  
  // Фильтрация по поисковому запросу
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(user => {
      const phone = (user.phone_e164 || '').toLowerCase()
      const email = (user.email || '').toLowerCase()
      const fio = (user.fio || '').toLowerCase()
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
  }
  
  return filtered
})

const totalPages = computed(() => {
  return Math.ceil(filteredUsers.value.length / itemsPerPage.value)
})

const paginatedUsers = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage.value
  const end = start + itemsPerPage.value
  return filteredUsers.value.slice(start, end)
})

const visiblePages = computed(() => {
  const pages = []
  const total = totalPages.value
  const current = currentPage.value
  
  if (total <= 7) {
    for (let i = 1; i <= total; i++) {
      pages.push(i)
    }
  } else {
    if (current <= 4) {
      for (let i = 1; i <= 5; i++) pages.push(i)
      pages.push('...')
      pages.push(total)
    } else if (current >= total - 3) {
      pages.push(1)
      pages.push('...')
      for (let i = total - 4; i <= total; i++) pages.push(i)
    } else {
      pages.push(1)
      pages.push('...')
      for (let i = current - 1; i <= current + 1; i++) pages.push(i)
      pages.push('...')
      pages.push(total)
    }
  }
  
  return pages
})

const isAllSelected = computed(() => {
  return paginatedUsers.value.length > 0 && 
         paginatedUsers.value.every(user => isUserSelected(user))
})

// Методы
const handleFilterChange = (filters) => {
  activeFilters.value = filters
  currentPage.value = 1 // Сбрасываем на первую страницу при изменении фильтров
}

const openUserModal = (user) => {
  selectedUser.value = user
  isModalOpen.value = true
  isEditing.value = false
  emit('user-clicked', user)
  
  // Инициализируем форму редактирования
  initEditForm(user)
}

// Selection methods
const isUserSelected = (user) => {
  const userId = user.user_id || user.id
  return selectedUsers.value.some(u => (u.user_id || u.id) === userId)
}

const toggleUserSelection = (user) => {
  const userId = user.user_id || user.id
  const index = selectedUsers.value.findIndex(u => (u.user_id || u.id) === userId)
  
  if (index > -1) {
    selectedUsers.value.splice(index, 1)
  } else {
    selectedUsers.value.push(user)
  }
}

const toggleSelectAll = () => {
  if (isAllSelected.value) {
    // Deselect all on current page
    paginatedUsers.value.forEach(user => {
      const userId = user.user_id || user.id
      const index = selectedUsers.value.findIndex(u => (u.user_id || u.id) === userId)
      if (index > -1) {
        selectedUsers.value.splice(index, 1)
      }
    })
  } else {
    // Select all on current page
    paginatedUsers.value.forEach(user => {
      if (!isUserSelected(user)) {
        selectedUsers.value.push(user)
      }
    })
  }
}

const clearSelection = () => {
  selectedUsers.value = []
}

const handleBulkAction = (action) => {
  if (selectedUsers.value.length === 0) return
  
  const userIds = selectedUsers.value.map(u => u.user_id || u.id)
  
  switch (action) {
    case 'approve':
      if (confirm(`Вы уверены, что хотите одобрить ${selectedUsers.value.length} пользователей?`)) {
        emit('bulk-approve', userIds)
        clearSelection()
      }
      break
    case 'block':
      if (confirm(`Вы уверены, что хотите заблокировать ${selectedUsers.value.length} пользователей?`)) {
        emit('bulk-block', userIds)
        clearSelection()
      }
      break
    case 'delete':
      if (confirm(`Вы уверены, что хотите удалить ${selectedUsers.value.length} пользователей? Это действие необратимо!`)) {
        emit('bulk-delete', userIds)
        clearSelection()
      }
      break
  }
}

const closeUserModal = () => {
  isModalOpen.value = false
  selectedUser.value = null
  isEditing.value = false
  // Очищаем форму редактирования
  editForm.value = {
    fio: '',
    phone_e164: '',
    email: '',
    role: 'user',
    parent_org_unit_id: '',
    status: 'pending'
  }
}

const handleModalAction = (action) => {
  if (!selectedUser.value) return
  
  switch (action) {
    case 'approve':
      emit('approve-user', selectedUser.value)
      break
    case 'block':
      emit('block-user', selectedUser.value)
      break
    case 'unblock':
      emit('unblock-user', selectedUser.value)
      break
  }
  
  closeUserModal()
}

// Методы для редактирования
const initEditForm = (user) => {
  editForm.value = {
    fio: user.fio || '',
    phone_e164: user.phone_e164 || '',
    email: user.email || '',
    role: user.role || 'user',
    parent_org_unit_id: user.parent_org_unit_id || user.org_unit_id || '',
    status: user.status || 'pending'
  }
}

const toggleEditMode = () => {
  if (!isEditing.value) {
    // Включаем режим редактирования
    initEditForm(selectedUser.value)
  }
  isEditing.value = !isEditing.value
}

const cancelEdit = () => {
  isEditing.value = false
  initEditForm(selectedUser.value)
}

const saveChanges = async () => {
  const userId = selectedUser.value?.user_id || selectedUser.value?.id
  if (!userId) return
  
  try {
    // Подготавливаем данные для отправки
    const formData = { ...editForm.value }
    
    // Преобразуем parent_org_unit_id в число или null
    if (formData.parent_org_unit_id === '' || formData.parent_org_unit_id === null) {
      delete formData.parent_org_unit_id
    } else {
      formData.parent_org_unit_id = parseInt(formData.parent_org_unit_id)
    }
    
    // Преобразуем статус в английский формат
    const statusMap = {
      'ожидает': 'pending',
      'активный': 'active', 
      'заблокирован': 'blocked',
      'отклонен': 'rejected',
      'pending': 'pending',
      'active': 'active',
      'blocked': 'blocked',
      'rejected': 'rejected'
    }
    if (formData.status && statusMap[formData.status]) {
      formData.status = statusMap[formData.status]
    }
    
    // Обновляем локальные данные
    Object.assign(selectedUser.value, {
      fio: formData.fio,
      phone_e164: formData.phone_e164,
      email: formData.email,
      role: formData.role,
      parent_org_unit_id: formData.parent_org_unit_id,
      статус: formData.status,
      status: formData.status
    })
    
    isEditing.value = false
    
    // Эмитим событие для обновления данных на сервере
    emit('user-updated', selectedUser.value)
    
  } catch (error) {
    console.error('Ошибка сохранения изменений:', error)
    alert('Ошибка сохранения: ' + error.message)
  }
}

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

const getUserRowClass = (status) => {
  return `user-status-${getUserStatusClass(status)}`
}

const getUserGroupName = (orgUnitId) => {
  if (!orgUnitId) return 'Без группы'
  const group = props.orgUnits.find(ou => ou.org_unit_id === orgUnitId)
  return group ? group.name : 'Неизвестная группа'
}

const formatTime = (timestamp) => {
  if (!timestamp) return '—'
  const date = new Date(timestamp)
  return date.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const truncateText = (text, maxLength) => {
  if (!text || text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

// Сброс страницы при изменении поиска
watch(searchQuery, () => {
  currentPage.value = 1
})

// Очистка выбора при смене страницы
watch(currentPage, () => {
  // Можно оставить выбор или очистить - пока оставляем
})
</script>

<style scoped>
.users-table-container {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: calc(100vh - 120px);
  max-height: 900px;
}

.users-table-header {
  padding: 20px 24px;
  border-bottom: 1px solid #e9ecef;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f8f9fa;
  flex-shrink: 0;
}

.users-table-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.users-table-title h2 {
  margin: 0;
  color: #333;
  font-size: 1.5rem;
  font-weight: 700;
}

.users-count {
  background: #667eea;
  color: white;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 600;
}

.selected-count {
  background: #28a745;
  color: white;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 600;
  margin-left: 8px;
}

.users-table-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.search-container {
  position: relative;
  display: flex;
  align-items: center;
}

.search-input {
  padding: 10px 16px 10px 40px;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  width: 350px;
  font-size: 0.9rem;
  transition: border-color 0.3s ease;
}

.search-input:focus {
  outline: none;
  border-color: #667eea;
}

.search-icon {
  position: absolute;
  left: 12px;
  color: #666;
  font-size: 16px;
}

.btn-add-user {
  padding: 10px 20px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: background-color 0.3s ease;
}

.btn-add-user:hover {
  background: #5a6fd8;
}

.btn-bulk-import {
  padding: 10px 20px;
  background: #28a745;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: background-color 0.3s ease;
  margin-left: 10px;
}

.btn-bulk-import:hover {
  background: #218838;
}

/* Панель массовых действий */
.bulk-actions-bar {
  padding: 16px 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-bottom: 1px solid #e9ecef;
  display: flex;
  justify-content: space-between;
  align-items: center;
  animation: slideDown 0.3s ease-out;
  flex-shrink: 0;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.bulk-actions-info {
  display: flex;
  align-items: center;
  gap: 16px;
}

.bulk-selected-text {
  color: white;
  font-weight: 600;
  font-size: 0.95rem;
}

.btn-clear-selection {
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.3s ease;
}

.btn-clear-selection:hover {
  background: rgba(255, 255, 255, 0.3);
  border-color: rgba(255, 255, 255, 0.5);
}

.bulk-actions-buttons {
  display: flex;
  gap: 12px;
}

.btn-bulk-action {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.9rem;
  transition: all 0.3s ease;
  color: white;
}

.btn-bulk-action:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.btn-bulk-action.btn-approve {
  background: #28a745;
}

.btn-bulk-action.btn-approve:hover {
  background: #218838;
}

.btn-bulk-action.btn-block {
  background: #ffc107;
  color: #333;
}

.btn-bulk-action.btn-block:hover {
  background: #e0a800;
}

.btn-bulk-action.btn-delete {
  background: #dc3545;
}

.btn-bulk-action.btn-delete:hover {
  background: #c82333;
}

.table-wrapper {
  flex: 1;
  overflow: auto;
  min-height: 0;
  position: relative;
}

.users-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
  table-layout: auto;
}

.users-table th {
  background: #f8f9fa;
  padding: 16px 12px;
  text-align: left;
  font-weight: 600;
  color: #333;
  border-bottom: 2px solid #e9ecef;
  position: sticky;
  top: 0;
  z-index: 10;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.users-table td {
  padding: 16px 12px;
  border-bottom: 1px solid #e9ecef;
  vertical-align: middle;
  color: #333;
}

.user-row {
  transition: background-color 0.2s ease;
  cursor: pointer;
}

.user-row:hover {
  background: #f8f9fa;
}

.user-row.row-selected {
  background: #e7f3ff;
}

.user-row.row-selected:hover {
  background: #d6ebff;
}

/* Checkbox column */
.col-checkbox {
  width: 50px;
  min-width: 50px;
  text-align: center;
}

/* Flexible column widths */
.col-fio {
  min-width: 80px;
  max-width: 150px;
  width: 12%;
}

.col-phone {
  min-width: 100px;
  max-width: 140px;
  width: 12%;
}

.col-email {
  min-width: 120px;
  max-width: 200px;
  width: 18%;
}

.col-role {
  min-width: 120px;
  max-width: 180px;
  width: 15%;
}

.col-group {
  min-width: 150px;
  max-width: 250px;
  width: 20%;
}

.col-status {
  min-width: 80px;
  max-width: 120px;
  width: 10%;
}

.col-created {
  min-width: 100px;
  max-width: 140px;
  width: 8%;
}

.col-last-login {
  min-width: 100px;
  max-width: 140px;
  width: 8%;
}

.checkbox-input {
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: #667eea;
}

/* User status strip in checkbox cell */
.user-cell {
  position: relative;
  border-left: 6px solid transparent;
  padding-left: 10px;
}

.user-cell.user-status-status-active { 
  border-left-color: #28a745; 
}

.user-cell.user-status-status-pending { 
  border-left-color: #ffc107; 
}

.user-cell.user-status-status-blocked { 
  border-left-color: #dc3545; 
}

.user-cell.user-status-status-error { 
  border-left-color: #dc3545; 
}

.user-name-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.user-name {
  font-weight: 500;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
  max-width: 100%;
}

.phone-text, .email-text {
  font-size: 0.9rem;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
  max-width: 100%;
}

.status-container {
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

.status-indicator.status-blocked {
  background: #dc3545;
  box-shadow: 0 0 8px rgba(220, 53, 69, 0.5);
}

.status-indicator.status-error {
  background: #dc3545;
  box-shadow: 0 0 8px rgba(220, 53, 69, 0.5);
}

.status-text {
  font-size: 0.9rem;
  font-weight: 500;
  color: #333;
}

.date-text {
  font-size: 0.9rem;
  color: #666;
}

/* Role text */
.role-badge {
  display: inline-block;
  font-size: 0.85rem;
  font-weight: 500;
  color: #333;
}

/* Group text */
.group-badge {
  display: inline-block;
  font-size: 0.85rem;
  font-weight: 500;
  color: #333;
}

/* Пагинация */
.pagination {
  padding: 20px 24px;
  border-top: 1px solid #e9ecef;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f8f9fa;
  flex-shrink: 0;
}

.pagination-btn {
  padding: 8px 16px;
  background: white;
  border: 2px solid #e9ecef;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.3s ease;
}

.pagination-btn:hover:not(:disabled) {
  background: #667eea;
  color: white;
  border-color: #667eea;
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination-pages {
  display: flex;
  gap: 4px;
}

.pagination-page {
  padding: 8px 12px;
  background: white;
  border: 2px solid #e9ecef;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.3s ease;
  min-width: 40px;
}

.pagination-page:hover {
  background: #e9ecef;
}

.pagination-page.active {
  background: #667eea;
  color: white;
  border-color: #667eea;
}

/* Пустое состояние */
.empty-state {
  padding: 60px 20px;
  text-align: center;
  color: #666;
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 100%;
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
  padding: 20px;
}

.modal-content {
  background: white;
  border-radius: 12px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
  max-width: 600px;
  width: 100%;
  max-height: 90vh;
  animation: modalSlideIn 0.3s ease-out;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

@keyframes modalSlideIn {
  from {
    opacity: 0;
    transform: scale(0.9) translateY(-20px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.modal-header {
  padding: 20px 24px;
  border-bottom: 1px solid #e9ecef;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f8f9fa;
  border-radius: 12px 12px 0 0;
  flex-shrink: 0;
}

.modal-header h3 {
  margin: 0;
  color: #333;
  font-size: 1.3rem;
  font-weight: 700;
}

.modal-close-btn {
  background: none;
  border: none;
  font-size: 24px;
  color: #666;
  cursor: pointer;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: all 0.2s ease;
}

.modal-close-btn:hover {
  background: #e9ecef;
  color: #333;
}

.modal-body {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

.user-details {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.detail-section {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  border-left: 4px solid #667eea;
}

.detail-section h4 {
  margin: 0 0 16px 0;
  color: #333;
  font-size: 1.1rem;
  font-weight: 600;
}

.detail-rows {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.detail-row:last-child {
  border-bottom: none;
}

.detail-label {
  font-weight: 600;
  color: #666;
  font-size: 0.9rem;
  min-width: 140px;
}

.detail-value {
  color: #333;
  font-size: 1rem;
  text-align: right;
  flex: 1;
}

.editable-field {
  background: rgba(102, 126, 234, 0.05);
  border-radius: 6px;
  padding: 8px;
  border: 2px solid transparent;
  transition: all 0.3s ease;
}

.editable-field:hover {
  background: rgba(102, 126, 234, 0.1);
  border-color: rgba(102, 126, 234, 0.3);
}

.edit-input {
  width: 100%;
  padding: 8px 12px;
  border: 2px solid #e9ecef;
  border-radius: 6px;
  font-size: 0.9rem;
  background: white;
  transition: border-color 0.3s ease;
}

.edit-input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.edit-input[type="number"] {
  text-align: right;
}

.edit-input:disabled {
  background-color: #f8f9fa;
  color: #6c757d;
  cursor: not-allowed;
  opacity: 0.6;
}

.status-badge-large {
  display: inline-block;
  font-size: 1rem;
  font-weight: 500;
  text-align: center;
  color: #333;
}

.status-badge-large.status-active {
  color: #333;
}

.status-badge-large.status-pending {
  color: #333;
}

.status-badge-large.status-blocked {
  color: #333;
}

.status-badge-large.status-error {
  color: #333;
}

.modal-footer {
  padding: 20px 24px;
  border-top: 1px solid #e9ecef;
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  background: #f8f9fa;
  border-radius: 0 0 12px 12px;
  flex-shrink: 0;
  position: sticky;
  bottom: 0;
}

.btn-action {
  padding: 10px 16px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.3s ease;
  font-size: 0.9rem;
}

.btn-action:hover {
  background: #5a6fd8;
}

.btn-approve {
  background: #28a745;
}

.btn-approve:hover {
  background: #218838;
}

.btn-block {
  background: #dc3545;
}

.btn-block:hover {
  background: #c82333;
}

.btn-unblock {
  background: #28a745;
}

.btn-unblock:hover {
  background: #218838;
}

.btn-save {
  background: #28a745;
}

.btn-save:hover {
  background: #218838;
}

.btn-cancel {
  background: #dc3545;
}

.btn-cancel:hover {
  background: #c82333;
}

.btn-close {
  padding: 10px 20px;
  background: #6c757d;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.3s ease;
}

.btn-close:hover {
  background: #5a6268;
}

.edit-actions {
  display: flex;
  gap: 8px;
  justify-content: center;
  width: 100%;
  flex-wrap: nowrap;
}

.view-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  flex-wrap: nowrap;
  overflow-x: auto;
}

/* Responsive styles */
@media (max-width: 1200px) {
  .col-group {
    width: 18%;
    max-width: 200px;
  }
  
  .col-email {
    width: 16%;
    max-width: 180px;
  }
  
  .col-role {
    width: 14%;
    max-width: 160px;
  }
}

@media (max-width: 992px) {
  .col-fio {
    width: 15%;
    max-width: 120px;
  }
  
  .col-group {
    width: 20%;
    max-width: 180px;
  }
  
  .col-email {
    width: 18%;
    max-width: 160px;
  }
  
  .col-created,
  .col-last-login {
    width: 10%;
    max-width: 120px;
  }
}

/* Мобильные стили */
@media (max-width: 768px) {
  .users-table-header {
    flex-direction: column;
    gap: 16px;
    align-items: stretch;
  }

  .users-table-actions {
    flex-direction: column;
    gap: 12px;
  }

  .search-input {
    width: 100%;
  }

  .pagination {
    flex-direction: column;
    gap: 16px;
  }

  .pagination-pages {
    order: -1;
  }

  .users-table {
    font-size: 0.9rem;
  }

  .users-table th,
  .users-table td {
    padding: 12px 8px;
  }
  
  /* Мобильная адаптация колонок */
  .col-fio {
    width: 20%;
    min-width: 70px;
  }
  
  .col-phone {
    width: 18%;
    min-width: 90px;
  }
  
  .col-email {
    width: 25%;
    min-width: 100px;
  }
  
  .col-role {
    width: 15%;
    min-width: 100px;
  }
  
  .col-group {
    width: 22%;
    min-width: 120px;
  }
  
  .col-status {
    width: 12%;
    min-width: 70px;
  }
  
  .col-created,
  .col-last-login {
    width: 8%;
    min-width: 80px;
  }

  .modal-overlay {
    padding: 10px;
  }

  .modal-content {
    max-height: 95vh;
  }

  .modal-header {
    padding: 16px 20px;
  }

  .modal-header h3 {
    font-size: 1.1rem;
  }

  .modal-body {
    padding: 20px;
  }

  .detail-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }

  .detail-label {
    min-width: auto;
  }

  .detail-value {
    text-align: left;
  }

  .modal-footer {
    padding: 16px 20px;
    flex-direction: column;
  }

  .btn-action,
  .btn-close {
    width: 100%;
  }

  .bulk-actions-bar {
    flex-direction: column;
    gap: 12px;
    align-items: stretch;
  }

  .bulk-actions-info {
    justify-content: space-between;
  }

  .bulk-actions-buttons {
    flex-direction: column;
    gap: 8px;
  }

  .btn-bulk-action {
    width: 100%;
  }
}
</style>

