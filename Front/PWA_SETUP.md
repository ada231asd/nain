# Настройка PWA для проекта ЗАРЯД

## 📋 Требования

1. Node.js 18+ и npm
2. Nginx для production
3. HTTPS сертификат (обязательно для PWA)

## 🎨 Создание иконок для PWA

### Необходимые иконки:

Вам нужно создать следующие файлы в папке `Front/public/`:

1. **pwa-64x64.png** - 64×64 пикселя
2. **pwa-192x192.png** - 192×192 пикселя
3. **pwa-512x512.png** - 512×512 пикселя
4. **maskable-icon-512x512.png** - 512×512 пикселя (с безопасной зоной)
5. **apple-touch-icon.png** - 180×180 пикселя (для iOS)
6. **favicon-32x32.png** - 32×32 пикселя
7. **favicon-16x16.png** - 16×16 пикселя
8. **masked-icon.svg** - векторная иконка для Safari

### Способы создания иконок:

#### Вариант 1: Онлайн генераторы
- **PWA Asset Generator**: https://www.pwabuilder.com/imageGenerator
- **Favicon.io**: https://favicon.io/
- **RealFaviconGenerator**: https://realfavicongenerator.net/

#### Вариант 2: Использование утилит
```bash
# Установка утилиты для генерации иконок
npm install -g pwa-asset-generator

# Генерация всех иконок из одного изображения
pwa-asset-generator logo.png ./public --icon-only --favicon
```

#### Вариант 3: Ручное создание в графическом редакторе
- Используйте Figma, Photoshop, или GIMP
- Создайте квадратное изображение 512×512px
- Экспортируйте в нужных размерах

### Рекомендации по дизайну иконок:

1. **Основная иконка (512×512)**: 
   - Используйте простой, узнаваемый дизайн
   - Минимум текста или его отсутствие
   - Высокая контрастность

2. **Maskable иконка (512×512)**:
   - Важные элементы располагайте в центре (безопасная зона 80%)
   - Фон должен быть сплошным цветом
   - Проверьте на https://maskable.app/

3. **Apple Touch Icon (180×180)**:
   - iOS автоматически добавит скругление
   - Не добавляйте прозрачность

## 📦 Установка зависимостей

```bash
cd Front
npm install
```

## 🚀 Сборка для production

```bash
cd Front
npm run build
```

Результат будет в папке `Front/dist/`

## 🔧 Важные файлы PWA (автоматически генерируются)

После сборки `vite-plugin-pwa` автоматически создаст:
- `dist/manifest.webmanifest` - манифест PWA
- `dist/sw.js` - Service Worker
- `dist/workbox-*.js` - Workbox runtime

## 📱 Тестирование PWA локально

1. Соберите проект:
```bash
npm run build
```

2. Запустите preview с HTTPS:
```bash
npx serve dist -l 443 --ssl-cert cert.pem --ssl-key key.pem
```

3. Откройте в Chrome DevTools:
   - Application → Manifest
   - Application → Service Workers
   - Lighthouse → Generate Report → PWA

## ✅ Чеклист для PWA

- [ ] Все иконки созданы и размещены в `/public`
- [ ] Проект собран через `npm run build`
- [ ] Настроен HTTPS (обязательно!)
- [ ] Service Worker зарегистрирован
- [ ] Манифест загружается корректно
- [ ] Lighthouse PWA score > 90

## 🐛 Отладка

### Service Worker не регистрируется:
- Проверьте консоль браузера
- Убедитесь, что используется HTTPS (или localhost)
- Проверьте в DevTools → Application → Service Workers

### Иконки не отображаются:
- Проверьте пути в манифесте
- Убедитесь, что файлы существуют в `/dist`
- Очистите кэш браузера

### PWA не предлагает установку:
- Проверьте все критерии PWA в Lighthouse
- Убедитесь в наличии HTTPS
- Проверьте манифест на корректность

## 📚 Полезные ссылки

- [Vite PWA Plugin Docs](https://vite-pwa-org.netlify.app/)
- [Web.dev PWA Guide](https://web.dev/progressive-web-apps/)
- [PWA Builder](https://www.pwabuilder.com/)
- [Workbox Documentation](https://developer.chrome.com/docs/workbox/)

