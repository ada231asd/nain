<template>
  <!-- Кнопка установки для Chrome/Edge и других браузеров -->
  <button
    v-if="showInstallButton && !isSafariBrowser"
    class="pwa-install-btn"
    @click="handleInstall"
    :disabled="isInstalling"
    aria-label="Установить приложение"
  >
    <span class="pwa-install-btn__icon">📱</span>
    <span class="pwa-install-btn__text">{{ isInstalling ? 'Установка...' : 'Установить' }}</span>
  </button>

  <!-- Кнопка с инструкциями для Safari -->
  <button
    v-if="showInstallButton && isSafariBrowser"
    class="pwa-install-btn pwa-install-btn--safari"
    @click="showSafariInstructions = true"
    aria-label="Инструкции по установке"
  >
    <span class="pwa-install-btn__icon">📱</span>
    <span class="pwa-install-btn__text">Установить</span>
  </button>

  <!-- Модальное окно с инструкциями для Safari -->
  <div v-if="showSafariInstructions" class="safari-instructions-overlay" @click="showSafariInstructions = false">
    <div class="safari-instructions-modal" @click.stop>
      <button class="safari-instructions-close" @click="showSafariInstructions = false" aria-label="Закрыть">
        ✕
      </button>
      <h2 class="safari-instructions-title">Как установить приложение на iPhone/iPad</h2>
      <div class="safari-instructions-content">
        <div class="safari-instructions-step">
          <div class="safari-instructions-step-number">1</div>
          <div class="safari-instructions-step-text">
            Нажмите кнопку <strong>"Поделиться"</strong> <span class="safari-instructions-icon">📤</span> внизу экрана
          </div>
        </div>
        <div class="safari-instructions-step">
          <div class="safari-instructions-step-number">2</div>
          <div class="safari-instructions-step-text">
            Прокрутите вниз и нажмите <strong>"На экран Домой"</strong> <span class="safari-instructions-icon">➕</span>
          </div>
        </div>
        <div class="safari-instructions-step">
          <div class="safari-instructions-step-number">3</div>
          <div class="safari-instructions-step-text">
            Нажмите <strong>"Добавить"</strong> в правом верхнем углу
          </div>
        </div>
      </div>
      <div class="safari-instructions-note">
        После установки приложение появится на главном экране вашего устройства
      </div>
      <button class="safari-instructions-close-btn" @click="showSafariInstructions = false">
        Понятно
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { canInstallPWA, installPWA, isPWAInstalled, isSafari } from '../utils/pwa-install'

const showInstallButton = ref(false)
const isInstalling = ref(false)
const isSafariBrowser = ref(false)
const showSafariInstructions = ref(false)

const checkInstallability = () => {
  // Не показываем кнопку, если приложение уже установлено
  if (isPWAInstalled()) {
    showInstallButton.value = false
    return
  }
  
  // Проверяем браузер Safari
  isSafariBrowser.value = isSafari()
  
  // Показываем кнопку только если установка доступна
  showInstallButton.value = canInstallPWA()
}

const handleInstall = async () => {
  if (!canInstallPWA()) {
    return
  }
  
  isInstalling.value = true
  
  try {
    const result = await installPWA()
    if (result.success) {
      // Если пользователь принял установку, скрываем кнопку сразу
      // Если отклонил, кнопка скроется после очистки deferredPrompt
      if (result.outcome === 'accepted') {
        showInstallButton.value = false
      } else {
        // После отклонения также скрываем кнопку
        setTimeout(() => {
          showInstallButton.value = false
        }, 500)
      }
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
  justify-content: center;
  gap: 10px;
  padding: 12px 24px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
  width: 100%;
  text-align: center;
}

.pwa-install-btn:hover:not(:disabled) {
  background: #5a6fd8;
  transform: translateY(-2px);
  box-shadow: 0 5px 18px rgba(0, 0, 0, 0.15);
}

.pwa-install-btn:active:not(:disabled) {
  transform: translateY(0);
  box-shadow: 0 3px 12px rgba(0, 0, 0, 0.12);
}

.pwa-install-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.pwa-install-btn__icon {
  font-size: 18px;
  line-height: 1;
}

.pwa-install-btn__text {
  font-weight: 600;
}

/* Safari инструкции модальное окно */
.safari-instructions-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
  padding: 20px;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.safari-instructions-modal {
  background: white;
  border-radius: 16px;
  padding: 24px;
  max-width: 500px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  position: relative;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  animation: slideUp 0.3s ease;
}

@keyframes slideUp {
  from {
    transform: translateY(20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.safari-instructions-close {
  position: absolute;
  top: 16px;
  right: 16px;
  background: none;
  border: none;
  font-size: 24px;
  color: #666;
  cursor: pointer;
  padding: 4px;
  line-height: 1;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: all 0.2s ease;
}

.safari-instructions-close:hover {
  background: #f0f0f0;
  color: #333;
}

.safari-instructions-title {
  font-size: 20px;
  font-weight: 600;
  margin: 0 0 24px 0;
  color: #333;
  text-align: center;
}

.safari-instructions-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin-bottom: 24px;
}

.safari-instructions-step {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.safari-instructions-step-number {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 16px;
}

.safari-instructions-step-text {
  flex: 1;
  font-size: 16px;
  line-height: 1.5;
  color: #333;
  padding-top: 4px;
}

.safari-instructions-step-text strong {
  color: #667eea;
  font-weight: 600;
}

.safari-instructions-icon {
  font-size: 18px;
  margin-left: 4px;
}

.safari-instructions-note {
  background: #f8f9fa;
  border-left: 4px solid #667eea;
  padding: 12px 16px;
  border-radius: 4px;
  font-size: 14px;
  color: #666;
  margin-bottom: 20px;
  line-height: 1.5;
}

.safari-instructions-close-btn {
  width: 100%;
  padding: 12px 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
}

.safari-instructions-close-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.safari-instructions-close-btn:active {
  transform: translateY(0);
}

@media (max-width: 768px) {
  .safari-instructions-modal {
    padding: 20px;
    margin: 10px;
  }

  .safari-instructions-title {
    font-size: 18px;
    margin-bottom: 20px;
  }

  .safari-instructions-step-text {
    font-size: 15px;
  }

  .safari-instructions-step-number {
    width: 28px;
    height: 28px;
    font-size: 14px;
  }
}
</style>

