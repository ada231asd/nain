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
 * Определение браузера Safari
 * @returns {boolean}
 */
export function isSafari() {
  const ua = navigator.userAgent.toLowerCase()
  const isIOS = /iphone|ipad|ipod/.test(ua)
  const isMacOS = /macintosh|mac os x/.test(ua)
  
  // Проверка для iOS Safari
  if (isIOS) {
    // В iOS Safari нет window.chrome, но есть специфичные признаки
    return !window.MSStream && !window.chrome && /safari/.test(ua) && !/crios|fxios/.test(ua)
  }
  
  // Проверка для macOS Safari
  if (isMacOS) {
    // В macOS Safari есть специфичные признаки
    const hasSafariUA = /safari/.test(ua) && !/chrome|crios|fxios/.test(ua)
    // Дополнительная проверка: Safari имеет vendor 'Apple Computer, Inc.'
    const isAppleVendor = navigator.vendor && navigator.vendor.indexOf('Apple') !== -1
    return hasSafariUA && isAppleVendor && !window.chrome
  }
  
  // Проверка для других платформ (Windows Safari и т.д.)
  const isSafariUA = /safari/.test(ua) && !/chrome|crios|fxios/.test(ua)
  return isSafariUA && !window.chrome
}

/**
 * Определение iOS устройства
 * @returns {boolean}
 */
export function isIOS() {
  return /iphone|ipad|ipod/.test(navigator.userAgent.toLowerCase()) && !window.MSStream
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
  // Safari не поддерживает это событие
  if (!isSafari()) {
    window.addEventListener('beforeinstallprompt', beforeInstallPromptHandler)
  } else {
    // Для Safari проверяем, можно ли показать кнопку установки
    // Safari требует ручной установки через меню "Поделиться"
    console.log('🍎 Safari обнаружен - установка через меню "Поделиться"')
    
    // Проверяем периодически, не установлено ли уже приложение
    const checkInterval = setInterval(() => {
      if (isPWAInstalled()) {
        clearInterval(checkInterval)
        return
      }
      // Отправляем событие для показа инструкций по установке в Safari
      window.dispatchEvent(new CustomEvent('pwa-installable'))
    }, 2000)
    
    // Останавливаем проверку через 10 секунд
    setTimeout(() => clearInterval(checkInterval), 10000)
  }

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
  // В Safari нельзя программно установить PWA
  if (isSafari()) {
    console.log('🍎 Safari не поддерживает программную установку PWA')
    return { success: false, isSafari: true }
  }

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
  
  // Проверка для iOS Safari (standalone mode)
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
  // В Safari всегда можно показать инструкции (если не установлено)
  if (isSafari()) {
    return !isPWAInstalled()
  }
  
  // Для других браузеров проверяем наличие deferredPrompt
  return deferredPrompt !== null
}

