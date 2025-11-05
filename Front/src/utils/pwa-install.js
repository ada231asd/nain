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
  
  // Детальное логирование для отладки
  const ua = navigator.userAgent
  const browserInfo = {
    isYandex: /yabrowser|yaapp/i.test(ua),
    isChrome: /chrome/i.test(ua) && !/yabrowser|yaapp|edg/i.test(ua),
    hasPrompt: !!e.prompt,
    canPrompt: typeof e.prompt === 'function'
  }
  
  console.log('📱 PWA готово к установке (beforeinstallprompt)', {
    browser: browserInfo,
    userAgent: ua,
    event: e
  })
  
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
 * Определение браузера Yandex
 * @returns {boolean}
 */
export function isYandexBrowser() {
  const ua = navigator.userAgent.toLowerCase()
  // Yandex браузер имеет специфичные признаки в user agent
  return /yabrowser|yaapp/.test(ua) || 
         (window.yandex !== undefined && window.yandex !== null)
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

  const ua = navigator.userAgent
  const browserInfo = {
    isYandex: isYandexBrowser(),
    isSafari: isSafari(),
    isChrome: /chrome/i.test(ua) && !/yabrowser|yaapp|edg/i.test(ua),
    userAgent: ua,
    hasServiceWorker: 'serviceWorker' in navigator,
    isStandalone: window.matchMedia('(display-mode: standalone)').matches
  }
  
  console.log('🔍 Инициализация PWA install:', browserInfo)

  // Проверка наличия манифеста
  const manifestLink = document.querySelector('link[rel="manifest"]')
  if (!manifestLink) {
    console.warn('⚠️ Манифест PWA не найден в DOM')
  } else {
    console.log('✅ Манифест найден:', manifestLink.href)
  }

  // Обработка события beforeinstallprompt (Chrome, Edge, Yandex Browser, Samsung Internet)
  // Safari не поддерживает это событие
  if (!isSafari()) {
    // Для Yandex браузера и других Chromium-браузеров добавляем обработчик
    window.addEventListener('beforeinstallprompt', beforeInstallPromptHandler)
    
    // Для Yandex браузера также добавляем дополнительную проверку через небольшой таймаут
    // так как событие может сработать с задержкой
    if (isYandexBrowser()) {
      console.log('🌐 Yandex браузер обнаружен - добавлена дополнительная проверка')
      
      // Проверяем через небольшие интервалы, не сработало ли событие
      let checkCount = 0
      const maxChecks = 10 // проверяем 10 раз (20 секунд)
      
      const yandexCheckInterval = setInterval(() => {
        checkCount++
        
        // Если deferredPrompt уже установлен, прекращаем проверку
        if (deferredPrompt !== null) {
          clearInterval(yandexCheckInterval)
          console.log('✅ Yandex: beforeinstallprompt получен через проверку')
          return
        }
        
        // Если превысили лимит проверок, прекращаем
        if (checkCount >= maxChecks) {
          clearInterval(yandexCheckInterval)
          console.warn('⚠️ Yandex: beforeinstallprompt не получен после', maxChecks * 2, 'секунд')
          
          // Проверяем, может быть приложение уже установлено
          if (isPWAInstalled()) {
            console.log('ℹ️ Yandex: Приложение уже установлено как PWA')
          } else {
            // Если событие не пришло, но мы в Yandex браузере, проверяем манифест
            // и пытаемся показать кнопку установки через альтернативный способ
            if (manifestLink) {
              console.log('ℹ️ Yandex: Показываем кнопку установки (манифест найден)')
              window.dispatchEvent(new CustomEvent('pwa-installable'))
            }
          }
        }
      }, 2000) // проверяем каждые 2 секунды
    }
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
    console.warn('⚠️ Установка PWA недоступна - deferredPrompt отсутствует')
    
    // Для Yandex браузера пробуем альтернативный способ
    if (isYandexBrowser()) {
      console.log('🌐 Yandex: Пробуем альтернативный способ проверки установки')
      
      // Проверяем, может быть событие еще не пришло
      // Пробуем вызвать установку через прямое обращение к браузеру
      // (Yandex браузер может требовать прямого вызова)
      try {
        // Проверяем наличие манифеста
        const manifestLink = document.querySelector('link[rel="manifest"]')
        if (manifestLink) {
          console.log('ℹ️ Yandex: Манифест найден, но beforeinstallprompt не получен')
          console.log('ℹ️ Yandex: Пользователь может установить приложение через меню браузера')
          return { 
            success: false, 
            needsManualInstall: true,
            message: 'Для установки используйте меню браузера: "Установить приложение"' 
          }
        }
      } catch (error) {
        console.error('❌ Yandex: Ошибка при проверке:', error)
      }
    }
    
    return { success: false }
  }

  try {
    // Детальное логирование для Yandex браузера
    if (isYandexBrowser()) {
      console.log('🌐 Yandex: Запуск установки PWA', {
        hasPrompt: typeof deferredPrompt.prompt === 'function',
        promptType: typeof deferredPrompt.prompt
      })
    }
    
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
    
    // Для Yandex браузера добавляем дополнительную информацию
    if (isYandexBrowser()) {
      console.error('🌐 Yandex: Детали ошибки:', {
        error: error.message,
        stack: error.stack,
        deferredPrompt: deferredPrompt
      })
    }
    
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
  
  // Для Yandex браузера более либеральная проверка
  if (isYandexBrowser()) {
    // Если есть deferredPrompt - точно можно установить
    if (deferredPrompt !== null) {
      return true
    }
    
    // Если deferredPrompt еще нет, но есть манифест и приложение не установлено,
    // показываем кнопку (событие может прийти позже)
    const manifestLink = document.querySelector('link[rel="manifest"]')
    if (manifestLink && !isPWAInstalled()) {
      return true
    }
    
    return false
  }
  
  // Для других браузеров проверяем наличие deferredPrompt
  return deferredPrompt !== null
}

