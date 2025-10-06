<template>
  <aside class="admin-sidebar">
    <!-- Логотип и название группы -->
    <div class="group-header">
      <div class="group-logo">
        <div class="logo-placeholder">
          <span class="logo-text">🏢</span>
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
  </aside>
</template>

<script setup>
import { computed } from 'vue'
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
    (u.статус || u.status) === 'активный' || (u.статус || u.status) === 'active'
  ).length
  
  return `${activeUsers}/${groupUsers.length} пользователей`
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
  margin-bottom: 10px;
}

.logo-placeholder {
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  border: 2px solid #667eea;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.logo-text {
  font-size: 2.5rem;
  color: white;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
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
