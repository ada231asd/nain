<template>
  <button
    v-if="showInstallButton"
    class="pwa-install-btn"
    @click="handleInstall"
    :disabled="isInstalling"
    aria-label="Установить приложение"
  >
    <span class="pwa-install-btn__icon">📱</span>
    <span class="pwa-install-btn__text">{{ isInstalling ? 'Установка...' : 'Установить' }}</span>
  </button>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { canInstallPWA, installPWA, isPWAInstalled } from '../utils/pwa-install'

const showInstallButton = ref(false)
const isInstalling = ref(false)

const checkInstallability = () => {
  // Не показываем кнопку, если приложение уже установлено
  if (isPWAInstalled()) {
    showInstallButton.value = false
    return
  }
  
  // Показываем кнопку только если установка доступна
  showInstallButton.value = canInstallPWA()
}

const handleInstall = async () => {
  if (!canInstallPWA()) {
    return
  }
  
  isInstalling.value = true
  
  try {
    const success = await installPWA()
    if (success) {
      // После успешной установки скрываем кнопку
      setTimeout(() => {
        showInstallButton.value = false
      }, 500)
    }
  } catch (error) {
    console.error('Ошибка при установке PWA:', error)
  } finally {
    isInstalling.value = false
  }
}

// Слушаем событие о готовности к установке
const handlePWAInstallable = () => {
  checkInstallability()
}

// Слушаем событие об успешной установке
const handlePWAInstalled = () => {
  showInstallButton.value = false
}

onMounted(() => {
  // Проверяем сразу при монтировании
  checkInstallability()
  
  // Слушаем событие о готовности к установке (из pwa-install.js)
  window.addEventListener('pwa-installable', handlePWAInstallable)
  
  // Слушаем событие об успешной установке
  window.addEventListener('pwa-installed', handlePWAInstalled)
  
  // Также проверяем периодически (на случай если событие уже произошло)
  setTimeout(checkInstallability, 1000)
  setTimeout(checkInstallability, 2000)
})

onUnmounted(() => {
  window.removeEventListener('pwa-installable', handlePWAInstallable)
  window.removeEventListener('pwa-installed', handlePWAInstalled)
})
</script>

<style scoped>
.pwa-install-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
  white-space: nowrap;
}

.pwa-install-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
  background: linear-gradient(135deg, #5568d3 0%, #6a4190 100%);
}

.pwa-install-btn:active:not(:disabled) {
  transform: translateY(0);
}

.pwa-install-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.pwa-install-btn__icon {
  font-size: 18px;
  line-height: 1;
}

.pwa-install-btn__text {
  font-weight: 500;
}

@media (max-width: 768px) {
  .pwa-install-btn {
    padding: 6px 12px;
    font-size: 13px;
  }
  
  .pwa-install-btn__text {
    display: none;
  }
  
  .pwa-install-btn__icon {
    font-size: 20px;
  }
}
</style>

