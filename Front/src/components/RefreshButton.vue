<template>
  <button 
    class="refresh-button" 
    @click="handleRefresh"
    :disabled="isRefreshing"
    :title="title || 'Обновить данные'"
  >
    <svg 
      class="refresh-icon" 
      :class="{ 'rotating': isRefreshing }"
      viewBox="0 0 24 24" 
      fill="none" 
      xmlns="http://www.w3.org/2000/svg"
    >
      <path 
        d="M4 4V10H4.58152M19.9381 11C19.446 7.05369 16.0796 4 12 4C8.64262 4 5.76829 6.06817 4.58152 9M4.58152 9H10M20 20V14H19.4185M19.4185 14C18.2317 17.9318 15.3574 20 12 20C7.92038 20 4.55399 16.9463 4.06189 13M19.4185 14H14" 
        stroke="currentColor" 
        stroke-width="2" 
        stroke-linecap="round" 
        stroke-linejoin="round"
      />
    </svg>
    <span v-if="showText" class="refresh-text">Обновить</span>
  </button>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  title: {
    type: String,
    default: 'Обновить данные'
  },
  showText: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['refresh'])

const isRefreshing = ref(false)

const handleRefresh = async () => {
  if (isRefreshing.value) return
  
  isRefreshing.value = true
  try {
    await emit('refresh')
  } finally {
    // Небольшая задержка для визуального эффекта вращения
    setTimeout(() => {
      isRefreshing.value = false
    }, 500)
  }
}
</script>

<style scoped>
.refresh-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: white;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  color: #333;
  transition: all 0.3s ease;
  flex-shrink: 0;
}

.refresh-button:hover:not(:disabled) {
  border-color: #667eea;
  background: #f8f9fa;
}

.refresh-button:active:not(:disabled) {
  transform: scale(0.98);
}

.refresh-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.refresh-icon {
  width: 18px;
  height: 18px;
  color: #667eea;
  transition: transform 0.3s ease;
  flex-shrink: 0;
}

.refresh-icon.rotating {
  animation: rotate 1s linear infinite;
}

.refresh-text {
  color: #333;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>

