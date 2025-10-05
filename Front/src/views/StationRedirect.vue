<template>
  <div class="station-redirect">
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>Загрузка информации о станции...</p>
    </div>
    
    <div v-else-if="error" class="error">
      <div class="error-icon">⚠</div>
      <h3>Станция не найдена</h3>
      <p>{{ error }}</p>
      <button @click="goToDashboard" class="back-btn">Вернуться на главную</button>
    </div>
    
    <div v-else-if="stationData" class="station-info">
      <div class="station-header">
        <h2>Информация о станции</h2>
        <p>Вы перешли по ссылке станции</p>
      </div>
      
      <!-- Используем компонент StationCard -->
      <StationCard
        :station="normalizedStationData"
        :isFavorite="isStationFavorite"
        :isHighlighted="true"
        :showFavoriteButton="true"
        :showTakeBatteryButton="true"
        :showReturnBatteryButton="canReturn"
        :showAdminActions="isAdmin"
        @toggleFavorite="toggleFavorite"
        @takeBattery="handleTakeBattery"
        @returnBattery="handleReturnBattery"
        @adminClick="handleAdminClick"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { pythonAPI } from '../api/pythonApi';
import StationCard from '../components/StationCard.vue';
import { useAuthStore } from '../stores/auth';
import { useStationsStore } from '../stores/stations';

const route = useRoute();
const router = useRouter();

// Stores
const authStore = useAuthStore();
const stationsStore = useStationsStore();

const stationName = decodeURIComponent(route.params.stationName);
const stationData = ref(null);
const loading = ref(true);
const error = ref('');
const userPowerbanks = ref([]);

// Computed properties
const user = computed(() => authStore.user);
const isAdmin = computed(() => user.value?.role?.includes('admin') || false);

// Нормализуем данные станции для компонента StationCard
const normalizedStationData = computed(() => {
  if (!stationData.value) return null;
  
  return {
    ...stationData.value,
    // Маппинг полей для совместимости с StationCard
    freePorts: stationData.value.available_slots || 0,
    totalPorts: stationData.value.total_slots || 0,
    occupiedPorts: (stationData.value.total_slots || 0) - (stationData.value.available_slots || 0),
    lastSeen: stationData.value.last_seen || stationData.value.lastSeen
  };
});

const isStationFavorite = computed(() => {
  if (!stationData.value || !user.value) return false;
  const stationId = stationData.value.station_id || stationData.value.id;
  return stationsStore.favoriteStations.some(fav => 
    (fav.station_id || fav.id) === stationId
  );
});

const canReturn = computed(() => {
  return userPowerbanks.value && userPowerbanks.value.length > 0;
});

const getStatusText = (status) => {
  const statusMap = {
    'active': 'Активна',
    'inactive': 'Неактивна',
    'maintenance': 'Обслуживание',
    'error': 'Ошибка',
    'pending': 'Ожидает активации'
  };
  return statusMap[status] || 'Неизвестно';
};

const loadStationData = async () => {
  if (!stationName) {
    error.value = 'Имя станции не указано';
    loading.value = false;
    return;
  }
  
  try {
    // Загружаем все станции и ищем по имени
    const stationsResponse = await pythonAPI.getStations();
    console.log('Stations response:', stationsResponse);
    
    // Проверяем, что ответ содержит массив станций
    const stations = Array.isArray(stationsResponse) ? stationsResponse : 
                    stationsResponse.stations || stationsResponse.data || [];
    console.log('Stations array:', stations);
    
    const station = stations.find(s => 
      s.name === stationName || 
      s.station_name === stationName || 
      s.box_id === stationName ||
      s.station_id === stationName ||
      `Станция ${s.station_id || s.id}` === stationName
    );
    
    if (!station) {
      error.value = `Не удалось найти станцию с именем "${stationName}"`;
      loading.value = false;
      return;
    }
    
    stationData.value = station;
    
    // Загружаем информацию о пауэрбанках пользователя
    await loadUserPowerbanks();
    
    // Загружаем избранные станции пользователя
    if (user.value?.user_id) {
      await stationsStore.loadFavoriteStations(user.value.user_id);
    }
  } catch (error) {
    console.error('Ошибка загрузки станции:', error);
    error.value = 'Не удалось найти станцию с указанным именем';
  } finally {
    loading.value = false;
  }
};

const loadUserPowerbanks = async () => {
  try {
    const response = await pythonAPI.getUserPowerbanks();
    userPowerbanks.value = response.powerbanks || [];
  } catch (error) {
    console.error('Ошибка загрузки пауэрбанков пользователя:', error);
    userPowerbanks.value = [];
  }
};

// Обработчики событий для StationCard
const handleTakeBattery = async (station) => {
  try {
    const stationId = station.station_id || station.id;
    const response = await pythonAPI.borrowPowerbank(stationId);
    alert('Пауэрбанк успешно взят!');
    await loadStationData(); // Обновляем данные
  } catch (error) {
    console.error('Ошибка взятия пауэрбанка:', error);
    alert('Ошибка при взятии пауэрбанка: ' + (error.message || 'Неизвестная ошибка'));
  }
};

const handleReturnBattery = async (station) => {
  if (!canReturn.value) return;
  
  try {
    const stationId = station.station_id || station.id;
    const powerbankId = userPowerbanks.value[0].id; // Берем первый доступный
    const response = await pythonAPI.returnPowerbank(stationId, powerbankId);
    alert('Пауэрбанк успешно возвращен!');
    await loadStationData(); // Обновляем данные
  } catch (error) {
    console.error('Ошибка возврата пауэрбанка:', error);
    alert('Ошибка при возврате пауэрбанка: ' + (error.message || 'Неизвестная ошибка'));
  }
};

const toggleFavorite = async (station) => {
  try {
    const stationId = station.station_id || station.id;
    
    if (isStationFavorite.value) {
      console.log('Удаляем из избранного');
      await stationsStore.removeFavorite(user.value?.user_id, stationId);
    } else {
      console.log('Добавляем в избранное');
      await stationsStore.addFavorite(user.value?.user_id, stationId);
    }
    
    // Обновляем данные станций
    await stationsStore.loadFavoriteStations(user.value?.user_id);
  } catch (err) {
    console.error('Ошибка в toggleFavorite:', err);
  }
};

const handleAdminClick = (station) => {
  const stationId = station.station_id || station.id;
  router.push(`/address/${stationId}`);
};

const goToDashboard = () => {
  router.push('/dashboard');
};

onMounted(() => {
  loadStationData();
});
</script>

<style scoped>
.station-redirect {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem;
  background-color: var(--background-color);
  color: var(--text-primary);
}

.station-header {
  text-align: center;
  margin-bottom: 2rem;
}

.station-header h2 {
  margin-bottom: 0.5rem;
  color: var(--text-primary);
}

.station-header p {
  color: var(--text-secondary);
}

.loading {
  text-align: center;
  padding: 3rem;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #e5e7eb;
  border-top: 4px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error {
  text-align: center;
  padding: 3rem;
  background-color: var(--bg-secondary);
  border-radius: 12px;
}

.error-icon {
  font-size: 3rem;
  color: #ef4444;
  margin-bottom: 1rem;
}

.error h3 {
  margin-bottom: 1rem;
  color: var(--text-primary);
}

.error p {
  margin-bottom: 2rem;
  color: var(--text-secondary);
}

.back-btn {
  background-color: #3b82f6;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-size: 1rem;
  cursor: pointer;
  transition: background-color 0.2s;
}

.back-btn:hover {
  background-color: #2563eb;
}

@media (max-width: 768px) {
  .station-redirect {
    padding: 1rem;
  }
}
</style>
