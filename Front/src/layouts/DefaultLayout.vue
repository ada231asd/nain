<template>
  <div class="default-layout">
    <header class="layout-header">
      <div class="layout-header__content">
        <div class="layout-header__left">
          <button
            v-if="showBackButton"
            class="layout-header__back-btn"
            @click="goBack"
            aria-label="Назад"
          >
            ←
          </button>
          
          <h1 class="layout-header__title">{{ title }}</h1>
        </div>
        
        <div class="layout-header__right">
          <slot name="header-actions" />
          
          <div v-if="user" class="layout-header__user">
            <button
              class="layout-header__user-btn"
              @click="toggleUserMenu"
              aria-label="Меню пользователя"
            >
              <span class="layout-header__user-avatar">
                {{ getUserInitials(user.name) }}
              </span>
              <span class="layout-header__user-name">{{ user.name }}</span>
              <span class="layout-header__user-arrow">▼</span>
            </button>
            
            <div
              v-if="showUserMenu"
              class="layout-header__user-menu"
              :class="{ 'layout-header__user-menu--visible': showUserMenu }"
            >
              <div class="layout-header__user-menu-header">
                <span class="layout-header__user-menu-name">{{ user.name }}</span>
                <span class="layout-header__user-menu-role">{{ getUserRoleText(user.role) }}</span>
              </div>
              
              <div class="layout-header__user-menu-actions">
                <button
                  class="layout-header__user-menu-item"
                  @click="goToProfile"
                >
                  👤 Профиль
                </button>
                
                <button
                  v-if="isAdmin"
                  class="layout-header__user-menu-item"
                  @click="goToAdmin"
                >
                  ⚙️ Админ панель
                </button>
                
                <button
                  class="layout-header__user-menu-item"
                  @click="logout"
                >
                  🚪 Выйти
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </header>
    
    <main class="layout-main">
      <slot />
    </main>
    
    <nav v-if="showBottomNavigation" class="layout-bottom-nav">
      <router-link
        v-for="item in bottomNavItems"
        :key="item.path"
        :to="item.path"
        class="layout-bottom-nav__item"
        :class="{ 'layout-bottom-nav__item--active': $route.path === item.path }"
        :aria-label="item.label"
      >
        <span class="layout-bottom-nav__icon">{{ item.icon }}</span>
        <span class="layout-bottom-nav__label">{{ item.label }}</span>
      </router-link>
    </nav>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const props = defineProps({
  title: {
    type: String,
    default: 'Заряд'
  },
  showBackButton: {
    type: Boolean,
    default: false
  },
  showBottomNavigation: {
    type: Boolean,
    default: false
  }
})

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const showUserMenu = ref(false)

// Реальные данные пользователя из auth store
const user = computed(() => {
  if (!auth.user) return null
  return {
    name: `${auth.user.first_name} ${auth.user.last_name}`.trim(),
    role: auth.user.role || 'user',
    login: auth.user.login
  }
})
const isAdmin = computed(() => user.value?.role?.includes('admin') || false)

const bottomNavItems = computed(() => [
  {
    path: '/dashboard',
    label: 'Главная',
    icon: '🏠'
  },
  {
    path: '/qr-scanner',
    label: 'Сканер',
    icon: '📱'
  },
  {
    path: '/admin',
    label: 'Админ',
    icon: '⚙️'
  }
])

const getUserInitials = (name) => {
  if (!name) return '?'
  return name
    .split(' ')
    .map(word => word.charAt(0))
    .join('')
    .toUpperCase()
    .slice(0, 2)
}

const getUserRoleText = (role) => {
  const roleMap = {
    'service_admin': 'Администратор сервиса',
    'group_admin': 'Администратор группы',
    'subgroup_admin': 'Администратор подгруппы',
    'user': 'Пользователь'
  }
  return roleMap[role] || role
}

const toggleUserMenu = () => {
  showUserMenu.value = !showUserMenu.value
}

const goBack = () => {
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push('/admin')
  }
}

const goToProfile = () => {
  showUserMenu.value = false
  router.push('/profile')
}

const goToAdmin = () => {
  showUserMenu.value = false
  router.push('/admin')
}

const logout = async () => {
  showUserMenu.value = false
  try {
    await auth.logout()
    router.push('/login')
  } catch (error) {
    // Даже если logout на сервере не удался, очищаем локальное состояние
    auth.logout()
    router.push('/login')
  }
}

const handleClickOutside = (event) => {
  const userMenu = document.querySelector('.layout-header__user-menu')
  const userBtn = document.querySelector('.layout-header__user-btn')
  
  if (userMenu && userBtn && !userMenu.contains(event.target) && !userBtn.contains(event.target)) {
    showUserMenu.value = false
  }
}

const handleEscape = (event) => {
  if (event.key === 'Escape') {
    showUserMenu.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  document.addEventListener('keydown', handleEscape)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  document.removeEventListener('keydown', handleEscape)
})
</script>

<style scoped>
.default-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: var(--background-color);
}

.layout-header {
  background: var(--background-color);
  border-bottom: 1px solid var(--border-color);
  position: sticky;
  top: 0;
  z-index: 100;
  backdrop-filter: blur(10px);
  background-color: rgba(255, 255, 255, 0.95);
}

.layout-header__content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}

.layout-header__left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.layout-header__back-btn {
  background: none;
  border: none;
  font-size: 20px;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 8px;
  border-radius: 8px;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
}

.layout-header__back-btn:hover {
  background-color: var(--background-hover);
  color: var(--text-primary);
}

.layout-header__title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.layout-header__right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.layout-header__user {
  position: relative;
}

.layout-header__user-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  background: none;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 8px 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  color: var(--text-primary);
}

.layout-header__user-btn:hover {
  background-color: var(--background-hover);
  border-color: var(--primary-color);
}

.layout-header__user-avatar {
  width: 24px;
  height: 24px;
  background-color: var(--primary-color);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.layout-header__user-name {
  font-size: 14px;
  font-weight: 500;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.layout-header__user-arrow {
  font-size: 10px;
  color: var(--text-secondary);
  transition: transform 0.2s ease;
}

.layout-header__user-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 8px;
  background: var(--background-color);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
  min-width: 200px;
  opacity: 0;
  visibility: hidden;
  transform: translateY(-10px);
  transition: all 0.2s ease;
  z-index: 1000;
}

.layout-header__user-menu--visible {
  opacity: 1;
  visibility: visible;
  transform: translateY(0);
}

.layout-header__user-menu-header {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
}

.layout-header__user-menu-name {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 2px;
}

.layout-header__user-menu-role {
  display: block;
  font-size: 12px;
  color: var(--text-secondary);
}

.layout-header__user-menu-actions {
  padding: 8px 0;
}

.layout-header__user-menu-item {
  display: block;
  width: 100%;
  text-align: left;
  background: none;
  border: none;
  padding: 8px 16px;
  cursor: pointer;
  transition: background-color 0.2s ease;
  color: var(--text-primary);
  font-size: 14px;
}

.layout-header__user-menu-item:hover {
  background-color: var(--background-hover);
}

.layout-main {
  flex: 1;
  padding: 16px;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}

.layout-bottom-nav {
  background: var(--background-color);
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: space-around;
  padding: 8px 0;
  position: sticky;
  bottom: 0;
  z-index: 100;
}

.layout-bottom-nav__item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 8px 12px;
  text-decoration: none;
  color: var(--text-secondary);
  transition: all 0.2s ease;
  border-radius: 8px;
  min-width: 60px;
}

.layout-bottom-nav__item:hover {
  color: var(--text-primary);
  background-color: var(--background-hover);
}

.layout-bottom-nav__item--active {
  color: var(--primary-color);
  background-color: rgba(59, 130, 246, 0.1);
}

.layout-bottom-nav__icon {
  font-size: 20px;
  line-height: 1;
}

.layout-bottom-nav__label {
  font-size: 11px;
  font-weight: 500;
  text-align: center;
  line-height: 1;
}

/* Mobile optimizations */
@media (max-width: 768px) {
  .layout-header__content {
    padding: 8px 12px;
  }
  
  .layout-header__title {
    font-size: 16px;
  }
  
  .layout-header__user-name {
    display: none;
  }
  
  .layout-header__user-btn {
    padding: 6px 8px;
  }
  
  .layout-main {
    padding: 12px;
  }
  
  .layout-bottom-nav {
    padding: 4px 0;
  }
  
  .layout-bottom-nav__item {
    padding: 6px 8px;
    min-width: 50px;
  }
  
  .layout-bottom-nav__icon {
    font-size: 18px;
  }
  
  .layout-bottom-nav__label {
    font-size: 10px;
  }
}

/* Touch device optimizations */
@media (hover: none) and (pointer: coarse) {
  .layout-header__back-btn,
  .layout-header__user-btn {
    min-width: 44px;
    min-height: 44px;
  }
  
  .layout-bottom-nav__item {
    min-height: 44px;
  }
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  .layout-header {
    background-color: rgba(0, 0, 0, 0.95);
  }
  
  .layout-header__user-menu {
    background: var(--background-dark);
    border-color: var(--border-dark);
  }
}

/* High contrast mode */
@media (prefers-contrast: high) {
  .layout-header {
    border-bottom-width: 2px;
  }
  
  .layout-bottom-nav {
    border-top-width: 2px;
  }
}
</style>
