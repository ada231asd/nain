/**
 * Утилита для обработки установки PWA
 */

let deferredPrompt = null
let isInitialized = false

// Обработчики событий для возможности их удаления
const beforeInstallPromptHandler = (e) => {
  // Предотвращаем автоматическое отображение промпта
  e.preventDefault()
  // Сохраняем событие для использования позже
  deferredPrompt = e
  console.log('📱 PWA готово к установке (beforeinstallprompt)')
  
  // Отправляем событие для компонентов, чтобы показать кнопку установки
  window.dispatchEvent(new CustomEvent('pwa-installable'))
}

const appInstalledHandler = () => {
  console.log('✅ PWA успешно установлено')
  deferredPrompt = null
  // Отправляем событие для скрытия кнопки установки
  window.dispatchEvent(new CustomEvent('pwa-installed'))
}

/**
 * Инициализация обработчика установки PWA
 */
export function initPWAInstall() {
  // Защита от повторной инициализации
  if (isInitialized) {
    console.warn('⚠️ PWA install уже инициализирован')
    return
  }

  // Обработка события beforeinstallprompt (Chrome, Edge, Samsung Internet)
  window.addEventListener('beforeinstallprompt', beforeInstallPromptHandler)

  // Обработка успешной установки
  window.addEventListener('appinstalled', appInstalledHandler)
  
  isInitialized = true
  console.log('✅ PWA install handlers инициализированы')
}

/**
 * Программная установка PWA
 * @returns {Promise<{success: boolean, outcome?: string}>} результат установки
 */
export async function installPWA() {
  if (!deferredPrompt) {
    console.warn('⚠️ Установка PWA недоступна')
    return { success: false }
  }

  try {
    // Показываем промпт установки
    deferredPrompt.prompt()
    
    // Ждем ответа пользователя
    const { outcome } = await deferredPrompt.userChoice
    
    // Очищаем сохраненное событие (важно делать это после userChoice)
    deferredPrompt = null
    
    if (outcome === 'accepted') {
      console.log('✅ Пользователь принял установку PWA')
      return { success: true, outcome: 'accepted' }
    } else {
      console.log('❌ Пользователь отклонил установку PWA')
      return { success: true, outcome: 'dismissed' }
    }
  } catch (error) {
    console.error('❌ Ошибка при установке PWA:', error)
    deferredPrompt = null
    return { success: false, error: error.message }
  }
}

/**
 * Проверка, установлено ли приложение как PWA
 * @returns {boolean}
 */
export function isPWAInstalled() {
  // Проверка для мобильных устройств
  if (window.matchMedia('(display-mode: standalone)').matches) {
    return true
  }
  
  // Проверка для десктопа
  if (window.navigator.standalone === true) {
    return true
  }
  
  return false
}

/**
 * Проверка, можно ли установить PWA
 * @returns {boolean}
 */
export function canInstallPWA() {
  return deferredPrompt !== null
}

