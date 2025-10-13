<template>
  <div class="station-card" :class="{ 
    'station-card--favorite': isFavorite,
    'station-card--highlighted': isHighlighted 
  }">
    <div class="station-card__header">
      <div v-if="station.box_id" class="station-card__box-id station-card__box-id--header">
        {{ station.box_id }}
      </div>

      <div class="station-card__status">
        <span
          class="station-card__status-indicator"
          :class="`station-card__status-indicator--${station.status}`"
        ></span>
        <span class="station-card__status-text">{{ getStatusText(station.status) }}</span>
      </div>
    </div>
    
    <div class="station-card__content">

      <p v-if="station.address" class="station-card__address">
        {{ station.address }}
      </p>

      <p v-if="station.description" class="station-card__description">
        {{ station.description }}
      </p>

      <div class="station-card__powerbank-info">
        <div class="station-card__powerbank-item">
          <span class="station-card__powerbank-label">Вернуть:</span>
          <span class="station-card__powerbank-value station-card__powerbank-value--available">{{ availablePorts }}</span>
        </div>
        <div class="station-card__powerbank-item">
          <span class="station-card__powerbank-label">Взять:</span>
          <span class="station-card__powerbank-value station-card__powerbank-value--returnable">{{ returnablePorts }}</span>
        </div>
      </div>
      
      <div v-if="station.lastSeen" class="station-card__last-seen">
        <span class="station-card__last-seen-label">Последний раз видели:</span>
        <span class="station-card__last-seen-time">{{ formatLastSeen(station.lastSeen) }}</span>
      </div>
    </div>
    
    <div class="station-card__actions">
      <BaseButton
        v-if="showTakeBatteryButton && (availablePorts > 0 || station.status === 'active')"
        variant="success"
        size="small"
        @click="$emit('takeBattery', station)"
      >
        Взять аккумулятор
      </BaseButton>
      
      <BaseButton
        v-if="showReturnBatteryButton"
        variant="primary"
        size="small"
        @click="$emit('returnBattery', station)"
      >
        Вернуть аккумулятор
      </BaseButton>

      <BaseButton
        variant="warning"
        size="small"
        @click="$emit('returnWithError', station)"
      >
        Вернуть с ошибкой
      </BaseButton>

      <BaseButton
        v-if="showFavoriteButton"
        :variant="isFavorite ? 'danger' : 'secondary'"
        size="small"
        @click="toggleFavorite"
      >
        {{ isFavorite ? 'Удалить из избранного' : 'Добавить в избранное' }}
      </BaseButton>

      <BaseButton
        v-if="showAdminActions"
        variant="warning"
        size="small"
        @click="$emit('adminClick', station)"
      >
        Управление банками
      </BaseButton>
    </div>
    
    <div v-if="station.distance" class="station-card__distance">
      <span class="station-card__distance-text">{{ formatDistance(station.distance) }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import BaseButton from './BaseButton.vue'

const props = defineProps({
  station: {
    type: Object,
    required: true
  },
  isFavorite: {
    type: Boolean,
    default: false
  },
  isHighlighted: {
    type: Boolean,
    default: false
  },
  showFavoriteButton: {
    type: Boolean,
    default: true
  },
  showTakeBatteryButton: {
    type: Boolean,
    default: true
  },
  showReturnBatteryButton: {
    type: Boolean,
    default: false
  },
  showAdminActions: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['toggleFavorite', 'takeBattery', 'returnBattery', 'returnWithError', 'adminClick'])

const availablePorts = computed(() => {
  return props.station.freePorts || 0
})

const totalPorts = computed(() => {
  return props.station.totalPorts || 0
})

const returnablePorts = computed(() => {
  return props.station.occupiedPorts || 0
})

const getStatusText = (status) => {
  const statusMap = {
    'online': 'Онлайн',
    'offline': 'Офлайн',
    'maintenance': 'Обслуживание',
    'error': 'Ошибка',
    'blocked': 'Заблокирована'
  }
  return statusMap[status] || status
}


const formatLastSeen = (timestamp) => {
  if (!timestamp) return 'Неизвестно'
  
  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / (1000 * 60))
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  
  if (diffMins < 1) return 'Только что'
  if (diffMins < 60) return `${diffMins} мин назад`
  if (diffHours < 24) return `${diffHours} ч назад`
  if (diffDays < 7) return `${diffDays} дн назад`
  
  return date.toLocaleDateString('ru-RU')
}

const formatDistance = (distance) => {
  if (distance < 1000) {
    return `${Math.round(distance)} м`
  } else {
    return `${(distance / 1000).toFixed(1)} км`
  }
}

const toggleFavorite = () => {
  emit('toggleFavorite', props.station)
}
</script>

<style scoped>
.station-card {
  background: var(--background-color);
  border: 2px solid var(--border-color);
  border-radius: 12px;
  padding: 16px;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.station-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
}

.station-card--favorite {
  background: linear-gradient(135deg, var(--background-color) 0%, rgba(255, 193, 7, 0.05) 100%);
}

.station-card--highlighted {
  background: linear-gradient(135deg, var(--background-color) 0%, rgba(255, 193, 7, 0.15) 100%);
  border: 3px solid #ffc107;
  box-shadow: 0 0 0 2px rgba(255, 193, 7, 0.3), 0 8px 25px rgba(255, 193, 7, 0.2);
  animation: highlightPulse 5s ease-in-out infinite;
}

@keyframes highlightPulse {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 0 0 2px rgba(255, 193, 7, 0.3), 0 8px 25px rgba(255, 193, 7, 0.2);
  }
  50% {
    transform: scale(1.02);
    box-shadow: 0 0 0 4px rgba(255, 193, 7, 0.5), 0 12px 30px rgba(255, 193, 7, 0.3);
  }
}


.station-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.station-card__status {
  display: flex;
  align-items: center;
  gap: 6px;
}

.station-card__status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.station-card__status-indicator--online {
  background-color: var(--success-color);
  box-shadow: 0 0 8px var(--success-color);
}

.station-card__status-indicator--offline {
  background-color: var(--text-secondary);
}

.station-card__status-indicator--maintenance {
  background-color: var(--warning-color);
  box-shadow: 0 0 8px var(--warning-color);
}

.station-card__status-indicator--error {
  background-color: var(--danger-color);
  box-shadow: 0 0 8px var(--danger-color);
}

.station-card__status-indicator--blocked {
  background-color: var(--text-secondary);
}

.station-card__status-text {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}


.station-card__content {
  margin-bottom: 16px;
}


.station-card__box-id {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  background-color: var(--background-secondary);
  padding: 4px 8px;
  border-radius: 6px;
  font-family: 'Courier New', monospace;
}

.station-card__box-id--header {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  font-family: 'Courier New', monospace;
  margin-right: 12px;
}

.station-card__address {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0 0 8px 0;
  line-height: 1.4;
}

.station-card__description {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 0 0 12px 0;
  line-height: 1.4;
  opacity: 0.8;
}

.station-card__powerbank-info {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.station-card__powerbank-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.station-card__powerbank-label {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.station-card__powerbank-value {
  font-size: 14px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 12px;
  min-width: 24px;
  text-align: center;
}

.station-card__powerbank-value--available {
  background-color: var(--success-color);
  color: white;
}

.station-card__powerbank-value--returnable {
  background-color: var(--warning-color);
  color: white;
}


.station-card__last-seen {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-bottom: 12px;
}

.station-card__last-seen-label {
  font-size: 11px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.station-card__last-seen-time {
  font-size: 12px;
  color: var(--text-primary);
  font-weight: 500;
}

.station-card__actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.station-card__distance {
  position: absolute;
  top: 12px;
  right: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
  background-color: rgba(0, 0, 0, 0.1);
  padding: 4px 8px;
  border-radius: 12px;
  backdrop-filter: blur(10px);
}

.station-card__distance-icon {
  font-size: 12px;
}

.station-card__distance-text {
  font-size: 11px;
  color: var(--text-secondary);
  font-weight: 500;
}

/* Mobile optimizations */
@media (max-width: 768px) {
  .station-card {
    padding: 12px;
  }


  .station-card__box-id--header {
    font-size: 14px;
    margin-right: 8px;
  }


  .station-card__powerbank-info {
    flex-direction: column;
    gap: 8px;
  }

  .station-card__powerbank-item {
    gap: 8px;
  }

  .station-card__actions {
    flex-direction: column;
  }

  .station-card__actions .base-button {
    width: 100%;
  }
}

/* Touch device optimizations */
@media (hover: none) and (pointer: coarse) {
  .station-card:hover {
    transform: none;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  }
  
  .station-card:active {
    transform: scale(0.98);
  }
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  .station-card {
    background: var(--background-dark);
    border-color: var(--border-dark);
  }
  
}
</style>
