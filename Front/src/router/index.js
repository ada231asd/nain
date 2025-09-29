import { createRouter, createWebHistory } from 'vue-router'

// Импорт страниц
import Dashboard from '../views/Dashboard.vue'

import AdminPanel from '../views/AdminPanel.vue'
import Profile from '../views/Profile.vue'
import AddressStations from '../views/AddressStations.vue'
import Login from '../views/Login.vue'
import Register from '../views/Register.vue'
import { useAuthStore } from '../stores/auth';

const routes = [
  {
    path: '/',
    redirect: '/admin'
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: Dashboard
  },
  {
    path: '/admin',
    name: 'AdminPanel',
    component: AdminPanel
  },
  {
    path: '/profile',
    name: 'Profile',
    component: Profile
  },
  {
    path: '/address/:id',
    name: 'AddressStations',
    component: AddressStations
  },
  {
    path: '/login',
    name: 'Login',
    component: Login
  },
  {
    path: '/register',
    name: 'Register',
    component: Register
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore();
  
  // Если есть токен, но нет пользователя, пытаемся загрузить профиль
  if (authStore.token && !authStore.user) {
    try {
      await authStore.fetchProfile();
    } catch (error) {
      // Очищаем невалидный токен
      authStore.token = null;
      localStorage.removeItem('auth_token');
    }
  }
  
  // Защищаем админ панель
  if (to.name === 'AdminPanel') {
    if (!authStore.isAuthenticated) {
      next('/login');
      return;
    }

    if (!authStore.isAdmin) {
      next('/dashboard');
      return;
    }
  }
  
  // Защищаем другие страницы, требующие авторизации
  const protectedRoutes = ['Dashboard', 'Profile', 'AddressStations'];
  if (protectedRoutes.includes(to.name) && !authStore.isAuthenticated) {
    next('/login');
    return;
  }
  
  // Если пользователь авторизован и пытается зайти на страницы входа/регистрации, перенаправляем на дашборд
  if ((to.name === 'Login' || to.name === 'Register') && authStore.isAuthenticated) {
    next('/dashboard');
    return;
  }
  
  next();
});

export default router
