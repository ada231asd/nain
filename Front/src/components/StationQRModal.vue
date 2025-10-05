<template>
  <div v-if="show" class="modal-overlay" @click="closeModal">
    <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>QR-код станции</h3>
          <button @click="closeModal" class="close-btn">×</button>
        </div>
      
      <div class="modal-body">
        <div v-if="qrCodeUrl" class="qr-result">
          <div class="qr-code-container">
            <img :src="qrCodeUrl" alt="QR Code" class="qr-image" />
            <div class="qr-info">
              <h4>QR-код готов!</h4>
              <p><strong>Станция:</strong> {{ station.name || station.station_name || station.box_id || `Станция ${station.station_id || station.id}` }}</p>
              <p><strong>Ссылка:</strong></p>
              <div class="url-container">
                <input 
                  :value="qrLink" 
                  readonly 
                  class="url-input"
                  @click="selectUrl"
                />
                <button @click="copyUrl" class="copy-btn">Копировать</button>
              </div>
            </div>
          </div>
          
          <div class="qr-actions">
            <button @click="downloadQR" class="download-btn">Скачать QR-код</button>
            <button @click="printQR" class="print-btn">Печать QR-кода</button>
          </div>
        </div>
        
        <div v-else class="loading">
          <div class="spinner"></div>
          <p>Генерация QR-кода...</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue';
import QRCode from 'qrcode';

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  station: {
    type: Object,
    default: null
  }
});

const emit = defineEmits(['close']);

const qrCodeUrl = ref('');
const qrLink = ref('');

const generateQRCode = async () => {
  if (!props.station) return;
  
  try {
    // Формируем ссылку используя полное имя станции
    const stationName = props.station.name || props.station.station_name || props.station.box_id || `Станция ${props.station.station_id || props.station.id}`;
    const baseUrl = window.location.origin;
    const authUrl = `${baseUrl}/${encodeURIComponent(stationName)}`;
    
    qrLink.value = authUrl;
    
    // Генерируем QR-код
    const qrCodeDataURL = await QRCode.toDataURL(authUrl, {
      width: 300,
      margin: 2,
      color: {
        dark: '#000000',
        light: '#FFFFFF'
      }
    });
    
    qrCodeUrl.value = qrCodeDataURL;
  } catch (error) {
    console.error('Ошибка генерации QR-кода:', error);
    alert('Ошибка при генерации QR-кода');
  }
};

const selectUrl = (event) => {
  event.target.select();
};

const copyUrl = async () => {
  try {
    await navigator.clipboard.writeText(qrLink.value);
    alert('Ссылка скопирована в буфер обмена');
  } catch (error) {
    console.error('Ошибка копирования:', error);
    // Fallback для старых браузеров
    const textArea = document.createElement('textarea');
    textArea.value = qrLink.value;
    document.body.appendChild(textArea);
    textArea.select();
    document.execCommand('copy');
    document.body.removeChild(textArea);
    alert('Ссылка скопирована в буфер обмена');
  }
};

const downloadQR = () => {
  if (!qrCodeUrl.value) return;
  
  const link = document.createElement('a');
  link.download = `qr-code-${props.station.station_id || props.station.id}.png`;
  link.href = qrCodeUrl.value;
  link.click();
};

const printQR = () => {
  if (!qrCodeUrl.value) return;
  
  const printWindow = window.open('', '_blank');
  printWindow.document.write(`
    <html>
      <head>
        <title>QR-код станции ${props.station.name || props.station.station_name || props.station.box_id || `Станция ${props.station.station_id || props.station.id}`}</title>
        <style>
          body { 
            font-family: Arial, sans-serif; 
            text-align: center; 
            padding: 20px;
          }
          .qr-container { 
            margin: 20px auto; 
            max-width: 400px;
          }
          .qr-image { 
            max-width: 100%; 
            height: auto; 
          }
          .station-name { 
            margin-top: 20px; 
            font-size: 18px;
            font-weight: bold;
            text-align: center;
          }
        </style>
      </head>
      <body>
        <h2>QR-код станции</h2>
        <div class="qr-container">
          <img src="${qrCodeUrl.value}" alt="QR Code" class="qr-image" />
          <div class="station-name">
            ${props.station.name || props.station.station_name || props.station.box_id || `Станция ${props.station.station_id || props.station.id}`}
          </div>
        </div>
      </body>
    </html>
  `);
  printWindow.document.close();
  printWindow.print();
};

const closeModal = () => {
  emit('close');
};

// Генерируем QR-код при открытии модального окна
watch(() => props.show, (newValue) => {
  if (newValue && props.station) {
    qrCodeUrl.value = '';
    qrLink.value = '';
    generateQRCode();
  }
});
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background-color: white;
  border-radius: 12px;
  max-width: 600px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #e5e7eb;
}

.modal-header h3 {
  margin: 0;
  color: #1e293b;
  font-size: 1.25rem;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #6b7280;
  padding: 0;
  width: 2rem;
  height: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
}

.close-btn:hover {
  background-color: #f3f4f6;
  color: #374151;
}

.modal-body {
  padding: 1.5rem;
}

.qr-result {
  text-align: center;
}

.qr-code-container {
  display: flex;
  gap: 2rem;
  align-items: flex-start;
  margin-bottom: 1.5rem;
}

.qr-image {
  width: 200px;
  height: 200px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background-color: white;
}

.qr-info {
  flex: 1;
  text-align: left;
}

.qr-info h4 {
  margin-bottom: 1rem;
  color: #1e293b;
}

.qr-info p {
  margin-bottom: 0.5rem;
  color: #64748b;
}

.url-container {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.url-input {
  flex: 1;
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  background-color: white;
  color: #1e293b;
  font-size: 0.875rem;
}

.copy-btn {
  background-color: #10b981;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: background-color 0.2s;
}

.copy-btn:hover {
  background-color: #059669;
}

.qr-actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
}

.download-btn, .print-btn {
  background-color: #6b7280;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 6px;
  font-size: 1rem;
  cursor: pointer;
  transition: background-color 0.2s;
}

.download-btn:hover, .print-btn:hover {
  background-color: #4b5563;
}

.loading {
  text-align: center;
  padding: 3rem;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #e5e7eb;
  border-top: 4px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

@media (max-width: 768px) {
  .modal-content {
    width: 95%;
    margin: 1rem;
  }
  
  .qr-code-container {
    flex-direction: column;
    align-items: center;
  }
  
  .qr-image {
    width: 150px;
    height: 150px;
  }
  
  .qr-actions {
    flex-direction: column;
  }
}
</style>
