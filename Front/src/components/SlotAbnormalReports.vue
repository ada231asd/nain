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
        <select v-model="selectedEventType" @change="loadReports" class="form-select">
          <option value="">Все типы событий</option>
          <option v-for="eventType in eventTypes" :key="eventType" :value="eventType">
            {{ eventType }}
          </option>
        </select>
        <button @click="loadReports" class="btn btn-primary">Обновить</button>
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
              <th>ID</th>
              <th>Станция</th>
              <th>Слот</th>
              <th>Тип события</th>
              <th>Описание</th>
              <th>Время события</th>
              <th>Действия</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="report in reports" :key="report.report_id" class="report-row">
              <td>{{ report.report_id }}</td>
              <td>
                <span v-if="report.box_id">{{ report.box_id }}</span>
                <span v-else>ID: {{ report.station_id }}</span>
              </td>
              <td>{{ report.slot_number }}</td>
              <td>
                <span class="event-type" :class="getEventTypeClass(report.event_type)">
                  {{ report.event_type }}
                </span>
              </td>
              <td class="event-text">
                <span v-if="report.event_text">{{ report.event_text }}</span>
                <span v-else class="text-muted">-</span>
              </td>
              <td>
                <span v-if="report.reported_at">{{ formatDateTime(report.reported_at) }}</span>
                <span v-else class="text-muted">-</span>
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
import { ref, onMounted, computed } from 'vue'
import { pythonAPI } from '../api/pythonApi'

const props = defineProps({
  stations: {
    type: Array,
    default: () => []
  }
})

const loading = ref(false)
const reports = ref([])
const statistics = ref(null)
const selectedStation = ref('')
const selectedEventType = ref('')
const eventTypes = ref([])
const currentPage = ref(1)
const limit = 20

const totalPages = computed(() => {
  return Math.ceil(reports.value.length / limit)
})

const paginatedReports = computed(() => {
  const start = (currentPage.value - 1) * limit
  const end = start + limit
  return reports.value.slice(start, end)
})

onMounted(() => {
  loadReports()
  loadStatistics()
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
      
      // Извлекаем уникальные типы событий
      const types = [...new Set(reports.value.map(r => r.event_type).filter(Boolean))]
      eventTypes.value = types
      
      // Фильтруем по типу события, если выбран
      if (selectedEventType.value) {
        reports.value = reports.value.filter(r => r.event_type === selectedEventType.value)
      }
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
  
  try {
    const response = await pythonAPI.deleteSlotAbnormalReport(reportId)
    if (response.success) {
      // Удаляем из локального списка
      reports.value = reports.value.filter(r => r.report_id !== reportId)
      alert('Отчет удален успешно')
    } else {
      alert('Ошибка удаления отчета: ' + response.message)
    }
  } catch (error) {
    console.error('Ошибка удаления отчета:', error)
    alert('Ошибка удаления отчета: ' + error.message)
  }
}

const getEventTypeClass = (eventType) => {
  const type = eventType?.toLowerCase() || ''
  if (type.includes('error') || type.includes('ошибка')) return 'event-error'
  if (type.includes('warning') || type.includes('предупреждение')) return 'event-warning'
  if (type.includes('info') || type.includes('информация')) return 'event-info'
  return 'event-default'
}

const formatDateTime = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString('ru-RU')
}

const changePage = (page) => {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page
  }
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
