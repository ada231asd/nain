import { defineStore } from 'pinia';
import { pythonAPI } from '../api/pythonApi';

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    token: localStorage.getItem('auth_token') || null,
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

        return response;
      } catch (error) {
        // Очищаем состояние при ошибке
        this.token = null;
        localStorage.removeItem('auth_token');
        this.user = null;
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
      } catch (error) {
        // Очищаем состояние при ошибке
        this.token = null;
        localStorage.removeItem('auth_token');
        this.user = null;
        throw error;
      }
    },
    async logout() {
      try {
        // Для JWT токенов logout происходит на клиенте
        // Просто очищаем токен и пользователя
        this.token = null;
        this.user = null;
        localStorage.removeItem('auth_token');
      } catch (error) {
        // В любом случае очищаем состояние
        this.token = null;
        this.user = null;
        localStorage.removeItem('auth_token');
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
