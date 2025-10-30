import { defineStore } from 'pinia';
import { pythonAPI } from '../api/pythonApi';
import websocketNotificationService from '../utils/websocketNotifications';

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    token: localStorage.getItem('auth_token') || null,
    userLimits: null,
  }),
  getters: {
    isAuthenticated: (state) => !!state.token && !!state.user,
    isAdmin: (state) => {
      if (!state.user) return false;
      return ['service_admin', 'group_admin', 'subgroup_admin'].includes(state.user.role);
    },
    isServiceAdmin: (state) => state.user?.role === 'service_admin',
    isGroupAdmin: (state) => state.user?.role === 'group_admin',
    isSubgroupAdmin: (state) => state.user?.role === 'subgroup_admin',
    availableByLimit: (state) => {
      if (!state.userLimits) return null;
      return state.userLimits.available_by_limit;
    },
  },
  actions: {
    async login(credentials) {
      try {
        const phone_e164 = credentials.phone_e164;
        const password = credentials.password;

        const response = await pythonAPI.login({ phone_e164, password });

        this.token = response.token;
        this.user = response.user; // Бэкенд уже возвращает user объект
        localStorage.setItem('auth_token', response.token);

        // Загружаем лимиты пользователя сразу после логина
        await this.fetchUserLimits();

        // Подключаемся к WebSocket для получения уведомлений
        websocketNotificationService.connect(response.token);

        return response;
      } catch (error) {
        // Очищаем состояние при ошибке
        this.token = null;
        localStorage.removeItem('auth_token');
        this.user = null;
        this.userLimits = null;
        throw error;
      }
    },
    async register(data) {
      try {
        const response = await pythonAPI.register(data);

        // После успешной регистрации пользователь получает пароль на email
        // и должен дождаться подтверждения администратора
        return response;
      } catch (error) {
        throw error;
      }
    },
    async fetchProfile() {
      try {
        if (!this.token) {
          return;
        }

        const response = await pythonAPI.getProfile();
        this.user = response.user;
        
        // Получаем также лимиты пользователя
        await this.fetchUserLimits();
      } catch (error) {
        // Очищаем состояние при ошибке
        this.token = null;
        localStorage.removeItem('auth_token');
        this.user = null;
        this.userLimits = null;
        throw error;
      }
    },
    async fetchUserLimits() {
      try {
        if (!this.token) {
          return;
        }

        const response = await pythonAPI.getUserStationsAvailability();
        
        // API возвращает структуру {success: true, data: {user_limits: {...}}}
        if (response && response.data && response.data.user_limits) {
          this.userLimits = response.data.user_limits;
        }
      } catch (error) {
        console.error('Ошибка получения лимитов пользователя:', error);
        this.userLimits = null;
      }
    },
    async logout() {
      try {
        // Отключаемся от WebSocket
        websocketNotificationService.disconnect();
        
        // Для JWT токенов logout происходит на клиенте
        // Просто очищаем токен и пользователя
        this.token = null;
        this.user = null;
        this.userLimits = null;
        localStorage.removeItem('auth_token');
        
        // Очищаем сохраненные данные входа, если пользователь не выбрал "Запомнить меня"
        const rememberMe = localStorage.getItem('remember_me') === 'true';
        if (!rememberMe) {
          localStorage.removeItem('saved_phone');
          localStorage.removeItem('saved_password');
          localStorage.removeItem('remember_me');
        }
      } catch (error) {
        // В любом случае очищаем состояние
        websocketNotificationService.disconnect();
        
        this.token = null;
        this.user = null;
        this.userLimits = null;
        localStorage.removeItem('auth_token');
        
        // Очищаем сохраненные данные входа, если пользователь не выбрал "Запомнить меня"
        const rememberMe = localStorage.getItem('remember_me') === 'true';
        if (!rememberMe) {
          localStorage.removeItem('saved_phone');
          localStorage.removeItem('saved_password');
          localStorage.removeItem('remember_me');
        }
      }
    },
    async initializeAuth() {
      // Инициализация при загрузке приложения
      if (this.token && !this.user) {
        try {
          await this.fetchProfile();
        } catch (error) {
          // Очищаем невалидный токен
          this.token = null;
          localStorage.removeItem('auth_token');
        }
      }
    },
  },
});
