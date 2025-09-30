<template>
  <div class="user-page">
    <!-- Заголовок -->
    <header class="page-header">
      <button @click="goBack" class="btn-back">← Назад</button>
      <h1>Управление пользователями</h1>
      <div class="user-info">
        <span class="user-role">{{ userRoleText }}</span>
        <span class="user-name">{{ user?.phone || 'Администратор' }}</span>
      </div>
    </header>

    <!-- Основной контент -->
    <main class="page-main">
      <div class="page-content">
        <div class="section-header">
          <h2>Пользователи</h2>
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

    <!-- Loading overlay -->
    <div v-if="isLoading" class="loading-overlay">
      <div class="loading-spinner"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAdminStore } from '../../stores/admin'
import { useAuthStore } from '../../stores/auth'

import EditUserModal from '../../components/EditUserModal.vue'
import AddUserModal from '../../components/AddUserModal.vue'

const router = useRouter()
const adminStore = useAdminStore()
const authStore = useAuthStore()

// Состояние
const userSearch = ref('')

// Модальные окна
const showAddUserModal = ref(false)
const showEditUserModal = ref(false)
const selectedUser = ref(null)

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

const users = computed(() => adminStore.users)
const isLoading = computed(() => adminStore.isLoading)

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

// Методы
const goBack = () => {
  router.back()
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

const getUserGroupName = (orgUnitId) => {
  if (!orgUnitId) return 'Без группы'
  const group = adminStore.orgUnits.find(ou => ou.org_unit_id === orgUnitId)
  return group ? group.name : 'Неизвестная группа'
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
    console.error('Ошибка при одобрении пользователя:', error)
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
    console.error('Ошибка при отклонении пользователя:', error)
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
      console.error('Ошибка при удалении пользователя:', error)
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
    console.error('Ошибка при одобрении пользователя:', error)
  }
}

const blockUser = async (user) => {
  const id = user.user_id || user.id
  try {
    await adminStore.blockUser(id)
    // Автоматическое обновление данных
    await refreshAfterAction()
  } catch (error) {
    console.error('Ошибка при блокировке пользователя:', error)
  }
}

const unblockUser = async (user) => {
  const id = user.user_id || user.id
  try {
    await adminStore.unblockUser(id)
    // Автоматическое обновление данных
    await refreshAfterAction()
  } catch (error) {
    console.error('Ошибка при разблокировке пользователя:', error)
  }
}

const handleUserAdded = async (userData) => {
  try {
    await adminStore.createUser(userData)
    showAddUserModal.value = false
    // Автоматическое обновление данных
    await refreshAfterAction()
  } catch (error) {
    console.error('Ошибка при добавлении пользователя:', error)
  }
}

// Обновление данных после действий
const refreshAfterAction = async () => {
  try {
    await adminStore.fetchUsers()
  } catch (error) {
    console.warn('Ошибка при обновлении данных после действия:', error)
  }
}

onMounted(async () => {
  try {
    await Promise.all([
      adminStore.fetchUsers(),
      adminStore.fetchOrgUnits()
    ])
  } catch (error) {
    console.error('Ошибка при загрузке данных:', error)
  }
})
</script>

<style scoped>
.user-page {
  min-height: 100vh;
  background: #f5f5f5;
}

.page-header {
  background: white;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  position: sticky;
  top: 0;
  z-index: 100;
}

.page-header {
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

.page-header h1 {
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

.user-role {
  color: #667eea;
  font-weight: 600;
  font-size: 0.9rem;
}

.user-name {
  color: #666;
  font-size: 0.9rem;
}

.page-main {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

.page-content {
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

/* Users table */
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

.filter-select {
  padding: 10px;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  font-size: 0.9rem;
  min-width: 150px;
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
  background: #d4edda;
  color: #155724;
}

.status-pending {
  background: #fff3cd;
  color: #856404;
}

.status-blocked {
  background: #f8d7da;
  color: #721c24;
}

.status-error {
  background: #f8d7da;
  color: #721c24;
}

.status-unknown {
  background: #e2e3e5;
  color: #383d41;
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
  background: #dc3545;
  color: white;
}

.role-group-admin {
  background: #fd7e14;
  color: white;
}

.role-subgroup-admin {
  background: #ffc107;
  color: #212529;
}

.role-user {
  background: #6c757d;
  color: white;
}

/* Group badges */
.group-badge {
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  background: #e3f2fd;
  color: #1976d2;
  border: 1px solid #bbdefb;
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
  .page-header {
    padding: 15px;
    flex-direction: column;
    gap: 15px;
    text-align: center;
  }
  
  .page-header h1 {
    font-size: 1.5rem;
  }
  
  .page-main {
    padding: 15px;
  }
  
  .page-content {
    padding: 20px;
  }
  
  .section-header {
    flex-direction: column;
    gap: 15px;
    align-items: flex-start;
  }
  
  .header-actions {
    flex-direction: column;
    align-items: stretch;
    width: 100%;
  }
  
  .search-input {
    width: 100%;
  }
  
  .users-table {
    font-size: 0.8rem;
  }
  
  .users-table th,
  .users-table td {
    padding: 8px;
  }
}
</style>
