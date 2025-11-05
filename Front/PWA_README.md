# ⚡ PWA ЗАРЯД - Progressive Web App

Это PWA (Progressive Web App) версия сервиса аренды павербанков ЗАРЯД.

## 🚀 Быстрый старт

### 1. Установка зависимостей
```bash
cd Front
npm install
```

### 2. Создание иконок

**Вариант A: Автоматический генератор (рекомендуется для начала)**
1. Откройте файл `generate-placeholder-icons.html` в браузере
2. Настройте цвета и текст
3. Нажмите "Сгенерировать иконки"
4. Скачайте все иконки
5. Распакуйте в папку `Front/public/`

**Вариант B: Онлайн генератор**
- Используйте https://www.pwabuilder.com/imageGenerator
- Подробности в `ICONS_GUIDE.md`

**Вариант C: Свои иконки**
- Создайте иконки по инструкции в `ICONS_GUIDE.md`

### 3. Локальная разработка
```bash
npm run dev
```

### 4. Сборка для production
```bash
npm run build
```

Результат будет в папке `dist/`

### 5. Развертывание на Nginx
См. подробную инструкцию в `DEPLOYMENT.md`

## 📁 Структура файлов PWA

```
Front/
├── public/                          # Статические файлы
│   ├── pwa-64x64.png               # ⚠️ Создать
│   ├── pwa-192x192.png             # ⚠️ Создать
│   ├── pwa-512x512.png             # ⚠️ Создать
│   ├── maskable-icon-512x512.png   # ⚠️ Создать
│   ├── apple-touch-icon.png        # ⚠️ Создать
│   ├── favicon-32x32.png           # ⚠️ Создать
│   ├── favicon-16x16.png           # ⚠️ Создать
│   └── masked-icon.svg             # Опционально
├── dist/                           # Собранное приложение (после npm run build)
│   ├── index.html
│   ├── manifest.webmanifest        # Автоматически создается
│   ├── sw.js                       # Service Worker (автоматически)
│   └── ...
├── vite.config.js                  # ✅ Настроен для PWA
├── index.html                      # ✅ Обновлен с PWA мета-тегами
├── package.json                    # ✅ Добавлен vite-pwa plugin
├── nginx.conf                      # Конфигурация для Nginx
├── PWA_README.md                   # Этот файл
├── PWA_SETUP.md                    # Подробная настройка PWA
├── ICONS_GUIDE.md                  # Руководство по иконкам
├── DEPLOYMENT.md                   # Инструкция по развертыванию
└── generate-placeholder-icons.html # Генератор иконок
```

## ✅ Что уже настроено

- ✅ Vite Plugin PWA установлен и настроен
- ✅ Манифест PWA (автоматически генерируется)
- ✅ Service Worker с автообновлением
- ✅ Кэширование статических ресурсов
- ✅ Кэширование API запросов (NetworkFirst стратегия)
- ✅ Поддержка офлайн режима
- ✅ Meta теги для PWA в index.html
- ✅ Конфигурация Nginx для production
- ✅ Поддержка WebSocket через proxy

## ⚠️ Что нужно сделать

1. **Создать иконки** (см. раздел "Создание иконок" выше)
2. **Настроить HTTPS** (обязательно для PWA!)
3. **Настроить домен** в `nginx.conf`
4. **Собрать проект** `npm run build`
5. **Развернуть на сервер**

## 🎨 Особенности PWA

### Что получает пользователь:
- 📱 **Установка на главный экран** - как нативное приложение
- ⚡ **Мгновенная загрузка** - благодаря кэшированию
- 🔌 **Работа офлайн** - базовые функции доступны без интернета
- 🔔 **Push уведомления** - (можно добавить в будущем)
- 🎯 **Полноэкранный режим** - без браузерных элементов
- 🚀 **Автоматические обновления** - без участия пользователя

### Стратегии кэширования:

1. **Статические файлы** (JS, CSS, изображения)
   - Стратегия: `CacheFirst`
   - Хранятся 1 год
   - Мгновенная загрузка

2. **API запросы**
   - Стратегия: `NetworkFirst`
   - Кэш на 5 минут
   - Офлайн fallback

3. **Шрифты Google Fonts**
   - Стратегия: `CacheFirst`
   - Хранятся 1 год

## 🔧 Настройки манифеста

Текущие настройки в `vite.config.js`:

```javascript
{
  name: 'ЗАРЯД - Сервис аренды павербанков',
  short_name: 'ЗАРЯД',
  description: 'Сервис аренды павербанков для зарядки устройств',
  theme_color: '#ffffff',
  background_color: '#ffffff',
  display: 'standalone',
  orientation: 'portrait'
}
```

Для изменения откройте `Front/vite.config.js` и отредактируйте секцию `manifest`.

## 📱 Поддерживаемые платформы

| Платформа | Поддержка | Примечания |
|-----------|-----------|------------|
| Android Chrome | ✅ Полная | Лучшая поддержка |
| iOS Safari 16.4+ | ✅ Полная | Требуется iOS 16.4+ |
| Windows Chrome/Edge | ✅ Полная | - |
| macOS Safari/Chrome | ✅ Полная | - |
| Linux Chrome/Firefox | ✅ Полная | - |

## 🐛 Отладка PWA

### Chrome DevTools
```
F12 → Application → 
  - Manifest (проверка манифеста)
  - Service Workers (статус SW)
  - Storage → Cache Storage (просмотр кэша)
```

### Lighthouse Audit
```
F12 → Lighthouse → 
  Categories: Progressive Web App
  → Generate Report
```

**Цель:** PWA score > 90

### Проверка регистрации Service Worker
```javascript
// Откройте консоль браузера
navigator.serviceWorker.getRegistrations().then(registrations => {
  console.log('Service Workers:', registrations);
});
```

### Очистка кэша для тестирования
```javascript
// Консоль браузера
caches.keys().then(keys => {
  keys.forEach(key => caches.delete(key));
  console.log('Cache cleared');
});
```

## 📊 Критерии установки PWA

Браузер предложит установку PWA, если:
- ✅ Используется HTTPS (или localhost для разработки)
- ✅ Есть валидный манифест (`manifest.webmanifest`)
- ✅ Зарегистрирован Service Worker
- ✅ Service Worker обрабатывает событие `fetch`
- ✅ Есть иконки размером минимум 192×192 и 512×512
- ✅ Манифест содержит `name` или `short_name`
- ✅ Манифест содержит `start_url`
- ✅ Манифест содержит `display` (standalone, fullscreen, или minimal-ui)

Все эти критерии уже выполнены в текущей конфигурации!

## 🔐 Требования безопасности

### HTTPS обязателен!
PWA **не будет работать** без HTTPS в production!

**Исключения:**
- `localhost` для разработки
- `127.0.0.1` для разработки

### Получение бесплатного SSL:
```bash
# Certbot для Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

См. подробности в `DEPLOYMENT.md`

## 📚 Документация

- **PWA_SETUP.md** - Детальная настройка и требования
- **ICONS_GUIDE.md** - Создание иконок (с примерами)
- **DEPLOYMENT.md** - Развертывание на Nginx (пошагово)
- **nginx.conf** - Готовая конфигурация сервера

## 🎯 Следующие шаги

1. **Сейчас:**
   - [ ] Создайте иконки (используйте `generate-placeholder-icons.html`)
   - [ ] Соберите проект (`npm run build`)
   - [ ] Протестируйте локально (`npx serve dist`)

2. **Перед деплоем:**
   - [ ] Настройте HTTPS сертификат
   - [ ] Отредактируйте `nginx.conf` (домен, пути, API backend)
   - [ ] Настройте proxy для API запросов

3. **После деплоя:**
   - [ ] Проверьте Lighthouse audit (должен быть > 90)
   - [ ] Протестируйте установку PWA на разных устройствах
   - [ ] Проверьте работу офлайн режима

4. **Опционально:**
   - [ ] Настройте Push уведомления
   - [ ] Добавьте страницу офлайн fallback
   - [ ] Настройте аналитику для отслеживания установок
   - [ ] Добавьте бейдж на иконку приложения

## 💡 Полезные команды

```bash
# Разработка
npm run dev                 # Запуск dev сервера

# Production
npm run build              # Сборка для production
npm run preview            # Предпросмотр production сборки

# Проверка
npx serve dist             # Локальный сервер для dist/
npx lighthouse https://your-url --view  # Lighthouse audit

# Очистка
rm -rf dist/              # Удаление старой сборки
rm -rf node_modules/      # Удаление зависимостей
npm install               # Переустановка зависимостей
```

## 🆘 Частые проблемы

### PWA не предлагает установку
- Проверьте HTTPS
- Проверьте манифест в DevTools
- Убедитесь, что все иконки доступны

### Service Worker не регистрируется
- Проверьте консоль браузера на ошибки
- Убедитесь, что используется HTTPS (или localhost)
- Очистите кэш браузера

### Изменения не видны после обновления
- Жесткая перезагрузка (Ctrl+Shift+R)
- Очистите кэш в DevTools
- Проверьте, что Service Worker обновился

### API запросы не работают
- Проверьте настройки proxy в `nginx.conf`
- Убедитесь, что backend запущен
- Проверьте CORS настройки

## 📞 Дополнительная информация

### Официальная документация:
- [Vite PWA Plugin](https://vite-pwa-org.netlify.app/)
- [Web.dev PWA Guide](https://web.dev/progressive-web-apps/)
- [MDN PWA Documentation](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps)

### Инструменты:
- [PWA Builder](https://www.pwabuilder.com/)
- [Maskable.app](https://maskable.app/)
- [Lighthouse](https://developer.chrome.com/docs/lighthouse/)

---

**Приложение готово к преобразованию в PWA! 🎉**

Следуйте инструкциям выше и ваше приложение будет работать как нативное на всех платформах.

