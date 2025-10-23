import { defineStore } from 'pinia';
import { pythonAPI } from '../api/pythonApi';

export const useStationsStore = defineStore('stations', {
  state: () => ({
    stations: [],
    favoriteStations: [],
    loading: false,
    error: null,
  }),
  actions: {
    async fetchStations() {
      this.loading = true;
      try {
        const stations = await pythonAPI.getStations();
        this.stations = Array.isArray(stations) ? stations : [];
      } catch (err) {
        this.error = 'Failed to fetch stations';
      } finally {
        this.loading = false;
      }
    },
    async fetchFavoriteStations(userId) {
      try {
        if (!userId) {
          // Если нет userId, используем только localStorage
          const ids = JSON.parse(localStorage.getItem('favoriteStationIds') || '[]');
          if (!Array.isArray(ids) || ids.length === 0) {
            this.favoriteStations = [];
            return;
          }
          
          const allStations = await pythonAPI.getStations();
          // Фильтруем и загружаем полные данные для каждой станции
          const favoriteStations = [];
          for (const stationId of ids) {
            try {
              const fullStationData = await pythonAPI.getStation(stationId);
              if (fullStationData) {
                favoriteStations.push(fullStationData);
              }
            } catch (error) {
              console.error('Ошибка загрузки станции:', error);
              // Добавляем базовую информацию из общего списка
              const basicStation = allStations.find(s => (s.station_id || s.id) === stationId);
              if (basicStation) {
                favoriteStations.push(basicStation);
              }
            }
          }
          this.favoriteStations = favoriteStations;
          return;
        }

        // Сначала пытаемся получить с сервера
        try {
          const response = await pythonAPI.getUserFavoriteStations(userId);
          console.log('Ответ API избранного:', response);
          console.log('Тип ответа:', typeof response);
          console.log('response.data:', response.data);
          console.log('response.success:', response.success);
          
          // Проверяем структуру ответа
          let serverFavorites;
          if (response && response.success && response.data) {
            serverFavorites = response.data;
            console.log('Используем response.data');
          } else if (Array.isArray(response)) {
            serverFavorites = response;
            console.log('Используем response как массив');
          } else {
            serverFavorites = [];
            console.log('Пустой массив, так как структура неожиданная');
          }
          
          console.log('Данные избранного:', serverFavorites);
          
          // Преобразуем данные избранного в формат станций
          const transformedFavorites = await Promise.all(serverFavorites.map(async (fav) => {
            try {
              // Загружаем полные данные станции для получения информации о портах
              const fullStationData = await pythonAPI.getStation(fav.station_id);
              console.log('Полные данные станции для избранного:', fullStationData);
              
              // Извлекаем данные из ответа API
              let stationDetails = fullStationData?.data || fullStationData;
              if (stationDetails && stationDetails.success && stationDetails.data) {
                stationDetails = stationDetails.data;
              }
              
              // Получаем актуальные данные о powerbank'ах
              let powerbanksData = [];
              try {
                const powerbanksResponse = await pythonAPI.getStationPowerbanks(fav.station_id);
                console.log('Ответ API для powerbank избранного:', powerbanksResponse);
                
                // Извлекаем данные о powerbank'ах из ответа API
                powerbanksData = powerbanksResponse?.data || powerbanksResponse;
                if (powerbanksData && powerbanksData.success && powerbanksData.data) {
                  powerbanksData = powerbanksData.data;
                }
              } catch (powerbankError) {
                console.error('Ошибка загрузки данных powerbank для избранного:', powerbankError);
              }
              
              // Обновляем данные станции актуальной информацией о портах
              if (powerbanksData && Array.isArray(powerbanksData)) {
                stationDetails.ports = powerbanksData;
                // Вычисляем числовые свойства на основе данных с сервера
                stationDetails.freePorts = powerbanksData.filter(port => port.status === 'free').length;
                stationDetails.totalPorts = powerbanksData.length;
                stationDetails.occupiedPorts = powerbanksData.filter(port => port.status === 'occupied').length;
                console.log('Порты станции избранного обновлены актуальными данными:', stationDetails.ports);
              } else {
                // Если нет данных о powerbank'ах, создаем числовые свойства на основе remain_num
                const totalSlots = stationDetails.slots_declared || 20;
                const freeSlots = stationDetails.remain_num || 0;
                const occupiedSlots = totalSlots - freeSlots;
                
                stationDetails.freePorts = freeSlots;
                stationDetails.totalPorts = totalSlots;
                stationDetails.occupiedPorts = occupiedSlots;
                
                console.log('Созданы числовые свойства портов для избранного:', {
                  freePorts: stationDetails.freePorts,
                  totalPorts: stationDetails.totalPorts,
                  occupiedPorts: stationDetails.occupiedPorts
                });
              }
              
              return {
                station_id: fav.station_id,
                id: fav.station_id,
                box_id: fav.station_box_id,
                code: fav.station_box_id,
                name: fav.station_box_id,
                status: fav.station_status || stationDetails?.status || 'active',
                address: fav.station_address || stationDetails?.address || null,
                ports: stationDetails?.ports || [], // Используем актуальные данные о портах
                remain_num: stationDetails?.remain_num || 0,
                slots_declared: stationDetails?.slots_declared || 0,
                freePorts: stationDetails?.freePorts || stationDetails?.remain_num || 0,
                totalPorts: stationDetails?.totalPorts || stationDetails?.slots_declared || 0,
                occupiedPorts: stationDetails?.occupiedPorts || ((stationDetails?.slots_declared || 0) - (stationDetails?.remain_num || 0)),
                lastSeen: stationDetails?.last_seen || stationDetails?.last_seen_at || fav.created_at,
                last_seen: stationDetails?.last_seen || stationDetails?.last_seen_at,
                // Сохраняем оригинальные данные избранного
                favorite_id: fav.id,
                favorite_created_at: fav.created_at
              };
            } catch (error) {
              console.error('Ошибка загрузки полных данных станции:', error);
              // Возвращаем базовые данные без портов
              return {
                station_id: fav.station_id,
                id: fav.station_id,
                box_id: fav.station_box_id,
                code: fav.station_box_id,
                name: fav.station_box_id,
                status: fav.station_status || 'active',
                address: fav.station_address || null,
                ports: [],
                remain_num: 0,
                slots_declared: 0,
                freePorts: 0,
                totalPorts: 0,
                occupiedPorts: 0,
                lastSeen: fav.created_at, // fallback если нет данных станции
                last_seen: null,
                favorite_id: fav.id,
                favorite_created_at: fav.created_at
              };
            }
          }));
          
          console.log('Преобразованные данные избранного:', transformedFavorites);
          this.favoriteStations = transformedFavorites || [];
          // Кэшируем локально для быстрого доступа
          this._cacheFavoritesLocally(transformedFavorites || []);
        } catch (serverError) {
          // Если сервер недоступен, используем локальный кэш
          const ids = JSON.parse(localStorage.getItem('favoriteStationIds') || '[]');
          if (!Array.isArray(ids) || ids.length === 0) {
            this.favoriteStations = [];
            return;
          }
          
          const allStations = await pythonAPI.getStations();
          // Загружаем полные данные для каждой станции
          const favoriteStations = [];
          for (const stationId of ids) {
            try {
              const fullStationData = await pythonAPI.getStation(stationId);
              if (fullStationData) {
                // Извлекаем данные из ответа API
                let stationDetails = fullStationData?.data || fullStationData;
                if (stationDetails && stationDetails.success && stationDetails.data) {
                  stationDetails = stationDetails.data;
                }
                
                // Получаем актуальные данные о powerbank'ах
                let powerbanksData = [];
                try {
                  const powerbanksResponse = await pythonAPI.getStationPowerbanks(stationId);
                  powerbanksData = powerbanksResponse?.data || powerbanksResponse;
                  if (powerbanksData && powerbanksData.success && powerbanksData.data) {
                    powerbanksData = powerbanksData.data;
                  }
                } catch (powerbankError) {
                  console.error('Ошибка загрузки данных powerbank для fallback:', powerbankError);
                }
                
                // Обновляем данные станции актуальной информацией о портах
                if (powerbanksData && Array.isArray(powerbanksData)) {
                  stationDetails.ports = powerbanksData;
                  // Вычисляем числовые свойства на основе данных с сервера
                  stationDetails.freePorts = powerbanksData.filter(port => port.status === 'free').length;
                  stationDetails.totalPorts = powerbanksData.length;
                  stationDetails.occupiedPorts = powerbanksData.filter(port => port.status === 'occupied').length;
                } else {
                  // Если нет данных о powerbank'ах, создаем числовые свойства на основе remain_num
                  const totalSlots = stationDetails.slots_declared || 20;
                  const freeSlots = stationDetails.remain_num || 0;
                  const occupiedSlots = totalSlots - freeSlots;
                  
                  stationDetails.freePorts = freeSlots;
                  stationDetails.totalPorts = totalSlots;
                  stationDetails.occupiedPorts = occupiedSlots;
                }
                
                favoriteStations.push(stationDetails);
              }
            } catch (error) {
              console.error('Ошибка загрузки станции:', error);
              // Добавляем базовую информацию из общего списка
              const basicStation = allStations.find(s => (s.station_id || s.id) === stationId);
              if (basicStation) {
                favoriteStations.push(basicStation);
              }
            }
          }
          this.favoriteStations = favoriteStations;
        }
      } catch (err) {
        // Error handled silently
      }
    },

    // Вспомогательный метод для кэширования избранных станций локально
    _cacheFavoritesLocally(favorites) {
      const ids = favorites.map(f => f.station_id || f.id);
      localStorage.setItem('favoriteStationIds', JSON.stringify(ids));
    },
    async addFavorite(userId, stationId) {
      try {
        if (!userId) {
          // Если нет userId, используем только localStorage
          const ids = JSON.parse(localStorage.getItem('favoriteStationIds') || '[]');
          if (!ids.includes(stationId)) {
            ids.push(stationId);
            localStorage.setItem('favoriteStationIds', JSON.stringify(ids));
          }
          await this.fetchFavoriteStations(userId);
          return;
        }

        // Сначала добавляем на сервер
        try {
          console.log('Добавляем в избранное:', { user_id: userId, station_id: stationId });
          const addResult = await pythonAPI.addFavoriteStation({ user_id: userId, station_id: stationId });
          console.log('Результат добавления:', addResult);
          // Обновляем локальный кэш
          await this._updateLocalCacheAfterServerOperation(userId);
        } catch (serverError) {
          console.error('Ошибка при добавлении в избранное:', serverError);
          // Если сервер недоступен, добавляем только локально
          const ids = JSON.parse(localStorage.getItem('favoriteStationIds') || '[]');
          if (!ids.includes(stationId)) {
            ids.push(stationId);
            localStorage.setItem('favoriteStationIds', JSON.stringify(ids));
          }
        }

        await this.fetchFavoriteStations(userId);
      } catch (err) {
        // Error handled silently
      }
    },
    async removeFavorite(userId, stationId) {
      try {
        if (!userId) {
          // Если нет userId, используем только localStorage
          const ids = JSON.parse(localStorage.getItem('favoriteStationIds') || '[]');
          const filteredIds = ids.filter(id => id !== stationId);
          localStorage.setItem('favoriteStationIds', JSON.stringify(filteredIds));
          await this.fetchFavoriteStations(userId);
          return;
        }

        // Находим favorite_id для удаления
        const favorite = this.favoriteStations.find(f => (f.station_id || f.id) === stationId);
        if (!favorite) {
          // Если не найдено в избранном, удаляем только локально
          const ids = JSON.parse(localStorage.getItem('favoriteStationIds') || '[]');
          const filteredIds = ids.filter(id => id !== stationId);
          localStorage.setItem('favoriteStationIds', JSON.stringify(filteredIds));
          await this.fetchFavoriteStations(userId);
          return;
        }

        // Сначала удаляем с сервера
        try {
          await pythonAPI.removeFavoriteStation(favorite.favorite_id || favorite.id);
          // Обновляем локальный кэш
          await this._updateLocalCacheAfterServerOperation(userId);
        } catch (serverError) {
          // Если сервер недоступен, удаляем только локально
          const ids = JSON.parse(localStorage.getItem('favoriteStationIds') || '[]');
          const filteredIds = ids.filter(id => id !== stationId);
          localStorage.setItem('favoriteStationIds', JSON.stringify(filteredIds));
        }

        await this.fetchFavoriteStations(userId);
      } catch (err) {
        // Error handled silently
      }
    },

    // Вспомогательный метод для обновления локального кэша после операций с сервером
    async _updateLocalCacheAfterServerOperation(userId) {
      try {
        const response = await pythonAPI.getUserFavoriteStations(userId);
        const serverFavorites = response.data || response;
        
        // Преобразуем данные избранного в формат станций
        const transformedFavorites = serverFavorites.map(fav => ({
          station_id: fav.station_id,
          id: fav.station_id,
          box_id: fav.station_box_id,
          code: fav.station_box_id,
          name: fav.station_box_id,
          status: fav.station_status || 'active', // Устанавливаем статус по умолчанию
          address: fav.station_address || null,
          ports: [],
          remain_num: 0,
          slots_declared: 0,
          freePorts: 0,
          totalPorts: 0,
          occupiedPorts: 0,
          lastSeen: fav.created_at, // fallback
          last_seen: null,
          favorite_id: fav.id,
          favorite_created_at: fav.created_at
        }));
        
        this._cacheFavoritesLocally(transformedFavorites || []);
      } catch (err) {
        // Error handled silently
      }
    },

    // Обновление данных конкретной станции с актуальной информацией
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
        if (powerbanksData && Array.isArray(powerbanksData)) {
          stationDetails.ports = powerbanksData;
          // Вычисляем числовые свойства на основе данных с сервера
          stationDetails.freePorts = powerbanksData.filter(port => port.status === 'free').length;
          stationDetails.totalPorts = powerbanksData.length;
          stationDetails.occupiedPorts = powerbanksData.filter(port => port.status === 'occupied').length;
          console.log('Порты станции обновлены актуальными данными:', stationDetails.ports);
        } else {
          // Если нет данных о powerbank'ах, создаем числовые свойства на основе remain_num
          const totalSlots = stationDetails.slots_declared || 20;
          const freeSlots = stationDetails.remain_num || 0;
          const occupiedSlots = totalSlots - freeSlots;
          
          stationDetails.freePorts = freeSlots;
          stationDetails.totalPorts = totalSlots;
          stationDetails.occupiedPorts = occupiedSlots;
          
          console.log('Созданы числовые свойства портов:', {
            freePorts: stationDetails.freePorts,
            totalPorts: stationDetails.totalPorts,
            occupiedPorts: stationDetails.occupiedPorts
          });
        }
        
        return stationDetails;
      } catch (error) {
        console.error('Ошибка при обновлении данных станции:', error);
        throw error;
      }
    },

    // Перемещение станции в начало списка избранных
    moveStationToTop(stationId) {
      const stationIndex = this.favoriteStations.findIndex(station => 
        (station.station_id || station.id) === stationId
      );
      
      if (stationIndex > 0) {
        // Удаляем станцию из текущей позиции
        const station = this.favoriteStations.splice(stationIndex, 1)[0];
        // Добавляем в начало списка
        this.favoriteStations.unshift(station);
        console.log('Станция перемещена в начало списка:', stationId);
      }
    },

    // Поиск станций по различным критериям
    async searchStations(searchQuery) {
      if (!searchQuery || searchQuery.trim().length === 0) {
        return [];
      }

      try {
        // Сначала ищем среди избранных станций (там есть адреса)
        const favoriteResults = this.favoriteStations.filter(station => {
          const normalizedQuery = searchQuery.trim().toLowerCase();
          
          // Поиск по адресу в избранных станциях
          const address = station.address || '';
          if (address && address.toLowerCase().includes(normalizedQuery)) {
            return true;
          }
          
          // Поиск по box_id
          const boxId = station.box_id || '';
          if (boxId.toLowerCase().includes(normalizedQuery)) {
            return true;
          }
          
          return false;
        });
        
        if (favoriteResults.length > 0) {
          return favoriteResults;
        }
        
        // Если в избранном не найдено, ищем среди всех станций
        const allStations = await pythonAPI.getStations();
        const stationsArray = Array.isArray(allStations) ? allStations : 
                            (allStations?.data || allStations?.stations || []);
        
        // Нормализуем поисковый запрос
        const normalizedQuery = searchQuery.trim().toLowerCase();
        
        // Фильтруем станции по различным критериям
        const searchResults = stationsArray.filter(station => {
          // Поиск по box_id
          const boxId = station.box_id || station.station_box_id || '';
          if (boxId.toLowerCase().includes(normalizedQuery)) {
            return true;
          }
          
          // Поиск по адресу станции (основной приоритет для поиска)
          const address = station.address || station.station_address || '';
          if (address && address.toLowerCase().includes(normalizedQuery)) {
            return true;
          }
          
          // Поиск по названию станции
          const name = station.name || station.station_name || '';
          if (name.toLowerCase().includes(normalizedQuery)) {
            return true;
          }
          
          // Поиск по ID станции
          const stationId = station.station_id || station.id;
          if (stationId && String(stationId).includes(normalizedQuery)) {
            return true;
          }
          
          // Поиск по org_unit_name (название организации)
          const orgUnitName = station.org_unit_name || '';
          if (orgUnitName.toLowerCase().includes(normalizedQuery)) {
            return true;
          }
          
          // Поиск по ICCID (если есть)
          const iccid = station.iccid || '';
          if (iccid.toLowerCase().includes(normalizedQuery)) {
            return true;
          }
          
          return false;
        });
        
        return searchResults;
        
      } catch (error) {
        console.error('❌ Ошибка при поиске станций:', error);
        return [];
      }
    },
  },
});
