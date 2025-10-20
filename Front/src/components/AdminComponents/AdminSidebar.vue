<template>
  <aside class="admin-sidebar">
    <!-- Логотип и название группы -->
    <div class="group-header">
      <div class="group-logo" @click="openLogoUpload">
        <div class="logo-placeholder" v-if="!getCurrentGroupLogo()">
          <span class="logo-text">🏢</span>
        </div>
        <div class="logo-image" v-else>
          <img :src="getCurrentGroupLogo()" :alt="getCurrentGroupName()" />
          <div class="logo-overlay">
            <span class="edit-icon">📷</span>
            <span class="edit-text">Изменить</span>
          </div>
        </div>
      </div>
      <div class="group-info">
        <h3 class="group-name">{{ getCurrentGroupName() }}</h3>
        <div class="group-stats" v-if="getGroupStats()">
          <span class="group-users-count">{{ getGroupStats() }}</span>
        </div>
      </div>
    </div>

    <!-- Меню навигации -->
    <div class="sidebar-menu">
      <button 
        v-for="tab in availableTabs"
        :key="tab.id"
        :class="['sidebar-item', { active: activeTab === tab.id }]"
        @click="$emit('tab-change', tab.id)"
      >
        {{ tab.name }}
      </button>
    </div>

    <!-- Кнопка "На главную" -->
    <div class="sidebar-footer">
      <button @click="$emit('go-home')" class="btn-home">
        🏠 На главную
      </button>
    </div>

    <!-- Скрытый input для загрузки логотипа -->
    <input 
      ref="logoInput"
      type="file"
      accept="image/*"
      @change="handleLogoChange"
      style="display: none;"
    />
  </aside>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useAuthStore } from '../../stores/auth'
import { useAdminStore } from '../../stores/admin'

// Props
const props = defineProps({
  activeTab: {
    type: String,
    required: true
  }
})

// Emits
const emit = defineEmits(['tab-change', 'go-home'])

// Stores
const authStore = useAuthStore()
const adminStore = useAdminStore()

// Refs
const logoInput = ref(null)

// Computed
const availableTabs = computed(() => {
  const tabs = [
    { id: 'users', name: 'Пользователи' },
    { id: 'stations', name: 'Станции' },
    { id: 'powerbanks', name: 'Павербанки' },
    { id: 'org-units', name: 'Группы' },
    { id: 'orders', name: 'Все заказы' },
    { id: 'slot-abnormal-reports', name: 'Аномалии слотов' },
    { id: 'stats', name: 'Статистика' }
  ]

  return tabs
})

// Methods
const getCurrentGroupName = () => {
  const user = authStore.user

  if (!user) return 'Администратор'

  // Проверяем все возможные поля для ID группы
  const orgUnitId = user.parent_org_unit_id || user.org_unit_id || user.group_id || user.organization_id
  
  // Если нет прямого ID группы, пытаемся найти группу по user_id
  let group = null
  if (!orgUnitId) {
    // Ищем группу, где user_id совпадает с текущим пользователем
    group = adminStore.orgUnits.find(ou => ou.user_id === user.user_id)

    // Если не нашли, ищем в списке пользователей
    if (!group) {
      const userInList = adminStore.users.find(u => u.user_id === user.user_id)
      if (userInList) {
        const userOrgUnitId = userInList.parent_org_unit_id || userInList.org_unit_id
        if (userOrgUnitId) {
          group = adminStore.orgUnits.find(ou => ou.org_unit_id === userOrgUnitId)
        }
      }
    }
  }
  
  if (!orgUnitId && !group) {
    // Если пользователь subgroup_admin, ищем подгруппу где он админ
    if (user.role === 'subgroup_admin') {
      group = adminStore.orgUnits.find(ou =>
        ou.unit_type === 'subgroup' &&
        (ou.admin_user_id === user.user_id || ou.user_id === user.user_id)
      )
    }
    // Если пользователь group_admin, ищем группу где он админ
    else if (user.role === 'group_admin') {
      group = adminStore.orgUnits.find(ou =>
        ou.unit_type === 'group' &&
        (ou.admin_user_id === user.user_id || ou.user_id === user.user_id)
      )
    }

    // Если все еще не нашли группу, показываем роль
    if (!group) {
      switch (user.role) {
        case 'service_admin': return 'Сервис-админ'
        case 'group_admin': return 'Админ группы'
        case 'subgroup_admin': return 'Админ подгруппы'
        default: return 'Администратор'
      }
    }
  }
  
  // Если данные о группах еще не загружены, показываем загрузку
  if (!adminStore.orgUnits || adminStore.orgUnits.length === 0) {
    return 'Загрузка...'
  }

  // Если не нашли группу по user_id, ищем по orgUnitId
  if (!group && orgUnitId) {
    group = adminStore.orgUnits.find(ou => ou.org_unit_id === orgUnitId)
  }

  if (!group) {
    return 'Неизвестная группа'
  }

  // Показываем только название найденной группы/подгруппы
  return group.name
}

const getCurrentGroupType = () => {
  const user = authStore.user
  if (!user) return ''
  
  // Используем ту же логику поиска группы, что и в getCurrentGroupName
  const orgUnitId = user.parent_org_unit_id || user.org_unit_id || user.group_id || user.organization_id
  
  let group = null
  if (!orgUnitId) {
    // Ищем группу по user_id
    group = adminStore.orgUnits.find(ou => ou.user_id === user.user_id)
    
    // Если не нашли, ищем в списке пользователей
    if (!group) {
      const userInList = adminStore.users.find(u => u.user_id === user.user_id)
      if (userInList) {
        const userOrgUnitId = userInList.parent_org_unit_id || userInList.org_unit_id
        if (userOrgUnitId) {
          group = adminStore.orgUnits.find(ou => ou.org_unit_id === userOrgUnitId)
        }
      }
    }
    
    // Если не нашли, ищем по роли
    if (!group) {
      if (user.role === 'subgroup_admin') {
        group = adminStore.orgUnits.find(ou => 
          ou.unit_type === 'subgroup' && 
          (ou.admin_user_id === user.user_id || ou.user_id === user.user_id)
        )
      } else if (user.role === 'group_admin') {
        group = adminStore.orgUnits.find(ou => 
          ou.unit_type === 'group' && 
          (ou.admin_user_id === user.user_id || ou.user_id === user.user_id)
        )
      }
    }
  } else {
    group = adminStore.orgUnits.find(ou => ou.org_unit_id === orgUnitId)
  }
  
  if (!group) return ''
  
  // Возвращаем тип группы (группа или подгруппа)
  switch (group.unit_type) {
    case 'group': return 'Группа'
    case 'subgroup': return 'Подгруппа'
    default: return group.unit_type || ''
  }
}


const getGroupStats = () => {
  const user = authStore.user
  if (!user) return null
  
  const orgUnitId = user.parent_org_unit_id || user.org_unit_id
  if (!orgUnitId) return null
  
  // Подсчитываем количество пользователей в группе
  const groupUsers = adminStore.users.filter(u => 
    (u.parent_org_unit_id || u.org_unit_id) === orgUnitId
  )
  
  if (groupUsers.length === 0) return null
  
  const activeUsers = groupUsers.filter(u => 
    u.status === 'active'
  ).length
  
  return `${activeUsers}/${groupUsers.length} пользователей`
}

// Вычисляет текущий org_unit_id по тем же правилам, что и getCurrentGroupName
const getCurrentOrgUnitId = () => {
  const user = authStore.user
  if (!user) return null

  // Прямые поля
  const directId = user.parent_org_unit_id || user.org_unit_id || user.group_id || user.organization_id
  if (directId) return directId

  // Поиск по user_id в orgUnits
  let group = adminStore.orgUnits.find(ou => ou.user_id === user.user_id)
  if (!group) {
    // Поиск по users списку
    const userInList = adminStore.users.find(u => u.user_id === user.user_id)
    if (userInList) {
      const userOrgUnitId = userInList.parent_org_unit_id || userInList.org_unit_id
      if (userOrgUnitId) {
        group = adminStore.orgUnits.find(ou => ou.org_unit_id === userOrgUnitId)
      }
    }
  }

  // Поиск по роли
  if (!group) {
    if (user.role === 'subgroup_admin') {
      group = adminStore.orgUnits.find(ou => ou.unit_type === 'subgroup' && (ou.admin_user_id === user.user_id || ou.user_id === user.user_id))
    } else if (user.role === 'group_admin') {
      group = adminStore.orgUnits.find(ou => ou.unit_type === 'group' && (ou.admin_user_id === user.user_id || ou.user_id === user.user_id))
    }
  }

  return group ? group.org_unit_id : null
}

const getCurrentGroupLogo = () => {
  const orgUnitId = getCurrentOrgUnitId()
  if (!orgUnitId) return null

  // Ищем группу в списке организационных единиц
  const group = adminStore.orgUnits.find(ou => ou.org_unit_id === orgUnitId)
  if (!group || !group.logo_url) return null

  // Если это относительный путь, добавляем базовый URL
  if (group.logo_url.startsWith('/api/')) {
    return group.logo_url
  }

  return group.logo_url
}

// Открытие диалога выбора файла
const openLogoUpload = () => {
  if (logoInput.value) {
    logoInput.value.click()
  }
}

// Обработка выбора файла логотипа
const handleLogoChange = async (event) => {
  const file = event.target.files[0]
  if (!file) return

  // Проверяем размер файла (5MB)
  if (file.size > 5 * 1024 * 1024) {
    alert('Размер файла не должен превышать 5MB')
    return
  }

  // Проверяем тип файла
  if (!file.type.startsWith('image/')) {
    alert('Выберите файл изображения')
    return
  }

  const orgUnitId = getCurrentOrgUnitId()
  if (!orgUnitId) return

  try {
    const formData = new FormData()
    formData.append('logo', file)

    const response = await fetch(`/api/org-units/${orgUnitId}/logo`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
      },
      body: formData
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.error || 'Ошибка загрузки логотипа')
    }

    const result = await response.json()
    console.log('Логотип загружен:', result)

    // Обновляем данные организационных единиц
    await adminStore.fetchOrgUnits()

    // Очищаем input
    if (logoInput.value) {
      logoInput.value.value = ''
    }

  } catch (error) {
    console.error('Ошибка загрузки логотипа:', error)
    alert('Ошибка загрузки логотипа: ' + error.message)
  }
}
</script>

<style scoped>
.admin-sidebar {
  width: 250px;
  background: white;
  border-radius: 15px;
  padding: 20px 20px 20px 12px;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.group-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 5px 0 5px 0;
  border-bottom: 2px solid #f0f0f0;
  margin-bottom: 5px;
}

.group-logo {
  margin-bottom: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.group-logo:hover {
  opacity: 0.8;
}

.logo-placeholder {
  width: 64px;
  height: 64px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  background: #f9fafb;
  position: relative;
}

.logo-text {
  font-size: 1.5rem;
  color: #6b7280;
}

.upload-hint {
  font-size: 0.6rem;
  color: #9ca3af;
  text-align: center;
  margin-top: 4px;
  font-weight: 400;
}

.logo-image {
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  background: white;
  overflow: hidden;
  position: relative;
}

.logo-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 11px;
}

.logo-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s ease;
  border-radius: 11px;
}

.logo-image:hover .logo-overlay {
  opacity: 1;
}

.edit-icon {
  font-size: 1rem;
  color: white;
  margin-bottom: 2px;
}

.edit-text {
  font-size: 0.6rem;
  color: white;
  font-weight: 400;
}

.group-info {
  text-align: center;
}

.group-name {
  color: #333;
  font-size: 1.1rem;
  font-weight: 700;
  margin: 0 0 5px 0;
  line-height: 1.2;
}

.group-stats {
  margin-top: 8px;
}

.group-users-count {
  color: #495057;
  font-size: 0.7rem;
  font-weight: 500;
  background: rgba(73, 80, 87, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
  text-align: center;
  display: block;
}

.sidebar-menu {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.sidebar-footer {
  margin-top: auto;
  padding-top: 20px;
  border-top: 2px solid #f0f0f0;
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

.btn-home {
  width: 100%;
  padding: 15px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  font-weight: 600;
  font-size: 1rem;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.btn-home:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
  background: linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%);
}

.btn-home:active {
  transform: translateY(0);
}

/* Мобильные стили */
@media (max-width: 768px) {
  .admin-sidebar {
    width: 100%;
    padding: 15px 15px 15px 8px;
  }

  .group-header {
    padding: 10px 0 15px 0;
  }

  .logo-placeholder {
    width: 60px;
    height: 60px;
  }
  
  .logo-text {
    font-size: 2rem;
  }

  .group-name {
    font-size: 1rem;
  }

  .group-users-count {
    font-size: 0.65rem;
    padding: 1px 4px;
  }

  .sidebar-item {
    flex: 1;
    min-width: 120px;
  }
}
</style>
