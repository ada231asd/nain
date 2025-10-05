import { createRouter, createWebHistory } from 'vue-router'

// Импорт страниц
import Dashboard from '../views/Dashboard.vue'

import AdminPanel from '../views/AdminPanel.vue'
import UserPage from '../views/admin/UserPage.vue'
import Profile from '../views/Profile.vue'
import AddressStations from '../views/AddressStations.vue'
import Login from '../views/Login.vue'
import Register from '../views/Register.vue'
import StationInfo from '../views/StationInfo.vue'
import QRDemo from '../views/QRDemo.vue'
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
    path: '/admin/users',
    name: 'UserPage',
    component: UserPage
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
  },
  {
    path: '/station-info',
    name: 'StationInfo',
    component: StationInfo,
    meta: { requiresAuth: true }
  },
  {
    path: '/qr-demo',
    name: 'QRDemo',
    component: QRDemo
  },
  {
    path: '/:stationName',
    name: 'StationRedirect',
    component: () => import('../views/StationRedirect.vue'),
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore();
  
  console.log('Router beforeEach:', { to: to.path, name: to.name, matched: to.matched.length });
  
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
  
  // Защищаем админ панель и страницу пользователей
  if (to.name === 'AdminPanel' || to.name === 'UserPage') {
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
  const protectedRoutes = ['Dashboard', 'Profile', 'AddressStations', 'StationInfo', 'StationRedirect'];
  if (protectedRoutes.includes(to.name) && !authStore.isAuthenticated) {
    // Если это страница станции, сохраняем параметры станции для перенаправления после авторизации
    if (to.name === 'StationInfo') {
      next(`/login?station=${to.query.station}&stationName=${to.query.stationName}`);
    } else if (to.name === 'StationRedirect') {
      // Для прямых ссылок на станции по имени
      next(`/login?stationName=${to.params.stationName}`);
    } else {
      next('/login');
    }
    return;
  }
  
  // Проверяем права администратора для страниц, требующих админских прав
  if (to.meta?.requiresAdmin && !authStore.isAdmin) {
    next('/dashboard');
    return;
  }
  
  // Если пользователь авторизован и пытается зайти на страницы входа/регистрации, перенаправляем на дашборд
  if ((to.name === 'Login' || to.name === 'Register') && authStore.isAuthenticated) {
    console.log('Authenticated user trying to access login/register, redirecting to dashboard');
    console.log('Query params:', to.query);
    // Если есть параметры станции, перенаправляем на дашборд с параметром станции
    if (to.query.station) {
      console.log('Redirecting to dashboard with station params');
      next(`/dashboard?station=${to.query.station}&stationName=${to.query.stationName}`);
    } else if (to.query.stationName) {
      // Для прямых ссылок на станции по имени
      console.log('Redirecting to dashboard with stationName:', to.query.stationName);
      next(`/dashboard?stationName=${to.query.stationName}`);
    } else {
      console.log('Redirecting to dashboard without station params');
      next('/dashboard');
    }
    return;
  }
  
  // Если это роут станции, но пользователь не авторизован, перенаправляем на вход
  if (to.name === 'StationRedirect' && !authStore.isAuthenticated) {
    console.log('StationRedirect without auth, redirecting to login');
    next(`/login?stationName=${to.params.stationName}`);
    return;
  }
  
  next();
});

export default router
