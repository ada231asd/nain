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
        // Запрашиваем всех пользователей с большим лимитом
        const res = await pythonAPI.getUsers({ limit: 10000 });

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
      try {
        // Получаем данные пользователя
        const user = this.users.find(u => u.user_id === id);
        if (!user) {
          throw new Error('Пользователь не найден');
        }
        
        // Обновляем только статус, сохраняя остальные данные
        await this.updateUser(id, {
          fio: user.fio,
          phone_e164: user.phone_e164,
          email: user.email,
          role: user.role,
          status: 'blocked',
          parent_org_unit_id: user.parent_org_unit_id || ''
        });
      } catch (err) {
        throw err;
      }
    },
    async unblockUser(id) {
      try {
        // Получаем данные пользователя
        const user = this.users.find(u => u.user_id === id);
        if (!user) {
          throw new Error('Пользователь не найден');
        }
        
        // Обновляем только статус, сохраняя остальные данные
        await this.updateUser(id, {
          fio: user.fio,
          phone_e164: user.phone_e164,
          email: user.email,
          role: user.role,
          status: 'active',
          parent_org_unit_id: user.parent_org_unit_id || ''
        });
      } catch (err) {
        throw err;
      }
    },
    async fetchStations() {
      this.isLoading = true;
      try {
        // Запрашиваем все станции с большим лимитом
        const res = await pythonAPI.getStations({ limit: 10000 });
        console.log('Raw API response for stations:', res);

        // Обрабатываем ответ в зависимости от структуры
        let stations = [];
        if (Array.isArray(res)) {
          stations = res;
        } else if (res && Array.isArray(res.data)) {
          stations = res.data;
        } else if (res && Array.isArray(res.stations)) {
          stations = res.stations;
        } else {
          console.warn('Unexpected API response structure:', res);
          stations = [];
        }

        console.log('Processed stations:', stations);
        this.stations = stations;
        return this.stations;
      } catch (err) {
        console.error('Error fetching stations:', err);
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
        let normalized = [];
        if (Array.isArray(fresh)) {
          normalized = fresh;
        } else if (fresh && Array.isArray(fresh.data)) {
          normalized = fresh.data;
        } else if (fresh && Array.isArray(fresh.stations)) {
          normalized = fresh.stations;
        }
        if (normalized) {
          this.stations = normalized;
        }
      } catch (_err) {
        // Игнорируем, остаёмся на оптимистичном состоянии
      }
    },
    // Обновление конкретной станции с актуальными данными о портах
    async refreshStationData(stationId) {
      try {
        console.log('Обновляем данные станции:', stationId);
        
        // Получаем актуальные детали станции
        const stationResponse = await pythonAPI.getStation(stationId);
        console.log('Ответ API для станции:', stationResponse);
        
        // Извлекаем данные из ответа API
        let stationDetails = stationResponse?.data || stationResponse;
        console.log('Детали станции извлечены:', stationDetails);
        
        // Если данные все еще в структуре API, извлекаем их
        if (stationDetails && stationDetails.success && stationDetails.data) {
          console.log('Извлекаем данные из вложенной структуры API');
          stationDetails = stationDetails.data;
          console.log('Финальные детали станции:', stationDetails);
        }
        
        // Получаем актуальные данные о powerbank'ах
        const powerbanksResponse = await pythonAPI.getStationPowerbanks(stationId);
        console.log('Ответ API для powerbank:', powerbanksResponse);
        
        // Извлекаем данные о powerbank'ах из ответа API
        let powerbanksData = powerbanksResponse?.data || powerbanksResponse;
        console.log('Данные powerbank извлечены:', powerbanksData);
        
        // Если данные все еще в структуре API, извлекаем их
        if (powerbanksData && powerbanksData.success && powerbanksData.data) {
          console.log('Извлекаем данные powerbank из вложенной структуры API');
          powerbanksData = powerbanksData.data;
          console.log('Финальные данные powerbank:', powerbanksData);
        }
        
        // Обновляем данные станции актуальной информацией о портах
        // ВАЖНО: Используем ТОЛЬКО данные из API powerbanks
        if (powerbanksData && powerbanksData.success) {
          // API возвращает: { success, available_powerbanks, count, free_slots, total_slots }
          const availablePowerbanks = powerbanksData.available_powerbanks || [];
          stationDetails.ports = availablePowerbanks;
          
          // Используем ТОЛЬКО актуальные данные из API powerbanks
          stationDetails.freePorts = powerbanksData.free_slots; // Пустые слоты для возврата
          stationDetails.totalPorts = powerbanksData.total_slots; // Всего слотов
          stationDetails.occupiedPorts = powerbanksData.count; // Powerbank'и в станции (можно взять)
          stationDetails.remain_num = powerbanksData.free_slots; // Обновляем remain_num актуальными данными
          
          console.log('Порты станции обновлены актуальными данными:', {
            freePorts: stationDetails.freePorts,
            totalPorts: stationDetails.totalPorts,
            occupiedPorts: stationDetails.occupiedPorts,
            powerbanksCount: availablePowerbanks.length
          });
        } else {
          // Если нет данных о powerbank'ах, используем 0 (безопаснее чем неактуальный remain_num)
          const totalSlots = stationDetails.slots_declared || 20;
          
          stationDetails.freePorts = 0;
          stationDetails.totalPorts = totalSlots;
          stationDetails.occupiedPorts = 0;
          
          console.warn('⚠️ Не удалось получить актуальные данные о портах (admin). Используем заглушки.');
        }
        
        // Обновляем станцию в локальном состоянии
        const stationIndex = this.stations.findIndex(s => (s.station_id || s.id) === stationId);
        if (stationIndex !== -1) {
          this.stations[stationIndex] = { ...this.stations[stationIndex], ...stationDetails };
          console.log('Станция обновлена в локальном состоянии:', this.stations[stationIndex]);
        }
        
        return stationDetails;
      } catch (error) {
        console.error('Ошибка при обновлении данных станции:', error);
        throw error;
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
        // Запрашиваем все заказы с большим лимитом
        const res = await pythonAPI.getOrders({ limit: 10000 });
        const orders = (res && Array.isArray(res.data)) ? res.data : [];
        // Normalize timestamp field for UI that expects created_at
        this.orders = orders.map(o => ({ ...o, created_at: o.created_at || o.timestamp }));
      } catch (err) {
        this.error = 'Failed to fetch orders';
        console.error('Error fetching orders:', err);
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
        console.log('🔍 fetchOrgUnits: Starting fetch with params:', params);
        // Запрашиваем все org units с большим лимитом
        const res = await pythonAPI.getOrgUnits({ ...params, limit: 10000 });
        console.log('🔍 fetchOrgUnits: Raw response:', res);
        
        // Обрабатываем ответ в зависимости от структуры
        let orgUnits = [];
        if (Array.isArray(res)) {
          orgUnits = res;
          console.log('🔍 fetchOrgUnits: Using response as array');
        } else if (res && Array.isArray(res.data)) {
          orgUnits = res.data;
          console.log('🔍 fetchOrgUnits: Using response.data');
        } else if (res && Array.isArray(res.orgUnits)) {
          orgUnits = res.orgUnits;
          console.log('🔍 fetchOrgUnits: Using response.orgUnits');
        } else {
          console.warn('🔍 fetchOrgUnits: Unexpected response structure:', res);
          orgUnits = [];
        }
        
        this.orgUnits = orgUnits;
        console.log('🔍 fetchOrgUnits: Final orgUnits:', this.orgUnits);
        return this.orgUnits;
      } catch (err) {
        console.error('🔍 fetchOrgUnits: Error:', err);
        this.error = 'Failed to fetch org units';
        return [];
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
        // Обновляем данные конкретной станции после принудительного извлечения
        if (data.station_id) {
          await this.refreshStationData(data.station_id);
        } else {
          // Если нет station_id, обновляем все станции
          await this.fetchStations();
        }
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

    // АККУМУЛЯТОРЫ
    async fetchPowerbanks(params = {}) {
      this.isLoading = true;
      try {
        // Запрашиваем все powerbanks с большим лимитом
        const res = await pythonAPI.getPowerbanks({ ...params, limit: 10000 });

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
    async resetPowerbankError(id) {
      try {
        await pythonAPI.resetPowerbankError(id);
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
