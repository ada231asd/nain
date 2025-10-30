/**
 * Система уведомлений для замены стандартных alert()
 * Показывает чистые уведомления без префикса браузера
 */

/**
 * Показывает уведомление пользователю
 * @param {string} message - Сообщение для отображения
 * @param {string} type - Тип уведомления: 'info', 'success', 'error', 'warning'
 * @param {number} duration - Длительность показа в миллисекундах (0 = не скрывать автоматически)
 */
export function showNotification(message, type = 'info', duration = 4000) {
  // Создаем контейнер для уведомлений, если его еще нет
  let container = document.getElementById('notification-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'notification-container';
    container.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      z-index: 10000;
      display: flex;
      flex-direction: column;
      gap: 10px;
      max-width: 400px;
      pointer-events: none;
    `;
    document.body.appendChild(container);
  }

  // Создаем элемент уведомления
  const notification = document.createElement('div');
  notification.className = `notification notification-${type}`;
  
  // Определяем иконку в зависимости от типа
  const icons = {
    success: '✅',
    error: '❌',
    warning: '⚠️',
    info: 'ℹ️'
  };
  const icon = icons[type] || icons.info;

  // Определяем цвета в зависимости от типа
  const colors = {
    success: { bg: '#10b981', border: '#059669' },
    error: { bg: '#ef4444', border: '#dc2626' },
    warning: { bg: '#f59e0b', border: '#d97706' },
    info: { bg: '#3b82f6', border: '#2563eb' }
  };
  const color = colors[type] || colors.info;

  notification.innerHTML = `
    <div style="
      background: ${color.bg};
      color: white;
      padding: 16px 20px;
      border-radius: 8px;
      border-left: 4px solid ${color.border};
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      display: flex;
      align-items: flex-start;
      gap: 12px;
      pointer-events: auto;
      cursor: pointer;
      transition: all 0.3s ease;
      animation: slideIn 0.3s ease;
      max-width: 100%;
      word-wrap: break-word;
    ">
      <span style="font-size: 20px; flex-shrink: 0;">${icon}</span>
      <span style="flex: 1; line-height: 1.5; white-space: pre-wrap;">${escapeHtml(message)}</span>
      <button style="
        background: rgba(255, 255, 255, 0.2);
        border: none;
        color: white;
        border-radius: 4px;
        padding: 4px 8px;
        cursor: pointer;
        font-size: 16px;
        line-height: 1;
        transition: background 0.2s;
      " onclick="this.parentElement.parentElement.remove()">×</button>
    </div>
  `;

  // Добавляем стили анимации, если их еще нет
  if (!document.getElementById('notification-styles')) {
    const style = document.createElement('style');
    style.id = 'notification-styles';
    style.textContent = `
      @keyframes slideIn {
        from {
          transform: translateX(400px);
          opacity: 0;
        }
        to {
          transform: translateX(0);
          opacity: 1;
        }
      }
      @keyframes slideOut {
        from {
          transform: translateX(0);
          opacity: 1;
        }
        to {
          transform: translateX(400px);
          opacity: 0;
        }
      }
      .notification > div:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2) !important;
      }
      .notification > div:hover button {
        background: rgba(255, 255, 255, 0.3) !important;
      }
    `;
    document.head.appendChild(style);
  }

  // Добавляем уведомление в контейнер
  container.appendChild(notification);

  // Закрытие по клику на уведомление
  notification.firstElementChild.addEventListener('click', (e) => {
    if (e.target.tagName !== 'BUTTON') {
      removeNotification(notification);
    }
  });

  // Автоматическое удаление через заданное время
  if (duration > 0) {
    setTimeout(() => {
      removeNotification(notification);
    }, duration);
  }

  return notification;
}

/**
 * Удаляет уведомление с анимацией
 */
function removeNotification(notification) {
  const div = notification.firstElementChild;
  if (div) {
    div.style.animation = 'slideOut 0.3s ease';
    setTimeout(() => {
      notification.remove();
    }, 300);
  }
}

/**
 * Экранирование HTML для безопасности
 */
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Показывает уведомление об успехе
 */
export function showSuccess(message, duration = 4000) {
  return showNotification(message, 'success', duration);
}

/**
 * Показывает уведомление об ошибке
 */
export function showError(message, duration = 6000) {
  return showNotification(message, 'error', duration);
}

/**
 * Показывает предупреждение
 */
export function showWarning(message, duration = 5000) {
  return showNotification(message, 'warning', duration);
}

/**
 * Показывает информационное сообщение
 */
export function showInfo(message, duration = 4000) {
  return showNotification(message, 'info', duration);
}

/**
 * Показывает диалог подтверждения
 * @param {string} message - Сообщение
 * @param {string} confirmText - Текст кнопки подтверждения
 * @param {string} cancelText - Текст кнопки отмены
 * @returns {Promise<boolean>} - true если подтверждено, false если отменено
 */
export function showConfirm(message, confirmText = 'Да', cancelText = 'Отмена') {
  return new Promise((resolve) => {
    // Создаем оверлей
    const overlay = document.createElement('div');
    overlay.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.5);
      z-index: 10001;
      display: flex;
      align-items: center;
      justify-content: center;
      animation: fadeIn 0.2s ease;
    `;

    // Создаем модальное окно
    const modal = document.createElement('div');
    modal.style.cssText = `
      background: white;
      padding: 24px;
      border-radius: 12px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
      max-width: 400px;
      width: 90%;
      animation: scaleIn 0.2s ease;
    `;

    modal.innerHTML = `
      <div style="margin-bottom: 20px; font-size: 16px; line-height: 1.6; color: #1e293b; white-space: pre-wrap;">${escapeHtml(message)}</div>
      <div style="display: flex; gap: 12px; justify-content: flex-end;">
        <button id="cancel-btn" style="
          padding: 10px 20px;
          border: 1px solid #cbd5e1;
          background: white;
          color: #475569;
          border-radius: 6px;
          cursor: pointer;
          font-size: 14px;
          font-weight: 500;
          transition: all 0.2s;
        ">${escapeHtml(cancelText)}</button>
        <button id="confirm-btn" style="
          padding: 10px 20px;
          border: none;
          background: #3b82f6;
          color: white;
          border-radius: 6px;
          cursor: pointer;
          font-size: 14px;
          font-weight: 500;
          transition: all 0.2s;
        ">${escapeHtml(confirmText)}</button>
      </div>
    `;

    // Добавляем стили анимации
    if (!document.getElementById('confirm-styles')) {
      const style = document.createElement('style');
      style.id = 'confirm-styles';
      style.textContent = `
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes scaleIn {
          from { transform: scale(0.9); opacity: 0; }
          to { transform: scale(1); opacity: 1; }
        }
        #cancel-btn:hover {
          background: #f1f5f9 !important;
          border-color: #94a3b8 !important;
        }
        #confirm-btn:hover {
          background: #2563eb !important;
        }
      `;
      document.head.appendChild(style);
    }

    overlay.appendChild(modal);
    document.body.appendChild(overlay);

    // Обработчики кнопок
    const confirmBtn = modal.querySelector('#confirm-btn');
    const cancelBtn = modal.querySelector('#cancel-btn');

    const cleanup = (result) => {
      overlay.style.animation = 'fadeIn 0.2s ease reverse';
      setTimeout(() => {
        overlay.remove();
        resolve(result);
      }, 200);
    };

    confirmBtn.addEventListener('click', () => cleanup(true));
    cancelBtn.addEventListener('click', () => cleanup(false));
    
    // Закрытие по клику на оверлей
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        cleanup(false);
      }
    });

    // Закрытие по Escape
    const escapeHandler = (e) => {
      if (e.key === 'Escape') {
        cleanup(false);
        document.removeEventListener('keydown', escapeHandler);
      }
    };
    document.addEventListener('keydown', escapeHandler);
  });
}

// Экспортируем как дефолт объект со всеми методами
export default {
  show: showNotification,
  success: showSuccess,
  error: showError,
  warning: showWarning,
  info: showInfo,
  confirm: showConfirm
};

