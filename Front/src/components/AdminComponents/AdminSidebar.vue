<template>
  <aside class="admin-sidebar">
    <!-- Логотип и название группы -->
    <div class="group-header">
      <div class="group-logo">
        <img src="../../../10064.jpg" alt="Логотип группы" class="logo-image" />
      </div>
      <div class="group-info">
        <h3 class="group-name">{{ getCurrentGroupName() }}</h3>
        <p class="group-type">{{ getCurrentGroupType() }}</p>
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
  
  // Получаем название группы пользователя
  const orgUnitId = user.parent_org_unit_id || user.org_unit_id
  if (!orgUnitId) return 'Без группы'
  
  const group = adminStore.orgUnits.find(ou => ou.org_unit_id === orgUnitId)
  return group ? group.name : 'Неизвестная группа'
}

const getCurrentGroupType = () => {
  const user = authStore.user
  if (!user) return ''
  
  // Получаем название группы пользователя
  const orgUnitId = user.parent_org_unit_id || user.org_unit_id
  if (!orgUnitId) return ''
  
  const group = adminStore.orgUnits.find(ou => ou.org_unit_id === orgUnitId)
  if (!group) return ''
  
  // Возвращаем тип группы (группа или подгруппа)
  switch (group.unit_type) {
    case 'group': return 'Группа'
    case 'subgroup': return 'Подгруппа'
    default: return group.unit_type || ''
  }
}
</script>

<style scoped>
.admin-sidebar {
  width: 250px;
  background: white;
  border-radius: 15px;
  padding: 20px;
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

.logo-image {
  max-width: 100%;
  width: auto;
  height: auto;
  max-height: 80px;
  object-fit: contain;
  border-radius: 8px;
  border: 2px solid #667eea;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
  background: white;
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

.group-type {
  color: #667eea;
  font-size: 0.85rem;
  font-weight: 600;
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
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
    padding: 15px;
  }

  .group-header {
    padding: 10px 0 15px 0;
  }

  .logo-image {
    max-height: 60px;
  }

  .group-name {
    font-size: 1rem;
  }

  .group-type {
    font-size: 0.8rem;
  }

  .sidebar-item {
    flex: 1;
    min-width: 120px;
  }
}
</style>
