<template>
  <div class="qr-scanner-modal" @click="closeScanner">
    <div class="qr-scanner-content" @click.stop>
      <div class="scanner-header">
        <h3>Добавление станции</h3>
        <button @click="closeScanner" class="close-btn">✕</button>
      </div>
      
      <div class="scanner-body">
        <div v-if="!hasCamera" class="no-camera">
          <div class="no-camera-icon">📷</div>
          <p>Камера недоступна</p>
          <p>Введите код станции вручную</p>
        </div>
        
        <div v-else-if="isLoading" class="loading-camera">
          <div class="loading-spinner"></div>
          <p>Инициализация камеры...</p>
        </div>
        
         <div v-else class="camera-container">
           <QrcodeStream
             v-if="showCamera"
             @decode="onDecode"
             @init="onInit"
             @error="onError"
             :paused="paused"
             :track="paintBoundingBox"
             class="qr-stream"
           />
           
           <div v-if="!showCamera" class="camera-placeholder">
             <div class="camera-icon">📱</div>
             <p>Нажмите "Сканировать QR-код" для сканирования</p>
           </div>
           
           <!-- Отображение ошибок -->
           <div v-if="lastError" class="error-message">
             <p>⚠️ {{ lastError }}</p>
           </div>
         </div>
        
        <!-- Ручной ввод как fallback -->
        <div class="manual-input">
          <label for="manual-code">Или введите код вручную:</label>
          <input
            id="manual-code"
            v-model="manualCode"
            type="text"
            placeholder="Введите код станции"
            class="manual-input-field"
            @keyup.enter="handleManualSubmit"
          />
          <button 
            @click="handleManualSubmit" 
            class="manual-submit-btn"
            :disabled="!manualCode.trim()"
          >
            Добавить
          </button>
        </div>
      </div>
      
      <div class="scanner-footer">
        <button 
          v-if="!showCamera && hasCamera" 
          @click="startCamera" 
          class="btn-primary"
        >
          Сканировать QR-код
        </button>
        <button 
          v-if="showCamera" 
          @click="stopCamera" 
          class="btn-secondary"
        >
          Выключить камеру
        </button>
        <button @click="closeScanner" class="btn-cancel">
          Отмена
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { QrcodeStream } from 'vue-qrcode-reader'

const emit = defineEmits(['close', 'scan'])

// Состояние
const hasCamera = ref(false)
const isLoading = ref(false)
const showCamera = ref(false)
const paused = ref(false)
const manualCode = ref('')
const lastError = ref('')

// Проверка доступности камеры
const checkCameraAvailability = async () => {
  try {
    // Проверяем поддержку API камеры в окружении
    if (typeof navigator === 'undefined' || !navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
      console.warn('mediaDevices API недоступен в этом окружении')
      hasCamera.value = false
      lastError.value = 'Камера не поддерживается или недоступна в этом окружении'
      return
    }

    const devices = await navigator.mediaDevices.enumerateDevices()
    hasCamera.value = devices.some(device => device.kind === 'videoinput')
  } catch (error) {
    console.error('Ошибка проверки камеры:', error)
    hasCamera.value = false
  }
}

// Инициализация камеры
const onInit = async (promise) => {
  try {
    isLoading.value = true
    lastError.value = ''
    await promise
    hasCamera.value = true
  } catch (error) {
    console.error('Ошибка инициализации камеры:', error)
    lastError.value = error.message || 'Неизвестная ошибка камеры'
    hasCamera.value = false
  } finally {
    isLoading.value = false
  }
}

// Обработка ошибок камеры
const onError = (error) => {
  console.error('Ошибка QR-сканера:', error)
  lastError.value = error.message || 'Ошибка сканирования'
}

// Обработка сканирования QR-кода
const onDecode = (result) => {
  lastError.value = '' // Очищаем ошибки при успешном сканировании
  paused.value = true
  
  // Эмитим событие с результатом сканирования
  emit('scan', result)
  
  // Закрываем сканер через небольшую задержку
  setTimeout(() => {
    closeScanner()
  }, 1000)
}

// Функция для отрисовки рамки обнаружения
const paintBoundingBox = (detectedCodes, ctx) => {
  // Проверяем, что detectedCodes существует и является массивом
  if (!detectedCodes || !Array.isArray(detectedCodes)) {
    return
  }
  
  for (const detectedCode of detectedCodes) {
    if (!detectedCode || !detectedCode.location) {
      // НО! Мы все равно должны обработать этот код, даже без location
      // Попробуем вызвать onDecode для кодов без location
      if (detectedCode && detectedCode.rawValue) {
        onDecode(detectedCode.rawValue)
      }
      continue
    }
    
    const [firstPoint, ...otherPoints] = detectedCode.location
    
    ctx.strokeStyle = '#ff0000'
    ctx.lineWidth = 2
    ctx.beginPath()
    ctx.moveTo(firstPoint.x, firstPoint.y)
    for (const { x, y } of otherPoints) {
      ctx.lineTo(x, y)
    }
    ctx.lineTo(firstPoint.x, firstPoint.y)
    ctx.stroke()
  }
}

// Управление камерой
const startCamera = () => {
  // Не пытаемся запускать камеру, если API не поддерживается
  if (typeof navigator === 'undefined' || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    lastError.value = 'Невозможно включить камеру: не поддерживается в этом окружении'
    hasCamera.value = false
    return
  }

  showCamera.value = true
  paused.value = false
  lastError.value = ''
}

const stopCamera = () => {
  showCamera.value = false
  paused.value = true
}

// Обработка ручного ввода
const handleManualSubmit = () => {
  if (manualCode.value.trim()) {
    emit('scan', manualCode.value.trim())
    closeScanner()
  }
}

// Закрытие сканера
const closeScanner = () => {
  showCamera.value = false
  paused.value = true
  emit('close')
}

// Жизненный цикл
onMounted(() => {
  checkCameraAvailability()
})

onUnmounted(() => {
  stopCamera()
})
</script>

<style scoped>
.qr-scanner-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.qr-scanner-content {
  background: white;
  border-radius: 20px;
  max-width: 500px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
}

.scanner-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 30px;
  border-bottom: 1px solid #e9ecef;
}

.scanner-header h3 {
  margin: 0;
  color: #333;
  font-size: 1.3rem;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #666;
  padding: 5px;
  border-radius: 50%;
  transition: background-color 0.3s ease;
}

.close-btn:hover {
  background: #f8f9fa;
}

.scanner-body {
  padding: 30px;
}

.no-camera,
.loading-camera,
.camera-placeholder {
  text-align: center;
  padding: 40px 20px;
  background: #f8f9fa;
  border-radius: 15px;
  border: 2px dashed #dee2e6;
}

.no-camera-icon,
.camera-icon {
  font-size: 3rem;
  margin-bottom: 15px;
  display: block;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 15px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.camera-container {
  margin-bottom: 20px;
}

.qr-stream {
  width: 100%;
  height: 300px;
  border-radius: 15px;
  overflow: hidden;
  background: #000;
}

.error-message {
  margin-top: 15px;
  padding: 15px;
  background: #f8d7da;
  border: 1px solid #f5c6cb;
  border-radius: 10px;
  color: #721c24;
  text-align: center;
}

.error-message p {
  margin: 0;
  font-weight: 500;
}

.manual-input {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #e9ecef;
}

.manual-input label {
  display: block;
  margin-bottom: 10px;
  color: #666;
  font-weight: 500;
}

.manual-input-field {
  width: 100%;
  padding: 12px 15px;
  border: 2px solid #e9ecef;
  border-radius: 10px;
  font-size: 1rem;
  margin-bottom: 15px;
  transition: border-color 0.3s ease;
}

.manual-input-field:focus {
  outline: none;
  border-color: #667eea;
}

.manual-submit-btn {
  width: 100%;
  padding: 12px;
  background: #28a745;
  color: white;
  border: none;
  border-radius: 10px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.manual-submit-btn:hover:not(:disabled) {
  background: #218838;
}

.manual-submit-btn:disabled {
  background: #6c757d;
  cursor: not-allowed;
}

.scanner-footer {
  display: flex;
  gap: 15px;
  padding: 20px 30px;
  border-top: 1px solid #e9ecef;
  background: #f8f9fa;
  border-radius: 0 0 20px 20px;
}

.btn-primary {
  flex: 1;
  padding: 12px 20px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 10px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.btn-primary:hover {
  background: #5a6fd8;
}

.btn-secondary {
  flex: 1;
  padding: 12px 20px;
  background: #6c757d;
  color: white;
  border: none;
  border-radius: 10px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.btn-secondary:hover {
  background: #5a6268;
}

.btn-cancel {
  flex: 1;
  padding: 12px 20px;
  background: #dc3545;
  color: white;
  border: none;
  border-radius: 10px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.btn-cancel:hover {
  background: #c82333;
}

/* Мобильные стили */
@media (max-width: 768px) {
  .qr-scanner-content {
    margin: 10px;
    max-height: 95vh;
  }
  
  .scanner-header,
  .scanner-body,
  .scanner-footer {
    padding: 15px 20px;
  }
  
  .qr-stream {
    height: 250px;
  }
  
  .scanner-footer {
    flex-direction: column;
  }
}
</style>
