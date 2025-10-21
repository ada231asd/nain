<template>
  <div v-if="isVisible" class="modal-overlay" @click="$emit('close')">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h3>Массовый импорт пользователей из Excel</h3>
        <button class="btn-close" @click="$emit('close')">&times;</button>
      </div>

      <div class="modal-body">
        <!-- Шаг 1: Загрузка файла -->
        <div v-if="currentStep === 1" class="import-step">
          <div class="step-header">
            <h4>📎 Шаг 1: Загрузите файл Excel</h4>
            <button @click="downloadTemplate" class="btn-template" :disabled="isLoading">
              📥 Скачать шаблон
            </button>
          </div>

          <div class="file-upload-area">
            <div
              class="file-drop-zone"
              @dragover.prevent="onDragOver"
              @dragleave.prevent="onDragLeave"
              @drop.prevent="onDrop"
              :class="{ 'drag-over': isDragOver }"
            >
              <div v-if="!selectedFile" class="file-upload-content">
                <div class="upload-icon">📄</div>
                <p>Перетащите Excel файл сюда</p>
                <p class="upload-hint">или <button class="btn-select-file" @click="fileInput && fileInput.click()">выберите файл</button></p>
                <p class="file-format">Поддерживаемые форматы: .xlsx, .xls (макс. 10MB)</p>
              </div>

              <div v-else class="file-selected">
                <div class="file-info">
                  <div class="file-icon">📄</div>
                  <div class="file-details">
                    <p class="file-name">{{ selectedFile.name }}</p>
                    <p class="file-size">{{ formatFileSize(selectedFile.size) }}</p>
                  </div>
                </div>
                <button @click="clearFile" class="btn-clear-file">✕</button>
              </div>
            </div>

            <input
              ref="setFileInputRef"
              type="file"
              accept=".xlsx,.xls"
              @change="onFileSelect"
              style="display: none"
            />
          </div>

          <!-- Выбор группы -->
          <div class="form-group">
            <label>Привязать к группе (необязательно)</label>
            <select v-model="orgUnitId" class="form-select">
              <option value="">Без группы</option>
              <option
                v-for="orgUnit in orgUnits"
                :key="orgUnit.org_unit_id"
                :value="orgUnit.org_unit_id"
              >
                {{ orgUnit.name }}
              </option>
            </select>
          </div>

          <div class="step-actions">
            <button @click="validateFile" class="btn-primary" :disabled="!selectedFile || isLoading">
              {{ isLoading ? '🔄 Проверка...' : '✅ Проверить файл' }}
            </button>
            <button @click="$emit('close')" class="btn-cancel">Отмена</button>
          </div>
        </div>

        <!-- Шаг 2: Валидация и результаты -->
        <div v-else-if="currentStep === 2" class="import-step">
          <div class="step-header">
            <h4>🔍 Шаг 2: Результаты проверки</h4>
            <button @click="currentStep = 1" class="btn-back">← Назад</button>
          </div>

          <!-- Статистика валидации -->
          <div class="validation-stats">
            <div class="stat-card" :class="{ success: validationResult.success }">
              <div class="stat-icon">{{ validationResult.success ? '✅' : '⚠️' }}</div>
              <div class="stat-info">
                <h5>{{ validationResult.message }}</h5>
                <div class="stats-grid">
                  <div class="stat-item">
                    <span class="stat-label">Всего строк:</span>
                    <span class="stat-value">{{ validationResult.statistics?.total_rows || 0 }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">Валидных:</span>
                    <span class="stat-value">{{ validationResult.statistics?.valid_users || 0 }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">Новых:</span>
                    <span class="stat-value">{{ validationResult.statistics?.new_users || 0 }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">Существующих:</span>
                    <span class="stat-value">{{ validationResult.statistics?.existing_users || 0 }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Ошибки -->
          <div v-if="validationResult.errors && validationResult.errors.length > 0" class="errors-section">
            <h5>❌ Ошибки и предупреждения:</h5>
            <div class="errors-list">
              <div
                v-for="(error, index) in validationResult.errors.slice(0, 10)"
                :key="index"
                class="error-item"
              >
                {{ error }}
              </div>
              <div v-if="validationResult.errors.length > 10" class="error-more">
                ... и еще {{ validationResult.errors.length - 10 }} ошибок
              </div>
            </div>
          </div>

          <!-- Превью пользователей -->
          <div v-if="validationResult.preview_users && validationResult.preview_users.length > 0" class="preview-section">
            <h5>👀 Превью пользователей (первые 10):</h5>
            <div class="preview-users">
              <div
                v-for="user in validationResult.preview_users"
                :key="user.row_number"
                class="preview-user-card"
              >
                <div class="user-info">
                  <strong>{{ user.fio }}</strong><br>
                  📧 {{ user.email }}<br>
                  📞 {{ user.phone_e164 }}
                </div>
                <div class="user-row">Строка {{ user.row_number }}</div>
              </div>
            </div>
          </div>

          <div class="step-actions">
            <button
              @click="importUsers"
              class="btn-primary"
              :disabled="!validationResult.success || isLoading"
            >
              {{ isLoading ? '🔄 Импорт...' : '🚀 Импортировать пользователей' }}
            </button>
            <button @click="$emit('close')" class="btn-cancel">Отмена</button>
          </div>
        </div>

        <!-- Шаг 2.5: Прогресс импорта -->
        <div v-else-if="currentStep === 2.5" class="import-step">
          <div class="step-header">
            <h4>🔄 Импорт в процессе...</h4>
          </div>

          <div class="progress-section">
            <div class="progress-bar-container">
              <div 
                class="progress-bar" 
                :style="{ width: `${importProgress.total > 0 ? (importProgress.current / importProgress.total) * 100 : 0}%` }"
              ></div>
            </div>
            
            <div class="progress-info">
              <p class="progress-counter">
                <strong>Обработано: {{ importProgress.current }} из {{ importProgress.total }}</strong>
              </p>
              
              <div v-if="importProgress.user" class="current-user">
                <p>👤 Текущий пользователь: <strong>{{ importProgress.user }}</strong></p>
                
                <p v-if="importProgress.status === 'creating'" class="status-text">
                  ⏳ Создание пользователя в базе данных...
                </p>
                <p v-else-if="importProgress.status === 'sending_email'" class="status-text">
                  📧 Отправка письма с паролем...
                </p>
                <p v-else-if="importProgress.status === 'completed'" class="status-text">
                  ✅ Пользователь создан{{ importProgress.email_sent ? ' и письмо отправлено' : '' }}
                </p>
                <p v-else-if="importProgress.status === 'error'" class="status-text error">
                  ❌ Ошибка: {{ importProgress.error }}
                </p>
              </div>
              
              <div v-else class="loading-text">
                <p>⏳ Начинаем импорт...</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Шаг 3: Результаты импорта -->
        <div v-else-if="currentStep === 3" class="import-step">
          <div class="step-header">
            <h4>🎉 Шаг 3: Результаты импорта</h4>
          </div>

          <!-- Статистика импорта -->
          <div class="import-results">
            <div class="result-card" :class="{ success: importResult.success }">
              <div class="result-icon">{{ importResult.success ? '🎉' : '❌' }}</div>
              <div class="result-info">
                <h5>{{ importResult.message }}</h5>
                <div class="stats-grid">
                  <div class="stat-item">
                    <span class="stat-label">Обработано:</span>
                    <span class="stat-value">{{ importResult.statistics?.total_parsed || 0 }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">Создано:</span>
                    <span class="stat-value success">{{ importResult.statistics?.created_users || 0 }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">Пропущено:</span>
                    <span class="stat-value warning">{{ importResult.statistics?.existing_users || 0 }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">Ошибок:</span>
                    <span class="stat-value error">{{ importResult.statistics?.errors || 0 }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Созданные пользователи -->
          <div v-if="importResult.created_users && importResult.created_users.length > 0" class="created-users-section">
            <h5>✅ Созданные пользователи:</h5>
            <div class="created-users-list">
              <div
                v-for="user in importResult.created_users"
                :key="user.user_id"
                class="created-user-item"
              >
                <div class="user-info">
                  <strong>{{ user.fio }}</strong>
                  <span class="email">{{ user.email }}</span>
                  <span class="phone">{{ user.phone_e164 }}</span>
                </div>
                <div class="user-status">
                  <span v-if="user.email_sent" class="status-sent">📧 Отправлено</span>
                  <span v-else class="status-not-sent">📧 Не отправлено</span>
                  <span class="user-password">Пароль: {{ user.password }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Ошибки импорта -->
          <div v-if="importResult.errors && importResult.errors.length > 0" class="errors-section">
            <h5>❌ Ошибки импорта:</h5>
            <div class="errors-list">
              <div
                v-for="(error, index) in importResult.errors"
                :key="index"
                class="error-item"
              >
                {{ error }}
              </div>
            </div>
          </div>

          <div class="step-actions">
            <button @click="$emit('close')" class="btn-primary">Закрыть</button>
            <button @click="resetModal" class="btn-secondary">Импортировать еще</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch, onMounted } from 'vue'
import { pythonAPI } from '../api/pythonApi.js'

const props = defineProps({
  isVisible: { type: Boolean, default: false },
  orgUnits: { type: Array, default: () => [] }
})

const emit = defineEmits(['close', 'import-completed'])

// Состояние
const currentStep = ref(1)
const isLoading = ref(false)
const selectedFile = ref(null)
const orgUnitId = ref('')
const isDragOver = ref(false)

// Template ref for hidden file input (Vue 3 script setup)
let fileInputEl = null
const setFileInputRef = (el) => { fileInputEl = el }
const fileInput = {
  click: () => { if (fileInputEl) fileInputEl.click() },
  clear: () => { if (fileInputEl) fileInputEl.value = '' }
}

const validationResult = ref({})
const importResult = ref({})

const importProgress = ref({
  current: 0,
  total: 0,
  user: '',
  status: ''
})

// Функции работы с файлами
const onDragOver = () => {
  isDragOver.value = true
}

const onDragLeave = () => {
  isDragOver.value = false
}

const onDrop = (event) => {
  isDragOver.value = false
  const files = event.dataTransfer.files
  if (files.length > 0) {
    handleFileSelect(files[0])
  }
}

const onFileSelect = (event) => {
  const file = event.target.files[0]
  if (file) {
    handleFileSelect(file)
  }
}

const handleFileSelect = (file) => {
  // Проверка типа файла
  const allowedTypes = ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-excel']
  if (!allowedTypes.includes(file.type) && !file.name.match(/\.(xlsx|xls)$/i)) {
    alert('Пожалуйста, выберите файл Excel (.xlsx или .xls)')
    return
  }

  // Проверка размера файла (10MB)
  const maxSize = 10 * 1024 * 1024
  if (file.size > maxSize) {
    alert(`Файл слишком большой. Максимальный размер: ${maxSize / (1024 * 1024)}MB`)
    return
  }

  selectedFile.value = file
}

const clearFile = () => {
  selectedFile.value = null
  fileInput.clear()
}

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// Скачивание шаблона
const downloadTemplate = async () => {
  try {
    isLoading.value = true

    const blob = await pythonAPI.downloadBulkImportTemplate()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'users_import_template.xlsx'
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)

  } catch (error) {
    console.error('Ошибка скачивания шаблона:', error)
    alert('Ошибка скачивания шаблона: ' + (error.message || 'Неизвестная ошибка'))
  } finally {
    isLoading.value = false
  }
}

// Валидация файла
const validateFile = async () => {
  if (!selectedFile.value) return

  try {
    isLoading.value = true

    const response = await pythonAPI.validateBulkImportFile(selectedFile.value)

    validationResult.value = response
    currentStep.value = 2

  } catch (error) {
    console.error('Ошибка валидации:', error)
    alert('Ошибка валидации файла: ' + (error.message || 'Неизвестная ошибка'))
  } finally {
    isLoading.value = false
  }
}


// Импорт пользователей
const importUsers = async () => {
  try {
    isLoading.value = true
    // Выполняем импорт через HTTP API
    const response = await pythonAPI.bulkImportUsers(
      selectedFile.value,
      orgUnitId.value
    )
    importResult.value = response
    currentStep.value = 3
    if (response.success) {
      emit('import-completed', response)
    }
    
  } catch (error) {
    console.error('Ошибка запуска импорта:', error)
    alert('Ошибка запуска импорта: ' + (error.message || 'Неизвестная ошибка'))
    isLoading.value = false
    currentStep.value = 1
  } finally {
    isLoading.value = false
  }
}

// Сброс модального окна
const resetModal = () => {
  currentStep.value = 1
  selectedFile.value = null
  orgUnitId.value = ''
  validationResult.value = {}
  importResult.value = {}
  importProgress.value = { current: 0, total: 0, user: '', status: '' }
  fileInput.clear()
}

// Lifecycle hooks
onMounted(() => {})

// Сброс при закрытии
watch(() => props.isVisible, (newValue) => {
  if (!newValue) {
    resetModal()
  }
})
</script>

<style scoped>
/* Общие стили модального окна */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-content {
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
  max-width: 800px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px;
  border-bottom: 1px solid #e9ecef;
}

.modal-header h3 {
  margin: 0;
  color: #333;
  font-size: 20px;
  font-weight: 600;
}

.btn-close {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #6c757d;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: background-color 0.2s;
}

.btn-close:hover {
  background: #f8f9fa;
  color: #333;
}

.modal-body {
  padding: 24px;
}

/* Шаги импорта */
.import-step {
  min-height: 400px;
}

.step-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.step-header h4 {
  margin: 0;
  color: #333;
  font-size: 18px;
}

.btn-template {
  padding: 8px 16px;
  background: #17a2b8;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.2s;
}

.btn-template:hover:not(:disabled) {
  background: #138496;
}

.btn-template:disabled {
  background: #6c757d;
  cursor: not-allowed;
}

/* Загрузка файла */
.file-upload-area {
  margin-bottom: 24px;
}

.file-drop-zone {
  border: 2px dashed #dee2e6;
  border-radius: 8px;
  padding: 40px;
  text-align: center;
  transition: all 0.3s ease;
  cursor: pointer;
  background: #f8f9fa;
}

.file-drop-zone:hover,
.file-drop-zone.drag-over {
  border-color: #667eea;
  background: #f0f2ff;
}

.upload-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.file-upload-content p {
  margin: 8px 0;
  color: #666;
}

.upload-hint {
  color: #666;
  margin: 8px 0;
}

.btn-select-file {
  background: none;
  border: none;
  color: #667eea;
  text-decoration: underline;
  cursor: pointer;
  padding: 0;
}

.btn-select-file:hover {
  color: #5a6fd8;
}

.file-format {
  font-size: 12px;
  color: #6c757d;
  margin-top: 8px;
}

.file-selected {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 16px;
}

.file-icon {
  font-size: 32px;
}

.file-details {
  text-align: left;
}

.file-name {
  margin: 0;
  font-weight: 500;
  color: #333;
}

.file-size {
  margin: 4px 0 0 0;
  font-size: 12px;
  color: #6c757d;
}

.btn-clear-file {
  background: #dc3545;
  color: white;
  border: none;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}

/* Формы */
.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-weight: 500;
  color: #333;
}

.form-select {
  width: 100%;
  padding: 10px;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  font-size: 14px;
  background: white;
}

.form-select:focus {
  outline: none;
  border-color: #667eea;
}

/* Действия шагов */
.step-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid #e9ecef;
}

.btn-primary {
  padding: 12px 24px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: background-color 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: #5a6fd8;
}

.btn-primary:disabled {
  background: #6c757d;
  cursor: not-allowed;
}

.btn-cancel {
  padding: 12px 24px;
  background: #6c757d;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.btn-cancel:hover {
  background: #5a6268;
}

.btn-back {
  padding: 8px 16px;
  background: #6c757d;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}

.btn-secondary {
  padding: 12px 24px;
  background: #28a745;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.btn-secondary:hover {
  background: #218838;
}

/* Статистика валидации */
.validation-stats,
.import-results {
  margin-bottom: 24px;
}

.stat-card,
.result-card {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 20px;
  border-left: 4px solid #6c757d;
}

.stat-card.success,
.result-card.success {
  border-left-color: #28a745;
  background: #d4edda;
}

.stat-card .stat-icon,
.result-card .result-icon {
  font-size: 32px;
  margin-bottom: 12px;
}

.stat-card h5,
.result-card h5 {
  margin: 0 0 16px 0;
  color: #333;
  font-size: 16px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
}

.stat-item,
.result-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-label,
.result-label {
  color: #666;
  font-size: 14px;
}

.stat-value,
.result-value {
  font-weight: 600;
  font-size: 16px;
}

.stat-value.success { color: #28a745; }
.stat-value.warning { color: #ffc107; }
.stat-value.error { color: #dc3545; }

/* Ошибки */
.errors-section {
  margin-bottom: 24px;
}

.errors-section h5 {
  margin: 0 0 12px 0;
  color: #dc3545;
  font-size: 16px;
}

.errors-list {
  max-height: 200px;
  overflow-y: auto;
  border: 1px solid #f5c6cb;
  border-radius: 4px;
  background: #f8d7da;
}

.error-item {
  padding: 8px 12px;
  border-bottom: 1px solid #f5c6cb;
  font-size: 14px;
  color: #721c24;
}

.error-item:last-child {
  border-bottom: none;
}

.error-more {
  padding: 8px 12px;
  background: #f5c6cb;
  color: #721c24;
  font-style: italic;
  text-align: center;
}

/* Превью пользователей */
.preview-section {
  margin-bottom: 24px;
}

.preview-section h5 {
  margin: 0 0 12px 0;
  color: #333;
  font-size: 16px;
}

.preview-users {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 12px;
  max-height: 300px;
  overflow-y: auto;
}

.preview-user-card {
  background: #f8f9fa;
  border-radius: 6px;
  padding: 12px;
  border: 1px solid #dee2e6;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.user-info {
  flex: 1;
  font-size: 14px;
  line-height: 1.4;
}

.user-row {
  font-size: 12px;
  color: #6c757d;
  background: #e9ecef;
  padding: 4px 8px;
  border-radius: 4px;
  white-space: nowrap;
}

/* Созданные пользователи */
.created-users-section {
  margin-bottom: 24px;
}

.created-users-section h5 {
  margin: 0 0 12px 0;
  color: #28a745;
  font-size: 16px;
}

.created-users-list {
  max-height: 300px;
  overflow-y: auto;
}

.created-user-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  border: 1px solid #d4edda;
  border-radius: 6px;
  background: #d4edda;
  margin-bottom: 8px;
}

.created-user-item:last-child {
  margin-bottom: 0;
}

.created-user-item .user-info {
  flex: 1;
}

.created-user-item .user-info strong {
  display: block;
  color: #155724;
  margin-bottom: 4px;
}

.created-user-item .email,
.created-user-item .phone {
  display: block;
  font-size: 12px;
  color: #155724;
  opacity: 0.8;
}

.user-status {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.status-sent {
  background: #28a745;
  color: white;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
}

.status-not-sent {
  background: #ffc107;
  color: #212529;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
}

.user-password {
  font-size: 12px;
  color: #155724;
  font-family: monospace;
  background: rgba(255, 255, 255, 0.5);
  padding: 2px 4px;
  border-radius: 3px;
}

/* Прогресс импорта */
.progress-section {
  padding: 24px;
  background: #f8f9fa;
  border-radius: 8px;
}

.progress-bar-container {
  width: 100%;
  height: 32px;
  background: #e9ecef;
  border-radius: 16px;
  overflow: hidden;
  margin-bottom: 24px;
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.1);
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  transition: width 0.5s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 600;
  font-size: 14px;
}

.progress-info {
  text-align: center;
}

.progress-counter {
  font-size: 18px;
  color: #333;
  margin: 0 0 16px 0;
}

.current-user {
  padding: 16px;
  background: white;
  border-radius: 8px;
  border-left: 4px solid #667eea;
  margin-top: 16px;
}

.current-user p {
  margin: 8px 0;
  color: #333;
  font-size: 14px;
}

.status-text {
  color: #666;
  font-size: 14px;
  margin: 8px 0;
}

.status-text.error {
  color: #dc3545;
  font-weight: 500;
}

.loading-text {
  padding: 24px;
  text-align: center;
}

.loading-text p {
  font-size: 16px;
  color: #666;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* Адаптивность */
@media (max-width: 768px) {
  .modal-content {
    min-width: 95vw;
    max-height: 95vh;
  }

  .modal-header,
  .modal-body {
    padding: 16px;
  }

  .step-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .file-drop-zone {
    padding: 24px;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .preview-users {
    grid-template-columns: 1fr;
  }

  .step-actions {
    flex-direction: column;
  }

  .step-actions button {
    width: 100%;
  }
}
</style>
