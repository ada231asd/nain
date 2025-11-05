#!/bin/bash

#############################################
# Скрипт автоматического деплоя PWA ЗАРЯД
# Автор: AI Assistant
# Версия: 1.0
#############################################

set -e  # Остановка при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Эмодзи для красоты
ROCKET="🚀"
CHECK="✅"
CROSS="❌"
PACKAGE="📦"
BUILD="🔨"
UPLOAD="📤"
CLEAN="🧹"
LOCK="🔒"
RELOAD="🔄"

# Функция для вывода с цветом
print_info() {
    echo -e "${BLUE}$1${NC}"
}

print_success() {
    echo -e "${GREEN}$CHECK $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}$CROSS $1${NC}"
}

print_step() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
}

#############################################
# КОНФИГУРАЦИЯ (измените под свой проект)
#############################################

# Локальные пути
LOCAL_PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOCAL_DIST_DIR="$LOCAL_PROJECT_DIR/dist"

# Серверные настройки (если деплой на удаленный сервер)
# Раскомментируйте и настройте для удаленного деплоя
# SERVER_USER="your-username"
# SERVER_HOST="your-server.com"
# SERVER_PATH="/var/www/zaryd"

# Локальные настройки (для OSPanel или локального Nginx)
LOCAL_DEPLOY_PATH="C:/OSPanel/domains/zaryd"  # Для Windows
# LOCAL_DEPLOY_PATH="/var/www/zaryd"  # Для Linux

# Создавать ли бэкап перед деплоем
CREATE_BACKUP=true
BACKUP_DIR="./backups"

# Запускать ли тесты перед сборкой (если есть)
RUN_TESTS=false

#############################################
# ПРОВЕРКИ ПЕРЕД ДЕПЛОЕМ
#############################################

print_step "$ROCKET Начало деплоя PWA ЗАРЯД"

# Проверка наличия Node.js
if ! command -v node &> /dev/null; then
    print_error "Node.js не установлен!"
    exit 1
fi
print_success "Node.js найден: $(node --version)"

# Проверка наличия npm
if ! command -v npm &> /dev/null; then
    print_error "npm не установлен!"
    exit 1
fi
print_success "npm найден: $(npm --version)"

# Проверка наличия package.json
if [ ! -f "$LOCAL_PROJECT_DIR/package.json" ]; then
    print_error "package.json не найден в $LOCAL_PROJECT_DIR"
    exit 1
fi
print_success "package.json найден"

#############################################
# ПРОВЕРКА ИКОНОК PWA
#############################################

print_step "$PACKAGE Проверка наличия иконок PWA"

REQUIRED_ICONS=(
    "pwa-64x64.png"
    "pwa-192x192.png"
    "pwa-512x512.png"
    "maskable-icon-512x512.png"
    "apple-touch-icon.png"
)

MISSING_ICONS=()
for icon in "${REQUIRED_ICONS[@]}"; do
    if [ -f "$LOCAL_PROJECT_DIR/public/$icon" ]; then
        print_success "Найдена иконка: $icon"
    else
        MISSING_ICONS+=("$icon")
        print_warning "Отсутствует иконка: $icon"
    fi
done

if [ ${#MISSING_ICONS[@]} -gt 0 ]; then
    print_warning "Некоторые иконки отсутствуют!"
    print_info "Используйте generate-placeholder-icons.html для создания иконок"
    read -p "Продолжить без всех иконок? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_error "Деплой отменен пользователем"
        exit 1
    fi
else
    print_success "Все обязательные иконки найдены"
fi

#############################################
# УСТАНОВКА ЗАВИСИМОСТЕЙ
#############################################

print_step "$PACKAGE Установка/проверка зависимостей"

cd "$LOCAL_PROJECT_DIR"

if [ ! -d "node_modules" ] || [ "package.json" -nt "node_modules" ]; then
    print_info "Установка зависимостей..."
    npm ci --production=false
    print_success "Зависимости установлены"
else
    print_success "Зависимости актуальны"
fi

#############################################
# ЗАПУСК ТЕСТОВ (ОПЦИОНАЛЬНО)
#############################################

if [ "$RUN_TESTS" = true ]; then
    print_step "🧪 Запуск тестов"
    
    if npm run test --if-present; then
        print_success "Тесты пройдены"
    else
        print_error "Тесты провалились!"
        read -p "Продолжить деплой? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

#############################################
# СОЗДАНИЕ БЭКАПА
#############################################

if [ "$CREATE_BACKUP" = true ] && [ -d "$LOCAL_DIST_DIR" ]; then
    print_step "$PACKAGE Создание бэкапа"
    
    mkdir -p "$BACKUP_DIR"
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="$BACKUP_DIR/dist_backup_$TIMESTAMP.tar.gz"
    
    tar -czf "$BACKUP_FILE" -C "$LOCAL_PROJECT_DIR" dist 2>/dev/null || true
    
    if [ -f "$BACKUP_FILE" ]; then
        print_success "Бэкап создан: $BACKUP_FILE"
        
        # Удаление старых бэкапов (старше 7 дней)
        find "$BACKUP_DIR" -name "dist_backup_*.tar.gz" -mtime +7 -delete 2>/dev/null || true
    fi
fi

#############################################
# СБОРКА ПРОЕКТА
#############################################

print_step "$BUILD Сборка проекта"

print_info "Очистка старой сборки..."
rm -rf "$LOCAL_DIST_DIR"

print_info "Запуск сборки production..."
if npm run build; then
    print_success "Проект собран успешно"
else
    print_error "Ошибка при сборке проекта!"
    exit 1
fi

# Проверка наличия dist директории
if [ ! -d "$LOCAL_DIST_DIR" ]; then
    print_error "Директория dist не была создана!"
    exit 1
fi

# Проверка основных файлов
REQUIRED_FILES=("index.html" "manifest.webmanifest")
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$LOCAL_DIST_DIR/$file" ]; then
        print_success "Файл $file создан"
    else
        print_error "Отсутствует файл: $file"
        exit 1
    fi
done

# Показать размер сборки
DIST_SIZE=$(du -sh "$LOCAL_DIST_DIR" | cut -f1)
print_success "Размер сборки: $DIST_SIZE"

#############################################
# ДЕПЛОЙ (ЛОКАЛЬНЫЙ ИЛИ УДАЛЕННЫЙ)
#############################################

print_step "$UPLOAD Развертывание приложения"

# Определяем тип деплоя
if [ -n "${SERVER_HOST:-}" ]; then
    # УДАЛЕННЫЙ ДЕПЛОЙ через rsync
    print_info "Деплой на удаленный сервер: $SERVER_USER@$SERVER_HOST"
    
    if ! command -v rsync &> /dev/null; then
        print_error "rsync не установлен!"
        exit 1
    fi
    
    # Проверка SSH соединения
    if ! ssh -q -o BatchMode=yes -o ConnectTimeout=5 "$SERVER_USER@$SERVER_HOST" exit; then
        print_error "Не удается подключиться к серверу через SSH!"
        print_info "Проверьте SSH ключи и доступ к серверу"
        exit 1
    fi
    
    # Создание директории на сервере
    ssh "$SERVER_USER@$SERVER_HOST" "mkdir -p $SERVER_PATH"
    
    # Копирование файлов
    print_info "Копирование файлов на сервер..."
    if rsync -avz --delete \
        --exclude='*.map' \
        --exclude='node_modules' \
        "$LOCAL_DIST_DIR/" "$SERVER_USER@$SERVER_HOST:$SERVER_PATH/"; then
        print_success "Файлы успешно скопированы"
    else
        print_error "Ошибка при копировании файлов!"
        exit 1
    fi
    
    # Установка прав доступа
    print_info "Установка прав доступа..."
    ssh "$SERVER_USER@$SERVER_HOST" "sudo chown -R www-data:www-data $SERVER_PATH && sudo chmod -R 755 $SERVER_PATH"
    
    # Перезагрузка Nginx
    print_info "Перезагрузка Nginx..."
    if ssh "$SERVER_USER@$SERVER_HOST" "sudo nginx -t && sudo systemctl reload nginx"; then
        print_success "Nginx перезагружен"
    else
        print_warning "Не удалось перезагрузить Nginx (возможно, нужны права sudo)"
    fi
    
    print_success "Деплой на сервер завершен!"
    
else
    # ЛОКАЛЬНЫЙ ДЕПЛОЙ (для OSPanel или локального Nginx)
    print_info "Локальный деплой в: $LOCAL_DEPLOY_PATH"
    
    # Создание директории если не существует
    mkdir -p "$LOCAL_DEPLOY_PATH"
    
    # Копирование файлов
    print_info "Копирование файлов..."
    
    # Для Windows (OSPanel) используем robocopy или cp
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        # Windows
        # Преобразуем путь для Windows
        WIN_DIST_DIR=$(cygpath -w "$LOCAL_DIST_DIR" 2>/dev/null || echo "$LOCAL_DIST_DIR")
        WIN_DEPLOY_PATH=$(cygpath -w "$LOCAL_DEPLOY_PATH" 2>/dev/null || echo "$LOCAL_DEPLOY_PATH")
        
        if command -v robocopy &> /dev/null; then
            robocopy "$WIN_DIST_DIR" "$WIN_DEPLOY_PATH" /E /PURGE /NFL /NDL /NJH /NJS || true
        else
            cp -r "$LOCAL_DIST_DIR"/* "$LOCAL_DEPLOY_PATH/"
        fi
    else
        # Linux/Mac
        rsync -a --delete "$LOCAL_DIST_DIR/" "$LOCAL_DEPLOY_PATH/"
    fi
    
    print_success "Файлы скопированы в $LOCAL_DEPLOY_PATH"
    
    # Для Linux - установка прав
    if [[ "$OSTYPE" != "msys" && "$OSTYPE" != "win32" ]]; then
        print_info "Установка прав доступа..."
        sudo chown -R www-data:www-data "$LOCAL_DEPLOY_PATH" 2>/dev/null || true
        sudo chmod -R 755 "$LOCAL_DEPLOY_PATH" 2>/dev/null || true
        
        # Перезагрузка Nginx
        if command -v nginx &> /dev/null; then
            print_info "Перезагрузка Nginx..."
            sudo nginx -t && sudo systemctl reload nginx
            print_success "Nginx перезагружен"
        fi
    fi
    
    print_success "Локальный деплой завершен!"
fi

#############################################
# ФИНАЛЬНЫЕ ПРОВЕРКИ
#############################################

print_step "$CHECK Финальные проверки"

# Проверка Service Worker
SW_FILE="$LOCAL_DIST_DIR/sw.js"
if [ -f "$SW_FILE" ]; then
    print_success "Service Worker создан: sw.js"
else
    print_warning "Service Worker не найден (может быть workbox-*.js)"
    if ls "$LOCAL_DIST_DIR"/workbox-*.js 1> /dev/null 2>&1; then
        print_success "Найдены Workbox файлы"
    fi
fi

# Проверка манифеста
MANIFEST_FILE="$LOCAL_DIST_DIR/manifest.webmanifest"
if [ -f "$MANIFEST_FILE" ]; then
    print_success "Манифест PWA создан"
    
    # Проверка валидности JSON манифеста
    if command -v jq &> /dev/null; then
        if jq empty "$MANIFEST_FILE" 2>/dev/null; then
            print_success "Манифест валиден"
        else
            print_warning "Манифест может содержать ошибки"
        fi
    fi
fi

#############################################
# ИТОГИ ДЕПЛОЯ
#############################################

print_step "$ROCKET ДЕПЛОЙ ЗАВЕРШЕН УСПЕШНО!"

echo ""
print_success "═══════════════════════════════════════"
print_success "  PWA приложение ЗАРЯД задеплоено!"
print_success "═══════════════════════════════════════"
echo ""

print_info "📊 Статистика деплоя:"
echo "  • Размер сборки: $DIST_SIZE"
echo "  • Время: $(date '+%Y-%m-%d %H:%M:%S')"
if [ "$CREATE_BACKUP" = true ]; then
    echo "  • Бэкап создан: $BACKUP_FILE"
fi
echo ""

print_info "📋 Следующие шаги:"
echo ""
echo "  1. Откройте приложение в браузере"
if [ -n "${SERVER_HOST:-}" ]; then
    echo "     https://your-domain.com"
else
    echo "     http://localhost или http://zaryd.local"
fi
echo ""
echo "  2. Откройте Chrome DevTools (F12)"
echo "     → Application → Manifest"
echo "     → Application → Service Workers"
echo ""
echo "  3. Запустите Lighthouse audit"
echo "     → F12 → Lighthouse → PWA"
echo "     → Цель: score > 90"
echo ""
echo "  4. Проверьте установку PWA"
echo "     → В адресной строке должна появиться иконка установки"
echo ""

print_warning "ВАЖНО: Для production обязательно используйте HTTPS!"
echo ""

print_info "📚 Документация:"
echo "  • PWA_README.md - Быстрый старт"
echo "  • DEPLOYMENT.md - Подробный деплой"
echo "  • ICONS_GUIDE.md - Создание иконок"
echo ""

print_success "Приятного использования! ⚡"

