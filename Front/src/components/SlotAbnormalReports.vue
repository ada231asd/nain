<template>
  <div class="slot-abnormal-reports">
    <div class="reports-header">
      <h3>Отчеты об аномалиях слотов</h3>
      <div class="reports-controls">
        <select v-model="selectedStation" @change="loadReports" class="form-select">
          <option value="">Все станции</option>
          <option v-for="station in stations" :key="station.station_id" :value="station.station_id">
            {{ station.box_id }} ({{ station.org_unit_name || 'Без группы' }})
          </option>
        </select>
        <button @click="loadReports" class="btn btn-primary">Обновить</button>
      </div>
    </div>

    <!-- Массовые действия -->
    <div v-if="reports.length > 0" class="bulk-actions">
      <div class="bulk-controls">
        <label class="checkbox-container">
          <input 
            type="checkbox" 
            :checked="isAllSelected" 
            @change="toggleSelectAll"
          >
          <span class="checkmark"></span>
          Выбрать все ({{ selectedReports.length }}/{{ reports.length }})
        </label>
        
        <div class="bulk-buttons" v-if="selectedReports.length > 0">
          <button 
            @click="deleteSelected" 
            class="btn btn-danger"
            :disabled="selectedReports.length === 0"
          >
            🗑️ Удалить выбранные ({{ selectedReports.length }})
          </button>
          <button 
            @click="clearSelection" 
            class="btn btn-secondary"
          >
            Очистить выбор
          </button>
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading">
      Загрузка отчетов...
    </div>

    <div v-else-if="reports.length === 0" class="empty-state">
      <p>Отчеты об аномалиях не найдены</p>
    </div>

    <div v-else class="reports-list">
      <div class="reports-stats" v-if="statistics">
        <div class="stat-item">
          <span class="stat-label">Всего отчетов:</span>
          <span class="stat-value">{{ statistics.total_reports }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">За сегодня:</span>
          <span class="stat-value">{{ statistics.reports_today }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">За неделю:</span>
          <span class="stat-value">{{ statistics.reports_week }}</span>
        </div>
      </div>

      <div class="reports-table">
        <table>
          <thead>
            <tr>
              <th class="col-checkbox">
                <input 
                  type="checkbox" 
                  :checked="isAllSelected" 
                  @change="toggleSelectAll"
                  class="header-checkbox"
                >
              </th>
              <th>ID</th>
              <th>Станция</th>
              <th>Слот</th>
              <th>Описание</th>
              <th>Время события</th>
              <th>Действия</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="report in reports" :key="report.report_id" class="report-row" :class="{ selected: selectedReports.includes(report.report_id) }">
              <td class="col-checkbox">
                <input 
                  type="checkbox" 
                  :checked="selectedReports.includes(report.report_id)"
                  @change="toggleReportSelection(report.report_id)"
                  class="row-checkbox"
                >
              </td>
              <td>{{ report.report_id }}</td>
              <td>
                <div class="station-info">
                  <span class="station-name">{{ report.box_id || `ID: ${report.station_id}` }}</span>
                  <span v-if="getStationOrgUnit(report.station_id)" class="station-org">
                    ({{ getStationOrgUnit(report.station_id) }})
                  </span>
                </div>
              </td>
              <td>{{ report.slot_number }}</td>
              <td class="event-text">
                <span>{{ getEventTypeText(report.event_type) }}</span>
              </td>
              <td>
                <div class="time-info">
                  <span v-if="report.reported_at">{{ formatMoscowTime(report.reported_at) }}</span>
                  <span v-else class="text-muted">-</span>
                  <span v-if="report.reported_at" class="relative-time">{{ getRelativeTime(report.reported_at) }}</span>
                </div>
              </td>
              <td>
                <button 
                  @click="deleteReport(report.report_id)" 
                  class="btn btn-danger btn-sm"
                  title="Удалить отчет"
                >
                  🗑️
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="pagination" v-if="totalPages > 1">
        <button 
          @click="changePage(currentPage - 1)" 
          :disabled="currentPage <= 1"
          class="btn btn-secondary"
        >
          ←
        </button>
        <span class="page-info">
          Страница {{ currentPage }} из {{ totalPages }}
        </span>
        <button 
          @click="changePage(currentPage + 1)" 
          :disabled="currentPage >= totalPages"
          class="btn btn-secondary"
        >
          →
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, inject, watch } from 'vue'
import { pythonAPI } from '../api/pythonApi'
import { formatMoscowTime, getRelativeTime } from '../utils/timeUtils'
import websocketClient from '../utils/websocketClient'

const props = defineProps({
  stations: {
    type: Array,
    default: () => []
  },
  activeTab: {
    type: String,
    default: ''
  }
})

const loading = ref(false)
const reports = ref([])
const statistics = ref(null)
const selectedStation = ref('')
const currentPage = ref(1)
const limit = 20
const selectedReports = ref([])

// Маппинг типов событий (соответствует packet_utils.py строки 612-616)
const eventTypeMap = {
  1: "No unlock command",
  2: "Return detected but no power bank"
}

const totalPages = computed(() => {
  return Math.ceil(reports.value.length / limit)
})

const paginatedReports = computed(() => {
  const start = (currentPage.value - 1) * limit
  const end = start + limit
  return reports.value.slice(start, end)
})

const isAllSelected = computed(() => {
  return reports.value.length > 0 && selectedReports.value.length === reports.value.length
})

onMounted(() => {
  loadReports()
  loadStatistics()
  setupWebSocket()
})

onUnmounted(() => {
  // Отключаем WebSocket при размонтировании компонента
  websocketClient.disconnect()
})

// Отслеживаем изменение активной вкладки
watch(() => props.activeTab, (newTab, oldTab) => {
  // Если уходим с вкладки аномалий слотов, отключаем WebSocket
  if (oldTab === 'slot-abnormal-reports' && newTab !== 'slot-abnormal-reports') {
    websocketClient.disconnect()
    console.log('WebSocket отключен при уходе с раздела аномалий слотов')
  }
  // Если заходим на вкладку аномалий слотов, подключаем WebSocket
  else if (newTab === 'slot-abnormal-reports' && oldTab !== 'slot-abnormal-reports') {
    setupWebSocket()
    console.log('WebSocket подключен при входе в раздел аномалий слотов')
  }
})

const loadReports = async () => {
  loading.value = true
  try {
    let response
    
    if (selectedStation.value) {
      response = await pythonAPI.getStationSlotAbnormalReports(selectedStation.value, 100)
    } else {
      response = await pythonAPI.getSlotAbnormalReports({ limit: 100 })
    }
    
    if (response.success) {
      reports.value = response.reports || []
    } else {
      console.error('Ошибка загрузки отчетов:', response.message)
    }
  } catch (error) {
    console.error('Ошибка загрузки отчетов:', error)
  } finally {
    loading.value = false
  }
}

const loadStatistics = async () => {
  try {
    const response = await pythonAPI.getSlotAbnormalReportsStatistics()
    if (response.success) {
      statistics.value = response.statistics
    }
  } catch (error) {
    console.error('Ошибка загрузки статистики:', error)
  }
}

const deleteReport = async (reportId) => {
  if (!confirm('Вы уверены, что хотите удалить этот отчет?')) {
    return
  }
  
  loading.value = true
  try {
    const response = await pythonAPI.deleteSlotAbnormalReport(reportId)
    if (response.success) {
      // Перезагружаем данные с сервера
      await loadReports()
      await loadStatistics()
      
      alert('Отчет удален успешно')
    } else {
      alert('Ошибка удаления отчета: ' + response.message)
    }
  } catch (error) {
    console.error('Ошибка удаления отчета:', error)
    alert('Ошибка удаления отчета: ' + error.message)
  } finally {
    loading.value = false
  }
}

const getEventTypeClass = (eventType) => {
  const type = eventType?.toLowerCase() || ''
  if (type.includes('error') || type.includes('ошибка')) return 'event-error'
  if (type.includes('warning') || type.includes('предупреждение')) return 'event-warning'
  if (type.includes('info') || type.includes('информация')) return 'event-info'
  return 'event-default'
}

// Методы для работы с чекбоксами
const toggleSelectAll = () => {
  if (isAllSelected.value) {
    selectedReports.value = []
  } else {
    selectedReports.value = reports.value.map(r => r.report_id)
  }
}

const toggleReportSelection = (reportId) => {
  const index = selectedReports.value.indexOf(reportId)
  if (index > -1) {
    selectedReports.value.splice(index, 1)
  } else {
    selectedReports.value.push(reportId)
  }
}

const clearSelection = () => {
  selectedReports.value = []
}

const deleteSelected = async () => {
  if (selectedReports.value.length === 0) return
  
  if (!confirm(`Вы уверены, что хотите удалить ${selectedReports.value.length} выбранных отчетов?`)) {
    return
  }
  
  loading.value = true
  try {
    // Удаляем по одному (можно оптимизировать, добавив bulk delete API)
    for (const reportId of selectedReports.value) {
      const response = await pythonAPI.deleteSlotAbnormalReport(reportId)
      if (!response.success) {
        console.error(`Ошибка удаления отчета ${reportId}:`, response.message)
      }
    }
    
    // Очищаем выбранные отчеты
    selectedReports.value = []
    
    // Перезагружаем данные с сервера
    await loadReports()
    await loadStatistics()
    
    alert('Выбранные отчеты удалены успешно')
  } catch (error) {
    console.error('Ошибка удаления выбранных отчетов:', error)
    alert('Ошибка удаления выбранных отчетов: ' + error.message)
  } finally {
    loading.value = false
  }
}

// Получение текста типа события
const getEventTypeText = (eventType) => {
  return eventTypeMap[eventType] || `Неизвестный тип (${eventType})`
}

const changePage = (page) => {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page
  }
}

// WebSocket методы
const setupWebSocket = async () => {
  // Проверяем, нужно ли подключаться
  if (!websocketClient.shouldConnect()) {
    console.log('WebSocket уже подключен или подключается')
    return
  }

  // Подписываемся на события
  websocketClient.on('new_abnormal_report', (reportData) => {
    // Добавляем новый отчет в начало списка
    reports.value.unshift(reportData)
    
    // Показываем уведомление
    showNewReportNotification(reportData)
    
    // Обновляем статистику
    loadStatistics()
  })
  
  websocketClient.on('recent_reports', (data) => {
    if (data.success) {
      reports.value = data.reports || []
    }
  })
  
  websocketClient.on('abnormal_report_deleted', (data) => {
    // Удаляем отчет из локального списка
    reports.value = reports.value.filter(r => r.report_id !== data.report_id)
    console.log(`Отчет ${data.report_id} удален другим пользователем`)
  })
  
  // Подключаемся к WebSocket
  websocketClient.connect()
  
  // Ждем подключения и запрашиваем последние отчеты
  try {
    await websocketClient.waitForConnection()
    websocketClient.getRecentReports(100)
  } catch (error) {
    console.warn('WebSocket недоступен, работаем без real-time обновлений:', error.message)
    // Загружаем данные обычным способом, если WebSocket недоступен
    loadReports()
  }
}

const showNewReportNotification = (reportData) => {
  // Простое уведомление в консоли (можно заменить на toast)
  const stationInfo = reportData.box_id || `ID: ${reportData.station_id}`
  const orgUnit = getStationOrgUnit(reportData.station_id)
  const stationDisplay = orgUnit ? `${stationInfo} (${orgUnit})` : stationInfo
  const eventText = getEventTypeText(reportData.event_type)
  console.log(`🔔 Новая аномалия слота: ${stationDisplay}, слот ${reportData.slot_number}, ${eventText}`)
  
  // Можно добавить toast уведомление здесь
  // toast.info(`Новая аномалия: ${stationDisplay}, слот ${reportData.slot_number}`)
}

// Получение информации о станции
const getStationOrgUnit = (stationId) => {
  const station = props.stations.find(s => s.station_id === stationId)
  return station?.org_unit_name || null
}
</script>

<style scoped>
.slot-abnormal-reports {
  padding: 20px;
}

.reports-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 10px;
}

.reports-controls {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.form-select {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: white;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.btn-primary {
  background: #007bff;
  color: white;
}

.btn-danger {
  background: #dc3545;
  color: white;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-sm {
  padding: 4px 8px;
  font-size: 12px;
}

.loading, .empty-state {
  text-align: center;
  padding: 40px;
  color: #666;
}

.reports-stats {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
  padding: 15px;
  background: #f8f9fa;
  border-radius: 4px;
  flex-wrap: wrap;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-size: 12px;
  color: #666;
}

.stat-value {
  font-size: 18px;
  font-weight: bold;
  color: #333;
}

.reports-table {
  overflow-x: auto;
  margin-bottom: 20px;
}

table {
  width: 100%;
  border-collapse: collapse;
  background: white;
  border-radius: 4px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

th, td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

th {
  background: #f8f9fa;
  font-weight: 600;
  color: #333;
}

.report-row:hover {
  background: #f8f9fa;
}

.event-type {
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.event-error {
  background: #f8d7da;
  color: #721c24;
}

.event-warning {
  background: #fff3cd;
  color: #856404;
}

.event-info {
  background: #d1ecf1;
  color: #0c5460;
}

.event-default {
  background: #e2e3e5;
  color: #383d41;
}

.event-text {
  max-width: 200px;
  word-wrap: break-word;
}

.station-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.station-name {
  font-weight: 600;
  color: #333;
}

.station-org {
  font-size: 12px;
  color: #666;
  font-style: italic;
}

.text-muted {
  color: #6c757d;
  font-style: italic;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 10px;
}

.page-info {
  padding: 0 10px;
  color: #666;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Стили для массовых действий */
.bulk-actions {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 20px;
  border: 1px solid #e9ecef;
}

.bulk-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 15px;
}

.bulk-buttons {
  display: flex;
  gap: 10px;
  align-items: center;
}

/* Стили для чекбоксов */
.checkbox-container {
  display: flex;
  align-items: center;
  cursor: pointer;
  font-weight: 500;
  color: #333;
}

.checkbox-container input[type="checkbox"] {
  display: none;
}

.checkmark {
  width: 20px;
  height: 20px;
  border: 2px solid #ddd;
  border-radius: 4px;
  margin-right: 8px;
  position: relative;
  background: white;
  transition: all 0.2s ease;
}

.checkbox-container input[type="checkbox"]:checked + .checkmark {
  background: #007bff;
  border-color: #007bff;
}

.checkbox-container input[type="checkbox"]:checked + .checkmark::after {
  content: '✓';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: white;
  font-weight: bold;
  font-size: 12px;
}

.header-checkbox, .row-checkbox {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.col-checkbox {
  width: 50px;
  text-align: center;
  padding: 8px !important;
}

.report-row.selected {
  background-color: #e3f2fd !important;
}

.report-row.selected:hover {
  background-color: #bbdefb !important;
}

/* Стили для времени */
.time-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.relative-time {
  font-size: 12px;
  color: #666;
  font-style: italic;
}


@media (max-width: 768px) {
  .reports-header {
    flex-direction: column;
    align-items: stretch;
  }
  
  .reports-controls {
    justify-content: center;
  }
  
  .reports-stats {
    flex-direction: column;
    gap: 10px;
  }
  
  .stat-item {
    flex-direction: row;
    justify-content: space-between;
  }
  
}
</style>
