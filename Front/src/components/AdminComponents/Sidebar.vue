<template>
  <aside class="admin-sidebar" :class="{ 'admin-sidebar--collapsed': isCollapsed }">
    <!-- Заголовок боковой панели -->
    <div class="admin-sidebar__header">
      <h3 class="admin-sidebar__title">Админ панель</h3>
      <button 
        class="admin-sidebar__toggle"
        @click="toggleCollapse"
        :title="isCollapsed ? 'Развернуть' : 'Свернуть'"
        aria-label="Переключить боковую панель"
      >
        {{ isCollapsed ? '→' : '←' }}
      </button>
    </div>

    <!-- Навигационные элементы -->
    <nav class="admin-sidebar__nav">
      <ul class="admin-sidebar__nav-list">
        <li 
          v-for="tab in availableTabs"
          :key="tab.id"
          class="admin-sidebar__nav-item"
        >
          <button 
            :class="['admin-sidebar__nav-link', { 'admin-sidebar__nav-link--active': activeTab === tab.id }]"
            @click="selectTab(tab.id)"
            :title="tab.name"
            :aria-label="tab.name"
          >
            <span class="admin-sidebar__nav-icon">{{ tab.icon }}</span>
            <span v-if="!isCollapsed" class="admin-sidebar__nav-text">{{ tab.name }}</span>
          </button>
        </li>
      </ul>
    </nav>

    <!-- Информация о пользователе -->
    <div v-if="!isCollapsed" class="admin-sidebar__user-info">
      <div class="admin-sidebar__user-avatar">
        {{ getUserInitials(user?.name || 'Админ') }}
      </div>
      <div class="admin-sidebar__user-details">
        <div class="admin-sidebar__user-name">{{ user?.name || 'Администратор' }}</div>
        <div class="admin-sidebar__user-role">{{ userRoleText }}</div>
      </div>
    </div>

    <!-- Свернутая информация о пользователе -->
    <div v-else class="admin-sidebar__user-info--collapsed">
      <div class="admin-sidebar__user-avatar--collapsed">
        {{ getUserInitials(user?.name || 'Админ') }}
      </div>
    </div>

    <!-- Дополнительные действия -->
    <div v-if="!isCollapsed" class="admin-sidebar__actions">
      <button 
        class="admin-sidebar__action-btn"
        @click="toggleAutoRefresh"
        :class="{ 'admin-sidebar__action-btn--active': autoRefreshEnabled }"
        :title="autoRefreshEnabled ? 'Отключить автообновление' : 'Включить автообновление'"
      >
        <span class="admin-sidebar__action-icon">{{ autoRefreshEnabled ? '🔄' : '⏸️' }}</span>
        <span class="admin-sidebar__action-text">Автообновление</span>
      </button>
    </div>
  </aside>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useAuthStore } from '../../stores/auth'

const props = defineProps({
  activeTab: {
    type: String,
    default: 'users'
  },
  autoRefreshEnabled: {
    type: Boolean,
    default: true
  },
  userRole: {
    type: String,
    default: 'service_admin'
  }
})

const emit = defineEmits(['tab-change', 'toggle-auto-refresh'])

const authStore = useAuthStore()
const isCollapsed = ref(false)

// Данные пользователя
const user = computed(() => {
  if (!authStore.user) return null
  return {
    name: `${authStore.user.first_name || ''} ${authStore.user.last_name || ''}`.trim() || 
          authStore.user.phone || 
          'Администратор',
    role: authStore.user.role || 'service_admin'
  }
})

const userRoleText = computed(() => {
  switch (props.userRole) {
    case 'service_admin': return 'Администратор сервиса'
    case 'group_admin': return 'Администратор группы'
    case 'subgroup_admin': return 'Администратор подгруппы'
    default: return 'Пользователь'
  }
})

// Доступные вкладки в зависимости от роли
const availableTabs = computed(() => {
  const tabs = [
    { id: 'users', name: 'Пользователи', icon: '👥' },
    { id: 'stations', name: 'Станции', icon: '🏢' },
    { id: 'powerbanks', name: 'Павербанки', icon: '🔋' },
    { id: 'org-units', name: 'Группы', icon: '🏛️' },
    { id: 'orders', name: 'Заказы', icon: '📋' },
    { id: 'stats', name: 'Статистика', icon: '📊' }
  ]

  // Ограничиваем доступ в зависимости от роли
  if (props.userRole === 'subgroup_admin') {
    return tabs.filter(tab => ['users', 'stations', 'org-units', 'stats'].includes(tab.id))
  } else if (props.userRole === 'group_admin') {
    return tabs.filter(tab => tab.id !== 'stats')
  }

  return tabs
})

// Методы
const getUserInitials = (name) => {
  if (!name) return '?'
  return name
    .split(' ')
    .map(word => word.charAt(0))
    .join('')
    .toUpperCase()
    .slice(0, 2)
}

const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value
}

const selectTab = (tabId) => {
  emit('tab-change', tabId)
}

const toggleAutoRefresh = () => {
  emit('toggle-auto-refresh')
}
</script>

<style scoped>
.admin-sidebar {
  width: 280px;
  background: white;
  border-radius: 15px;
  padding: 20px;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  gap: 20px;
  transition: all 0.3s ease;
  position: sticky;
  top: 20px;
  height: fit-content;
  max-height: calc(100vh - 40px);
  overflow-y: auto;
}

.admin-sidebar--collapsed {
  width: 80px;
  padding: 15px 10px;
}

.admin-sidebar__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 15px;
  border-bottom: 1px solid #e9ecef;
}

.admin-sidebar__title {
  font-size: 1.2rem;
  font-weight: 700;
  color: #333;
  margin: 0;
  transition: opacity 0.3s ease;
}

.admin-sidebar--collapsed .admin-sidebar__title {
  opacity: 0;
  width: 0;
  overflow: hidden;
}

.admin-sidebar__toggle {
  background: #f8f9fa;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 14px;
  color: #666;
}

.admin-sidebar__toggle:hover {
  background: #e9ecef;
  border-color: #667eea;
  color: #667eea;
}

.admin-sidebar__nav {
  flex: 1;
}

.admin-sidebar__nav-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.admin-sidebar__nav-item {
  margin: 0;
}

.admin-sidebar__nav-link {
  width: 100%;
  padding: 12px 16px;
  background: #f8f9fa;
  border: none;
  border-radius: 10px;
  text-align: left;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 12px;
  color: #333;
  font-size: 0.95rem;
  font-weight: 500;
  position: relative;
  overflow: hidden;
}

.admin-sidebar__nav-link:hover {
  background: #e9ecef;
  transform: translateX(2px);
}

.admin-sidebar__nav-link--active {
  background: #667eea;
  color: white;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

.admin-sidebar__nav-link--active:hover {
  background: #5a6fd8;
  transform: translateX(0);
}

.admin-sidebar__nav-icon {
  font-size: 18px;
  flex-shrink: 0;
  width: 20px;
  text-align: center;
}

.admin-sidebar__nav-text {
  transition: opacity 0.3s ease;
}

.admin-sidebar--collapsed .admin-sidebar__nav-text {
  opacity: 0;
  width: 0;
  overflow: hidden;
}

.admin-sidebar--collapsed .admin-sidebar__nav-link {
  justify-content: center;
  padding: 12px;
}

.admin-sidebar__user-info {
  padding: 15px;
  background: #f8f9fa;
  border-radius: 10px;
  display: flex;
  align-items: center;
  gap: 12px;
  border: 1px solid #e9ecef;
}

.admin-sidebar__user-info--collapsed {
  padding: 10px;
  background: #f8f9fa;
  border-radius: 10px;
  display: flex;
  justify-content: center;
  border: 1px solid #e9ecef;
}

.admin-sidebar__user-avatar {
  width: 40px;
  height: 40px;
  background: #667eea;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}

.admin-sidebar__user-avatar--collapsed {
  width: 32px;
  height: 32px;
  background: #667eea;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
}

.admin-sidebar__user-details {
  flex: 1;
  min-width: 0;
}

.admin-sidebar__user-name {
  font-size: 0.9rem;
  font-weight: 600;
  color: #333;
  margin: 0 0 2px 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.admin-sidebar__user-role {
  font-size: 0.75rem;
  color: #667eea;
  font-weight: 500;
  margin: 0;
}

.admin-sidebar__actions {
  padding-top: 15px;
  border-top: 1px solid #e9ecef;
}

.admin-sidebar__action-btn {
  width: 100%;
  padding: 10px 16px;
  background: #f8f9fa;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 10px;
  color: #666;
  font-size: 0.85rem;
  font-weight: 500;
}

.admin-sidebar__action-btn:hover {
  background: #e9ecef;
  border-color: #667eea;
  color: #667eea;
}

.admin-sidebar__action-btn--active {
  background: #667eea;
  border-color: #667eea;
  color: white;
}

.admin-sidebar__action-btn--active:hover {
  background: #5a6fd8;
  border-color: #5a6fd8;
}

.admin-sidebar__action-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.admin-sidebar__action-text {
  transition: opacity 0.3s ease;
}

.admin-sidebar--collapsed .admin-sidebar__action-text {
  opacity: 0;
  width: 0;
  overflow: hidden;
}

.admin-sidebar--collapsed .admin-sidebar__action-btn {
  justify-content: center;
  padding: 10px;
}

/* Скроллбар */
.admin-sidebar::-webkit-scrollbar {
  width: 4px;
}

.admin-sidebar::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 2px;
}

.admin-sidebar::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 2px;
}

.admin-sidebar::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

/* Мобильные стили */
@media (max-width: 768px) {
  .admin-sidebar {
    width: 100%;
    position: static;
    max-height: none;
    border-radius: 10px;
    margin-bottom: 20px;
  }

  .admin-sidebar--collapsed {
    width: 100%;
    padding: 15px;
  }

  .admin-sidebar__nav-list {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 8px;
  }

  .admin-sidebar__nav-link {
    justify-content: center;
    padding: 12px 8px;
    font-size: 0.85rem;
  }

  .admin-sidebar__nav-text {
    display: none;
  }

  .admin-sidebar__nav-icon {
    font-size: 20px;
  }

  .admin-sidebar__user-info {
    flex-direction: column;
    text-align: center;
    gap: 8px;
  }

  .admin-sidebar__user-name {
    white-space: normal;
    text-align: center;
  }
}

/* Анимации */
@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.admin-sidebar__nav-item {
  animation: slideIn 0.3s ease forwards;
}

.admin-sidebar__nav-item:nth-child(1) { animation-delay: 0.1s; }
.admin-sidebar__nav-item:nth-child(2) { animation-delay: 0.2s; }
.admin-sidebar__nav-item:nth-child(3) { animation-delay: 0.3s; }
.admin-sidebar__nav-item:nth-child(4) { animation-delay: 0.4s; }
.admin-sidebar__nav-item:nth-child(5) { animation-delay: 0.5s; }
.admin-sidebar__nav-item:nth-child(6) { animation-delay: 0.6s; }

/* Темная тема */
@media (prefers-color-scheme: dark) {
  .admin-sidebar {
    background: #1a1a1a;
    color: #e0e0e0;
  }

  .admin-sidebar__title {
    color: #e0e0e0;
  }

  .admin-sidebar__nav-link {
    background: #2a2a2a;
    color: #e0e0e0;
  }

  .admin-sidebar__nav-link:hover {
    background: #3a3a3a;
  }

  .admin-sidebar__nav-link--active {
    background: #667eea;
    color: white;
  }

  .admin-sidebar__user-info {
    background: #2a2a2a;
    border-color: #3a3a3a;
  }

  .admin-sidebar__user-name {
    color: #e0e0e0;
  }

  .admin-sidebar__action-btn {
    background: #2a2a2a;
    border-color: #3a3a3a;
    color: #e0e0e0;
  }

  .admin-sidebar__action-btn:hover {
    background: #3a3a3a;
  }
}
</style>
