<template>
  <div class="station-card" :class="{ 
    'station-card--favorite': isFavorite,
    'station-card--highlighted': isHighlighted,
    'station-card--collapsed': !isExpanded
  }" @click="handleCardClick">
    <div class="station-card__header">
      <div v-if="station.box_id" class="station-card__box-id station-card__box-id--header">
        {{ station.box_id }}
      </div>

      <div class="station-card__header-right">
        <div class="station-card__status">
          <span
            class="station-card__status-indicator"
            :class="`station-card__status-indicator--${station.status}`"
          ></span>
          <span class="station-card__status-text">{{ getStatusText(station.status) }}</span>
        </div>
        <div class="station-card__expand-icon" :class="{ 'station-card__expand-icon--expanded': isExpanded }">
          ▼
        </div>
      </div>
    </div>
    
    <div class="station-card__content" v-if="isExpanded">

      <p v-if="station.address" class="station-card__address">
        {{ station.address }}
      </p>

      <p v-if="station.description" class="station-card__description">
        {{ station.description }}
      </p>

      <div class="station-card__powerbank-info">
        <div class="station-card__powerbank-item">
          <span class="station-card__powerbank-label">можно взять:</span>
          <span class="station-card__powerbank-value station-card__powerbank-value--available">{{ availableForBorrow }}</span>
        </div>
        <div class="station-card__powerbank-item">
          <span class="station-card__powerbank-label">в станции:</span>
          <span class="station-card__powerbank-value station-card__powerbank-value--returnable">{{ availablePorts }}/{{ totalPorts }}</span>
        </div>
      </div>
      
      <div v-if="lastSeenValue" class="station-card__last-seen">
        <span class="station-card__last-seen-label">Последний раз в сети:</span>
        <span class="station-card__last-seen-time">{{ formatLastSeen(lastSeenValue) }}</span>
      </div>
    </div>
    
    <div class="station-card__actions" v-if="isExpanded">
      <BaseButton
        v-if="showTakeBatteryButton && (availableForBorrow > 0 || station.status === 'active')"
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
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '../stores/auth'
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
  isExpanded: {
    type: Boolean,
    default: true
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

const emit = defineEmits(['toggleFavorite', 'takeBattery', 'returnBattery', 'returnWithError', 'adminClick', 'toggleExpansion'])

const authStore = useAuthStore()

// Свободные слоты в станции (количество свободных слотов)
const availablePorts = computed(() => {
  return props.station.freePorts || 0
})

const totalPorts = computed(() => {
  return props.station.totalPorts || 0
})

// Проверка, является ли пользователь админом
const isUserAdmin = computed(() => {
  return authStore.isAdmin
})

// Доступно аккумуляторов для взятия (с учетом лимита пользователя)
const availableForBorrow = computed(() => {
  const freePorts = props.station.freePorts || 0
  
  // Для админов лимиты не применяются - показываем все свободные порты
  if (isUserAdmin.value) {
    return freePorts
  }
  
  // Получаем лимиты из store
  const availableByLimit = authStore.availableByLimit
  
  // Если нет данных о лимитах, показываем количество свободных портов
  if (availableByLimit === null || availableByLimit === undefined) {
    return freePorts
  }
  
  // Для админов может быть "unlimited" (дополнительная проверка)
  if (availableByLimit === 'unlimited') {
    return freePorts
  }
  
  // Возвращаем минимум из свободных портов и доступного по лимиту
  return Math.min(freePorts, availableByLimit || 0)
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


const parseTimestampToDate = (ts) => {
  if (!ts) return null
  // Accept Unix seconds, Unix ms, ISO strings
  if (typeof ts === 'number') {
    // Heuristic: seconds vs ms
    if (ts < 2e10) {
      return new Date(ts * 1000)
    }
    return new Date(ts)
  }
  if (typeof ts === 'string') {
    // Normalize common backend formats, ensure it parses
    // Add 'Z' if looks like UTC without zone
    const isoLike = /\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(ts)
    const withZone = /[zZ+\-]\d{0,2}:?\d{0,2}$/.test(ts)
    const normalized = isoLike && !withZone ? `${ts}Z` : ts
    const d = new Date(normalized)
    if (!isNaN(d.getTime())) return d
    // Try replacing space with 'T'
    const try2 = new Date(ts.replace(' ', 'T'))
    if (!isNaN(try2.getTime())) return try2
  }
  return null
}

const formatLastSeen = (timestamp) => {
  const date = parseTimestampToDate(timestamp)
  if (!date) return 'Неизвестно'

  const now = new Date(currentTime.value)
  let diffMs = now.getTime() - date.getTime()

  // Guard against clock skew (future timestamps)
  if (diffMs < 0) diffMs = 0

  const diffMins = Math.floor(diffMs / (1000 * 60))
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffMins < 1) return 'Только что'
  if (diffMins < 60) return `${diffMins} мин назад`
  if (diffHours < 24) return `${diffHours} ч назад`
  if (diffDays < 7) return `${diffDays} дн назад`

  return date.toLocaleString('ru-RU', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
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

const handleCardClick = (event) => {
  // Предотвращаем переключение при клике на кнопки
  if (event.target.closest('.base-button') || event.target.closest('button')) {
    return
  }
  emit('toggleExpansion', props.station)
}

// Обновление времени "последний раз в сети" каждые 10 секунд для динамичности
const currentTime = ref(Date.now())
const lastSeenValue = computed(() => props.station.lastSeen || props.station.last_seen || props.station.last_seen_at || props.station.lastSeenAt)
let lastSeenTimer = null

onMounted(() => {
  // Обновляем каждые 10 секунд для более динамичного отображения
  lastSeenTimer = setInterval(() => {
    currentTime.value = Date.now()
  }, 10000)
})

onUnmounted(() => {
  if (lastSeenTimer) {
    clearInterval(lastSeenTimer)
    lastSeenTimer = null
  }
})
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

.station-card--collapsed {
  cursor: pointer;
  transition: all 0.3s ease;
}

.station-card--collapsed:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
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

.station-card__header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.station-card__expand-icon {
  font-size: 12px;
  color: var(--text-secondary);
  transition: transform 0.3s ease;
  cursor: pointer;
}

.station-card__expand-icon--expanded {
  transform: rotate(180deg);
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
  font-family: inherit;
}

.station-card__box-id--header {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  font-family: inherit;
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

  .station-card__header-right {
    gap: 8px;
  }

  .station-card__box-id--header {
    font-size: 14px;
    margin-right: 8px;
  }

  .station-card__expand-icon {
    font-size: 14px;
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
