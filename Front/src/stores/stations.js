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
              // ОПТИМИЗАЦИЯ: Загружаем ТОЛЬКО актуальные данные о powerbank'ах
              // API getStationPowerbanks возвращает всё необходимое: count, free_slots, total_slots
              let powerbanksData = null;
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
              
              // Формируем объект станции из данных API powerbanks и user_favorites
              if (powerbanksData && powerbanksData.success) {
                // API возвращает: { success, available_powerbanks, count, free_slots, total_slots, free_slots_for_return, total_powerbanks_count, healthy_powerbanks_count, broken_powerbanks_count }
                const availablePowerbanks = powerbanksData.available_powerbanks || [];
                
                // Определяем total_powerbanks_count с fallback
                const totalPowerbanksCount = powerbanksData.total_powerbanks_count !== undefined 
                  ? powerbanksData.total_powerbanks_count 
                  : powerbanksData.count; // Fallback на count
                
                const freeSlots = powerbanksData.free_slots_for_return !== undefined 
                  ? powerbanksData.free_slots_for_return 
                  : (powerbanksData.total_slots - totalPowerbanksCount); // Fallback расчет
                
                console.log('Порты станции избранного обновлены актуальными данными:', {
                  totalSlots: powerbanksData.total_slots,
                  freeSlots: freeSlots,
                  totalPowerbanks: totalPowerbanksCount,
                  healthyPowerbanks: powerbanksData.healthy_powerbanks_count || 0,
                  brokenPowerbanks: powerbanksData.broken_powerbanks_count || 0,
                  calculation: `${powerbanksData.total_slots} - ${totalPowerbanksCount} = ${freeSlots}`
                });
                
                return {
                  station_id: fav.station_id,
                  id: fav.station_id,
                  box_id: fav.station_box_id,
                  code: fav.station_box_id,
                  name: fav.station_box_id,
                  status: fav.station_status || 'active',
                  address: fav.station_address || null,
                  // Актуальные данные из API powerbanks
                  ports: availablePowerbanks,
                  remain_num: totalPowerbanksCount,  // ВСЕ повербанки
                  slots_declared: fav.station_slots_declared || powerbanksData.total_slots,
                  freePorts: freeSlots,  // Правильный расчет
                  totalPorts: powerbanksData.total_slots,
                  occupiedPorts: totalPowerbanksCount,  // ВСЕ повербанки
                  // Детальная информация
                  total_powerbanks_count: totalPowerbanksCount,
                  healthy_powerbanks_count: powerbanksData.healthy_powerbanks_count || 0,
                  broken_powerbanks_count: powerbanksData.broken_powerbanks_count || 0,
                  // Последний heartbeat из станции
                  lastSeen: fav.station_last_seen || null,
                  last_seen: fav.station_last_seen || null,
                  // Сохраняем оригинальные данные избранного
                  favorite_id: fav.id,
                  favorite_created_at: fav.created_at,
                  // Сохраняем nickname из API
                  nickname: fav.nik || fav.nickname || null,
                  nik: fav.nik || fav.nickname || null
                };
              } else {
                // Fallback если не удалось получить данные powerbanks
                console.warn('⚠️ Не удалось получить актуальные данные о портах для избранного.');
                
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
                  slots_declared: fav.station_slots_declared || 0,
                  freePorts: fav.station_slots_declared || 0,
                  totalPorts: fav.station_slots_declared || 0,
                  occupiedPorts: 0,
                  // Последний heartbeat из станции
                  lastSeen: fav.station_last_seen || null,
                  last_seen: fav.station_last_seen || null,
                  favorite_id: fav.id,
                  favorite_created_at: fav.created_at,
                  nickname: fav.nik || fav.nickname || null,
                  nik: fav.nik || fav.nickname || null
                };
              }
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
                slots_declared: fav.station_slots_declared || 0,
                freePorts: fav.station_slots_declared || 0,
                totalPorts: fav.station_slots_declared || 0,
                occupiedPorts: 0,
                // Последний heartbeat из станции
                lastSeen: fav.station_last_seen || null,
                last_seen: fav.station_last_seen || null,
                favorite_id: fav.id,
                favorite_created_at: fav.created_at,
                // Сохраняем nickname из API
                nickname: fav.nik || fav.nickname || null,
                nik: fav.nik || fav.nickname || null
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
          
          // ОПТИМИЗАЦИЯ: Загружаем список станций один раз и используем для базовой информации
          const allStationsResponse = await pythonAPI.getStations();
          const allStations = Array.isArray(allStationsResponse) ? allStationsResponse : 
                            (allStationsResponse?.data || []);
          
          // Загружаем актуальные данные для каждой станции
          const favoriteStations = [];
          for (const stationId of ids) {
            try {
              // Находим базовую информацию в уже загруженном списке
              const basicStation = allStations.find(s => (s.station_id || s.id) === stationId);
              if (!basicStation) {
                console.warn(`Станция ${stationId} не найдена в списке`);
                continue;
              }
              
              // Загружаем ТОЛЬКО актуальные данные о powerbank'ах (единственный запрос)
              let powerbanksData = null;
              try {
                const powerbanksResponse = await pythonAPI.getStationPowerbanks(stationId);
                powerbanksData = powerbanksResponse?.data || powerbanksResponse;
                if (powerbanksData && powerbanksData.success && powerbanksData.data) {
                  powerbanksData = powerbanksData.data;
                }
              } catch (powerbankError) {
                console.error('Ошибка загрузки данных powerbank для fallback:', powerbankError);
              }
              
              // Формируем объект станции
              if (powerbanksData && powerbanksData.success) {
                const availablePowerbanks = powerbanksData.available_powerbanks || [];
                
                favoriteStations.push({
                  ...basicStation,
                  ports: availablePowerbanks,
                  remain_num: powerbanksData.count,
                  freePorts: powerbanksData.total_slots - powerbanksData.count,
                  totalPorts: powerbanksData.total_slots,
                  occupiedPorts: powerbanksData.count
                });
              } else {
                // Fallback на базовую информацию
                const totalSlots = basicStation.slots_declared || 0;
                favoriteStations.push({
                  ...basicStation,
                  ports: [],
                  remain_num: 0,
                  freePorts: totalSlots,
                  totalPorts: totalSlots,
                  occupiedPorts: 0
                });
              }
            } catch (error) {
              console.error('Ошибка загрузки станции:', error);
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
          favorite_created_at: fav.created_at,
          // Сохраняем nickname из API
          nickname: fav.nik || fav.nickname || null,
          nik: fav.nik || fav.nickname || null
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
        // ВАЖНО: Используем ТОЛЬКО данные из API powerbanks
        if (powerbanksData && powerbanksData.success) {
          // Логируем сырые данные из API
          console.log('📦 Сырые данные из API для станции:', {
            station_id: stationDetails.station_id,
            box_id: stationDetails.box_id,
            api_data: {
              total_slots: powerbanksData.total_slots,
              free_slots_for_return: powerbanksData.free_slots_for_return,
              total_powerbanks_count: powerbanksData.total_powerbanks_count,
              healthy_powerbanks_count: powerbanksData.healthy_powerbanks_count,
              broken_powerbanks_count: powerbanksData.broken_powerbanks_count,
              count: powerbanksData.count,
              available_powerbanks_length: (powerbanksData.available_powerbanks || []).length
            }
          });
          
          // API возвращает: { success, available_powerbanks, count, free_slots, total_slots, free_slots_for_return, healthy_powerbanks_count, broken_powerbanks_count }
          const availablePowerbanks = powerbanksData.available_powerbanks || [];
          stationDetails.ports = availablePowerbanks;
          
          // Используем ТОЛЬКО актуальные данные из API powerbanks
          stationDetails.totalPorts = powerbanksData.total_slots; // Всего слотов
          
          // ВАЖНО: Используем free_slots_for_return для правильного расчета свободных слотов
          // free_slots_for_return = total_slots - ВСЕ повербанки (здоровые + сломанные)
          // Сломанные повербанки ТОЖЕ занимают физические слоты!
          
          // Определяем total_powerbanks_count с fallback
          const totalPowerbanksCount = powerbanksData.total_powerbanks_count !== undefined 
            ? powerbanksData.total_powerbanks_count 
            : powerbanksData.count; // Fallback на count
          
          stationDetails.freePorts = powerbanksData.free_slots_for_return !== undefined 
            ? powerbanksData.free_slots_for_return 
            : (powerbanksData.total_slots - totalPowerbanksCount); // Fallback расчет
          
          // Количество повербанков для отображения
          stationDetails.remain_num = totalPowerbanksCount; // Все повербанки
          stationDetails.occupiedPorts = totalPowerbanksCount; // Все повербанки
          
          // Добавляем детальную информацию о повербанках
          stationDetails.total_powerbanks_count = totalPowerbanksCount;
          stationDetails.healthy_powerbanks_count = powerbanksData.healthy_powerbanks_count !== undefined 
            ? powerbanksData.healthy_powerbanks_count 
            : 0;
          stationDetails.broken_powerbanks_count = powerbanksData.broken_powerbanks_count !== undefined 
            ? powerbanksData.broken_powerbanks_count 
            : 0;
          
          console.log('Порты станции обновлены актуальными данными:', {
            totalSlots: stationDetails.totalPorts,
            freeSlots: stationDetails.freePorts,
            totalPowerbanks: stationDetails.total_powerbanks_count,
            healthyPowerbanks: stationDetails.healthy_powerbanks_count,
            brokenPowerbanks: stationDetails.broken_powerbanks_count,
            calculation: `${stationDetails.totalPorts} - ${stationDetails.total_powerbanks_count} = ${stationDetails.freePorts}`
          });
        } else {
          // Если нет данных о powerbank'ах, используем 0 (безопаснее чем неактуальный remain_num)
          const totalSlots = stationDetails.slots_declared || 20;
          
          stationDetails.totalPorts = totalSlots;
          stationDetails.remain_num = 0; // Количество powerbank'ов неизвестно
          stationDetails.freePorts = totalSlots; // Считаем все слоты свободными
          stationDetails.occupiedPorts = 0;
          
          console.warn('⚠️ Не удалось получить актуальные данные о портах. Используем заглушки.');
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
        // Сначала ищем среди избранных станций (там есть адреса и ники)
        const favoriteResults = this.favoriteStations.filter(station => {
          const normalizedQuery = searchQuery.trim().toLowerCase();
          
          // Поиск по нику (приоритетный поиск)
          const nickname = station.nickname || station.nik || '';
          if (nickname && nickname.toLowerCase().includes(normalizedQuery)) {
            return true;
          }
          
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

    // Установка nickname для станции в избранном
    async setStationNickname(favoriteId, userId, stationId, nickname) {
      try {
        console.log('Устанавливаем nickname:', { favoriteId, userId, stationId, nickname });
        
        // Отправляем запрос на сервер
        const result = await pythonAPI.setStationNickname(favoriteId, {
          user_id: userId,
          station_id: stationId,
          nik: nickname
        });
        
        console.log('Результат установки nickname:', result);
        
        // Обновляем локальные данные
        const station = this.favoriteStations.find(s => s.favorite_id === favoriteId);
        if (station) {
          station.nickname = nickname;
        }
        
        return result;
      } catch (error) {
        console.error('Ошибка при установке nickname:', error);
        throw error;
      }
    },

    // Удаление nickname для станции в избранном
    async deleteStationNickname(favoriteId) {
      try {
        console.log('Удаляем nickname для favorite_id:', favoriteId);
        
        // Отправляем запрос на сервер
        const result = await pythonAPI.deleteStationNickname(favoriteId);
        
        console.log('Результат удаления nickname:', result);
        
        // Обновляем локальные данные
        const station = this.favoriteStations.find(s => s.favorite_id === favoriteId);
        if (station) {
          station.nickname = null;
        }
        
        return result;
      } catch (error) {
        console.error('Ошибка при удалении nickname:', error);
        throw error;
      }
    },
  },
});
