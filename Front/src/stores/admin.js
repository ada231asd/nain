import { defineStore } from 'pinia';
import { pythonAPI } from '../api/pythonApi';


export const useAdminStore = defineStore('admin', {
  state: () => ({
    users: [],
    stations: [],
    addresses: [],
    orders: [],
    orgUnits: [],
    powerbanks: [],
    isLoading: false,
    error: null,
  }),
  getters: {
    totalUsers: (state) => state.users.length,
    totalStations: (state) => state.stations.length,
    totalAddresses: (state) => state.addresses.length,
    totalOrders: (state) => state.orders.length,
    totalOrgUnits: (state) => state.orgUnits.length,
    totalPowerbanks: (state) => state.powerbanks.length,
    pendingUsers: (state) => state.users.filter(u => u.статус === 'ожидает' || u.status === 'pending'),
    activeStations: (state) => state.stations.filter(s => s.status === 'active'),
    activePowerbanks: (state) => state.powerbanks.filter(p => p.status === 'active'),
    todayOrders: (state) => {
      const today = new Date().setHours(0,0,0,0);
      return state.orders.filter(o => new Date(o.created_at).setHours(0,0,0,0) === today);
    },
    // Группы по типам
    groups: (state) => {
      const result = state.orgUnits.filter(ou => ou.unit_type === 'group')
      return result
    },
    subgroups: (state) => {
      const result = state.orgUnits.filter(ou => ou.unit_type === 'subgroup')
      return result
    },
    // Иерархия групп
    orgUnitsHierarchy: (state) => {
      const units = [...state.orgUnits];
      const hierarchy = [];
      
      // Находим корневые элементы (без родителя)
      const rootUnits = units.filter(unit => !unit.parent_org_unit_id);
      
      const buildHierarchy = (parent, level = 0) => {
        const children = units.filter(unit => unit.parent_org_unit_id === parent.org_unit_id);
        const item = { ...parent, level, children: [] };
        
        children.forEach(child => {
          item.children.push(buildHierarchy(child, level + 1));
        });
        
        return item;
      };
      
      rootUnits.forEach(root => {
        hierarchy.push(buildHierarchy(root));
      });
      
      return hierarchy;
    },
  },
  actions: {
    async fetchUsers() {
      this.isLoading = true;
      try {
        const res = await pythonAPI.getUsers();

        // Обрабатываем ответ в зависимости от структуры
        this.users = Array.isArray(res)
          ? res
          : (res && Array.isArray(res.data))
            ? res.data
            : (res && Array.isArray(res.users))
              ? res.users
              : [];

        return this.users;
      } catch (err) {
        this.error = 'Failed to fetch users';
        return [];
      } finally {
        this.isLoading = false;
      }
    },
    async createUser(userData) {
      try {
        const id = await pythonAPI.createUser(userData);
        await this.fetchUsers();
        return id;
      } catch (err) {
        throw err;
      }
    },
    async updateUser(id, data) {
      try {
        await pythonAPI.updateUser(id, data);
        await this.fetchUsers();
      } catch (err) {
        throw err;
      }
    },
    async deleteUser(id) {
      try {
        await pythonAPI.deleteUser(id);
        await this.fetchUsers();
      } catch (err) {
        throw err;
      }
    },
    async approveUser(id) {
      try {
        await pythonAPI.approveUser(id);
        await this.fetchUsers();
      } catch (err) {
        throw err;
      }
    },
    async rejectUser(id) {
      try {
        await pythonAPI.rejectUser(id);
        await this.fetchUsers();
      } catch (err) {
        throw err;
      }
    },
    async blockUser(id) {
      await this.updateUser(id, { статус: 'заблокирован' });
    },
    async unblockUser(id) {
      await this.updateUser(id, { статус: 'активный' });
    },
    async fetchStations() {
      this.isLoading = true;
      try {
        const res = await pythonAPI.getStations();

        // Обрабатываем ответ в зависимости от структуры
        this.stations = Array.isArray(res)
          ? res
          : (res && Array.isArray(res.data))
            ? res.data
            : (res && Array.isArray(res.stations))
              ? res.stations
              : [];

        return this.stations;
      } catch (err) {
        this.error = 'Failed to fetch stations';
        return [];
      } finally {
        this.isLoading = false;
      }
    },
    // Тихий рефетч станций без глобального индикатора загрузки
    async _refreshStationsSilently() {
      try {
        const fresh = await pythonAPI.getStations();
        const normalized = Array.isArray(fresh)
          ? fresh
          : (fresh && Array.isArray(fresh.data))
            ? fresh.data
            : (fresh && Array.isArray(fresh.stations))
              ? fresh.stations
              : null;
        if (normalized) {
          this.stations = normalized;
        }
      } catch (_err) {
        // Игнорируем, остаёмся на оптимистичном состоянии
      }
    },
    async createStation(data) {
      try {
        await pythonAPI.createStation(data);
        await this.fetchStations();
      } catch (err) {
        throw err;
      }
    },
    async updateStation(id, data) {
      // Оптимистичное обновление локального стора
      const index = this.stations.findIndex(s => (s.station_id || s.id) === id);
      const previous = index !== -1 ? { ...this.stations[index] } : null;
      if (index !== -1) {
        this.stations[index] = { ...this.stations[index], ...data };
      }
      try {
        await pythonAPI.updateStation(id, data);
        await this._refreshStationsSilently();
      } catch (err) {
        // Не рефетчим, чтобы не перезатереть оптимистичное состояние старыми данными
      }
    },
    async deleteStation(id) {
      // Оптимистичное удаление локально
      const index = this.stations.findIndex(s => (s.station_id || s.id) === id);
      let removed = null;
      if (index !== -1) {
        removed = this.stations[index];
        this.stations.splice(index, 1);
      }
      try {
        await pythonAPI.deleteStation(id);
        await this._refreshStationsSilently();
      } catch (err) {
        // Не рефетчим, чтобы не вернуть удалённую станцию из сервера
      }
    },
    async fetchAddresses() {
      this.isLoading = true;
      try {
        // Python backend does not expose addresses endpoint yet
        // TODO: Implement addresses API in pythonAPI
        this.addresses = [];
      } catch (err) {
        this.error = 'Failed to fetch addresses';
      } finally {
        this.isLoading = false;
      }
    },
    async createAddress(data) {
      try {
        // TODO: Implement createAddress in pythonAPI
        throw new Error('Address creation not implemented yet');
      } catch (err) {
        throw err;
      }
    },
    async deleteAddress(id) {
      try {
        // TODO: Implement deleteAddress in pythonAPI
        throw new Error('Address deletion not implemented yet');
      } catch (err) {
        throw err;
      }
    },
    async fetchOrders() {
      this.isLoading = true;
      try {
        const res = await pythonAPI.getOrders();
        const orders = (res && Array.isArray(res.orders)) ? res.orders : [];
        // Normalize timestamp field for UI that expects created_at
        this.orders = orders.map(o => ({ ...o, created_at: o.created_at || o.timestamp }));
      } catch (err) {
        this.error = 'Failed to fetch orders';
      } finally {
        this.isLoading = false;
      }
    },
    async fetchUserHistory(userId) {
      try {
        // TODO: Implement getUserLogs in pythonAPI
        return [];
      } catch (err) {
        return [];
      }
    },

    // ОРГАНИЗАЦИОННЫЕ ЕДИНИЦЫ
    async fetchOrgUnits(params = {}) {
      this.isLoading = true;
      try {
        const res = await pythonAPI.getOrgUnits(params);
        this.orgUnits = (res && Array.isArray(res.data)) ? res.data : [];
      } catch (err) {
        this.error = 'Failed to fetch org units';
      } finally {
        this.isLoading = false;
      }
    },
    async getOrgUnit(id) {
      try {
        const res = await pythonAPI.getOrgUnit(id);
        return res.data;
      } catch (err) {
        throw err;
      }
    },
    async getOrgUnitStations(id) {
      try {
        const res = await pythonAPI.getOrgUnitStations(id);
        // API станций возвращает данные в поле data
        return (res && Array.isArray(res.data)) ? res.data : [];
      } catch (err) {
        throw err;
      }
    },
    async createOrgUnit(data) {
      try {
        const res = await pythonAPI.createOrgUnit(data);
        await this.fetchOrgUnits();
        return res.data.org_unit_id;
      } catch (err) {
        throw err;
      }
    },
    async updateOrgUnit(id, data) {
      try {
        await pythonAPI.updateOrgUnit(id, data);
        await this.fetchOrgUnits();
      } catch (err) {
        throw err;
      }
    },
    async deleteOrgUnit(id) {
      try {
        await pythonAPI.deleteOrgUnit(id);
        await this.fetchOrgUnits();
      } catch (err) {
        throw err;
      }
    },

    // АДМИНИСТРАТИВНЫЕ ФУНКЦИИ
    async forceEjectPowerbank(data) {
      try {
        await pythonAPI.forceEjectPowerbank(data);
        // Обновляем данные станций после принудительного извлечения
        await this.fetchStations();
      } catch (err) {
        throw err;
      }
    },

    // РОЛИ ПОЛЬЗОВАТЕЛЕЙ
    async fetchUserRoles() {
      try {
        const res = await pythonAPI.getUserRoles();
        return Array.isArray(res) ? res : (res && Array.isArray(res.data)) ? res.data : [];
      } catch (err) {
        return [];
      }
    },

    // ПАВЕРБАНКИ
    async fetchPowerbanks(params = {}) {
      this.isLoading = true;
      try {
        const res = await pythonAPI.getPowerbanks(params);

        // Обрабатываем ответ в зависимости от структуры
        this.powerbanks = Array.isArray(res)
          ? res
          : (res && Array.isArray(res.data))
            ? res.data
            : (res && Array.isArray(res.powerbanks))
              ? res.powerbanks
              : [];

        return this.powerbanks;
      } catch (err) {
        this.error = 'Failed to fetch powerbanks';
        return [];
      } finally {
        this.isLoading = false;
      }
    },
    async getPowerbank(id) {
      try {
        const res = await pythonAPI.getPowerbank(id);
        return res.data;
      } catch (err) {
        throw err;
      }
    },
    async updatePowerbank(id, data) {
      try {
        await pythonAPI.updatePowerbank(id, data);
        await this.fetchPowerbanks();
      } catch (err) {
        throw err;
      }
    },
    async deletePowerbank(id) {
      try {
        await pythonAPI.deletePowerbank(id);
        await this.fetchPowerbanks();
      } catch (err) {
        throw err;
      }
    },
  },
});
