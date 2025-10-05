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
      
      <div class="station-card">
        <div class="station-details">
          <h3>{{ stationData.name || stationData.station_name || stationData.box_id || `Станция ${stationData.station_id || stationData.id}` }}</h3>
          <div class="station-meta">
            <div class="meta-item">
              <span class="meta-label">ID станции:</span>
              <span class="meta-value">{{ stationData.station_id || stationData.id }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">Статус:</span>
              <span class="meta-value status" :class="stationData.status">
                {{ getStatusText(stationData.status) }}
              </span>
            </div>
            <div class="meta-item">
              <span class="meta-label">Адрес:</span>
              <span class="meta-value">{{ stationData.address || 'Не указан' }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">Доступные слоты:</span>
              <span class="meta-value">{{ stationData.available_slots || 0 }} / {{ stationData.total_slots || 0 }}</span>
            </div>
          </div>
        </div>
        
        <div class="station-actions">
          <button @click="borrowPowerbank" class="action-btn primary" :disabled="!canBorrow">
            Взять пауэрбанк
          </button>
          <button @click="returnPowerbank" class="action-btn secondary" :disabled="!canReturn">
            Вернуть пауэрбанк
          </button>
          <button @click="viewStationDetails" class="action-btn tertiary">
            Подробнее о станции
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { pythonAPI } from '../api/pythonApi';

const route = useRoute();
const router = useRouter();

const stationName = decodeURIComponent(route.params.stationId);
const stationData = ref(null);
const loading = ref(true);
const error = ref('');
const userPowerbanks = ref([]);

const canBorrow = computed(() => {
  return stationData.value && stationData.value.available_slots > 0;
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
    const station = stationsResponse.find(s => 
      s.name === stationName || 
      s.station_name === stationName || 
      s.box_id === stationName ||
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

const borrowPowerbank = async () => {
  if (!canBorrow.value) return;
  
  try {
    const stationId = stationData.value.station_id || stationData.value.id;
    const response = await pythonAPI.borrowPowerbank(stationId);
    alert('Пауэрбанк успешно взят!');
    await loadStationData(); // Обновляем данные
  } catch (error) {
    console.error('Ошибка взятия пауэрбанка:', error);
    alert('Ошибка при взятии пауэрбанка: ' + (error.message || 'Неизвестная ошибка'));
  }
};

const returnPowerbank = async () => {
  if (!canReturn.value) return;
  
  try {
    const stationId = stationData.value.station_id || stationData.value.id;
    const powerbankId = userPowerbanks.value[0].id; // Берем первый доступный
    const response = await pythonAPI.returnPowerbank(stationId, powerbankId);
    alert('Пауэрбанк успешно возвращен!');
    await loadStationData(); // Обновляем данные
  } catch (error) {
    console.error('Ошибка возврата пауэрбанка:', error);
    alert('Ошибка при возврате пауэрбанка: ' + (error.message || 'Неизвестная ошибка'));
  }
};

const viewStationDetails = () => {
  const stationId = stationData.value.station_id || stationData.value.id;
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

.station-card {
  background-color: var(--bg-secondary);
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.station-details h3 {
  margin-bottom: 1.5rem;
  color: var(--text-primary);
  font-size: 1.5rem;
}

.station-meta {
  display: grid;
  gap: 1rem;
  margin-bottom: 2rem;
}

.meta-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  background-color: white;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.meta-label {
  font-weight: 500;
  color: var(--text-secondary);
}

.meta-value {
  font-weight: 600;
  color: var(--text-primary);
}

.status.active {
  color: #10b981;
}

.status.inactive {
  color: #6b7280;
}

.status.maintenance {
  color: #f59e0b;
}

.status.error {
  color: #ef4444;
}

.status.pending {
  color: #8b5cf6;
}

.station-actions {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.action-btn {
  flex: 1;
  min-width: 150px;
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn.primary {
  background-color: #3b82f6;
  color: white;
}

.action-btn.primary:hover:not(:disabled) {
  background-color: #2563eb;
}

.action-btn.secondary {
  background-color: #10b981;
  color: white;
}

.action-btn.secondary:hover:not(:disabled) {
  background-color: #059669;
}

.action-btn.tertiary {
  background-color: #6b7280;
  color: white;
}

.action-btn.tertiary:hover:not(:disabled) {
  background-color: #4b5563;
}

.action-btn:disabled {
  background-color: #d1d5db;
  color: #9ca3af;
  cursor: not-allowed;
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
  
  .station-card {
    padding: 1.5rem;
  }
  
  .station-actions {
    flex-direction: column;
  }
  
  .action-btn {
    min-width: auto;
  }
}
</style>
