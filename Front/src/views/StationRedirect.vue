<template>
  <div class="station-redirect">
    <div class="loading">
      <div class="spinner"></div>
      <p>Перенаправление на станцию...</p>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';

const route = useRoute();
const router = useRouter();

// Получаем имя станции из параметров URL
const stationName = decodeURIComponent(route.params.stationName);

onMounted(() => {
  // Сразу перенаправляем на Dashboard с параметром stationName
  console.log('Redirecting to dashboard with stationName:', stationName);
  router.replace(`/dashboard?stationName=${encodeURIComponent(stationName)}`);
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
