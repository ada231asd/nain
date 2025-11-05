/**
 * Утилита для обработки установки PWA
 */

let deferredPrompt = null

/**
 * Инициализация обработчика установки PWA
 */
export function initPWAInstall() {
  // Обработка события beforeinstallprompt (Chrome, Edge, Samsung Internet)
  window.addEventListener('beforeinstallprompt', (e) => {
    // Предотвращаем автоматическое отображение промпта
    e.preventDefault()
    // Сохраняем событие для использования позже
    deferredPrompt = e
    console.log('📱 PWA готово к установке (beforeinstallprompt)')
    
    // Можно показать кастомную кнопку установки
    // dispatchEvent(new CustomEvent('pwa-installable'))
  })

  // Обработка успешной установки
  window.addEventListener('appinstalled', () => {
    console.log('✅ PWA успешно установлено')
    deferredPrompt = null
    // Можно показать уведомление об успешной установке
  })
}

/**
 * Программная установка PWA
 * @returns {Promise<boolean>} true если установка инициирована, false если недоступна
 */
export async function installPWA() {
  if (!deferredPrompt) {
    console.warn('⚠️ Установка PWA недоступна')
    return false
  }

  try {
    // Показываем промпт установки
    deferredPrompt.prompt()
    
    // Ждем ответа пользователя
    const { outcome } = await deferredPrompt.userChoice
    
    if (outcome === 'accepted') {
      console.log('✅ Пользователь принял установку PWA')
    } else {
      console.log('❌ Пользователь отклонил установку PWA')
    }
    
    // Очищаем сохраненное событие
    deferredPrompt = null
    return true
  } catch (error) {
    console.error('❌ Ошибка при установке PWA:', error)
    return false
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

