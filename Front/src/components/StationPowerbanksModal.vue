<template>
  <div v-if="isVisible" class="modal-overlay" @click="$emit('close')">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <div class="header-info">
          <h3>Станция {{ station?.box_id || station?.station_id || '' }}</h3>
          <p class="station-subtitle">Управление павербанками</p>
        </div>
        <button class="btn-close" @click="$emit('close')">&times;</button>
      </div>

      <div class="modal-body">
        
        <div class="table-wrapper">
          <table class="pb-table">
            <thead>
              <tr>
                <th>Слот</th>
                <th>ID батареи</th>
                <th>Заряд</th>
                <th>SOH</th>
                <th>Статус</th>
                <th>Действие</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(pb, idx) in powerbanks" :key="pb.id || pb.terminal_id || idx" :class="getRowClass(pb)">
                <td class="slot-number">{{ pb.slot_number || idx + 1 }}</td>
                <td class="battery-id">{{ pb.serial_number || '-' }}</td>
                <td class="battery-level">
                  <div class="level-container">
                    <span :class="getBatteryLevelClass(pb.level)">
                      {{ pb.level ?? '-' }}%
                    </span>
                    <div v-if="pb.level !== null && pb.level !== undefined" class="level-bar">
                      <div class="level-fill" :style="{ width: pb.level + '%' }" :class="getBatteryLevelClass(pb.level)"></div>
                    </div>
                  </div>
                </td>
                <td class="soh">{{ pb.soh ?? pb.SOH ?? '-' }}%</td>
                <td class="status-cell">
                  <span :class="['status-badge', getBatteryStatusClass(pb)]">
                    {{ getBatteryStatusText(pb) }}
                  </span>
                </td>
                <td class="action-cell">
                  <div class="action-buttons">
                    <button
                      class="btn-take"
                      @click="$emit('borrow-powerbank', pb)"
                      :disabled="isBorrowing || !canBorrowPowerbank(pb)"
                      :title="getBorrowButtonTitle(pb)"
                    >
                      <span v-if="isBorrowing">⏳</span>
                      <span v-else-if="canBorrowPowerbank(pb)">🔋 Взять</span>
                      <span v-else>❌</span>
                    </button>
                    <button
                      class="btn-force-eject"
                      @click="$emit('force-eject-powerbank', pb)"
                      :disabled="isBorrowing"
                      title="Принудительно извлечь повербанк"
                    >
                      ⚡ Извлечь
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-if="!powerbanks || powerbanks.length === 0">
                <td colspan="6" class="empty">Нет данных о павербанках</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  isVisible: { type: Boolean, default: false },
  station: { type: Object, default: null },
  powerbanks: { type: Array, default: () => [] },
  isBorrowing: { type: Boolean, default: false }
})

const availablePowerbanks = computed(() => {
  return props.powerbanks.filter(pb => canBorrowPowerbank(pb)).length
})

const errorPowerbanks = computed(() => {
  return props.powerbanks.filter(pb => {
    const hasError = pb.error_typec || pb.error_lightning || pb.error_microusb || pb.powerbank_error || pb.has_errors
    return hasError
  }).length
})

const getBatteryStatusClass = (pb) => {
  const hasError = pb.error_typec || pb.error_lightning || pb.error_microusb || pb.powerbank_error || pb.has_errors
  return hasError ? 'status-error' : 'status-ok'
}

const getBatteryStatusText = (pb) => {
  const hasError = pb.error_typec || pb.error_lightning || pb.error_microusb || pb.powerbank_error || pb.has_errors
  return hasError ? 'Error' : 'Normal'
}

const getSlotStatusClass = (pb) => {
  // If station exposes separate statuses, map them; otherwise mirror battery status
  return getBatteryStatusClass(pb)
}

const getSlotStatusText = (pb) => {
  return getBatteryStatusText(pb)
}

const getBatteryLevelClass = (level) => {
  if (level === null || level === undefined) return 'level-unknown'
  if (level >= 80) return 'level-high'
  if (level >= 50) return 'level-medium'
  if (level >= 20) return 'level-low'
  return 'level-critical'
}

const canBorrowPowerbank = (pb) => {
  // Проверяем, можно ли выдать повербанк
  const hasError = pb.error_typec || pb.error_lightning || pb.error_microusb || pb.powerbank_error || pb.has_errors
  const isActive = pb.powerbank_status === 'active' || pb.status === 'active' || !hasError
  const hasMinCharge = pb.level >= 20
  
  return isActive && !hasError && hasMinCharge
}

const getBorrowButtonTitle = (pb) => {
  if (!canBorrowPowerbank(pb)) {
    const reasons = []
    if (pb.powerbank_status !== 'active' && pb.status !== 'active' && pb.has_errors) {
      reasons.push('неактивен')
    }
    if (pb.error_typec || pb.error_lightning || pb.error_microusb || pb.powerbank_error || pb.has_errors) {
      reasons.push('ошибка')
    }
    if (pb.level < 20) {
      reasons.push('низкий заряд')
    }
    return `Нельзя выдать: ${reasons.join(', ')}`
  }
  return 'Выдать повербанк'
}

const getRowClass = (pb) => {
  const hasError = pb.error_typec || pb.error_lightning || pb.error_microusb || pb.powerbank_error || pb.has_errors
  const isAvailable = canBorrowPowerbank(pb)
  
  if (hasError) return 'row-error'
  if (isAvailable) return 'row-available'
  return 'row-unavailable'
}
</script>

<style scoped>
.modal-overlay { 
  position: fixed; 
  inset: 0; 
  background: rgba(0,0,0,0.5); 
  display: flex; 
  align-items: center; 
  justify-content: center; 
  z-index: 1000; 
}

.modal-content { 
  background: #fff; 
  border-radius: 12px; 
  width: 100%; 
  max-width: 960px; 
  max-height: 80vh; 
  overflow: auto; 
  box-shadow: 0 20px 40px rgba(0,0,0,0.2); 
}

.modal-header { 
  display: flex; 
  justify-content: space-between; 
  align-items: center; 
  padding: 20px 24px; 
  border-bottom: 1px solid #e9ecef; 
  background: #f8f9fa;
}

.header-info h3 {
  margin: 0 0 4px 0;
  color: #333;
  font-size: 1.25rem;
  font-weight: 600;
}

.station-subtitle {
  margin: 0;
  color: #666;
  font-size: 14px;
}

.btn-close { 
  background: none; 
  border: none; 
  font-size: 20px; 
  color: #666; 
  cursor: pointer; 
  transition: color 0.2s ease;
}

.btn-close:hover {
  color: #333;
}

.modal-body { 
  padding: 24px; 
}

.powerbanks-summary {
  display: flex;
  gap: 24px;
  margin-bottom: 24px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

.summary-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.summary-label {
  font-size: 12px;
  color: #666;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.summary-value {
  font-size: 18px;
  font-weight: 700;
  color: #333;
}

.summary-value.available {
  color: #28a745;
}

.summary-value.error {
  color: #dc3545;
}

.table-wrapper { 
  overflow-x: auto; 
}

.pb-table { 
  width: 100%; 
  border-collapse: collapse; 
}

.pb-table th, .pb-table td { 
  padding: 12px 16px; 
  text-align: left; 
  border-bottom: 1px solid #eef0f4; 
  font-size: 14px; 
  vertical-align: middle;
}

.pb-table tbody tr {
  transition: background-color 0.2s ease;
}

.pb-table tbody tr:hover {
  background: #f8f9fa;
}

.pb-table tbody tr.row-available {
  background: rgba(40, 167, 69, 0.05);
}

.pb-table tbody tr.row-error {
  background: rgba(220, 53, 69, 0.05);
}

.pb-table tbody tr.row-unavailable {
  background: rgba(108, 117, 125, 0.05);
}

.pb-table thead th { 
  background: #f8fafc; 
  color: #54657e; 
  font-weight: 600; 
}

.status { 
  font-weight: 600; 
}

.status-ok { 
  color: #28a745; 
}

.status-error { 
  color: #dc3545; 
}

.status-badge {
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.status-badge.status-ok {
  background: #d4edda;
  color: #155724;
}

.status-badge.status-error {
  background: #f8d7da;
  color: #721c24;
}

.slot-number {
  font-weight: 700;
  color: #667eea;
  text-align: center;
  font-family: 'Courier New', monospace;
}

.battery-id {
  font-family: 'Courier New', monospace;
  font-weight: 500;
}

.level-container {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 80px;
}

.level-bar {
  height: 4px;
  background: #e9ecef;
  border-radius: 2px;
  overflow: hidden;
}

.level-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.3s ease;
}

.level-fill.level-high {
  background: #28a745;
}

.level-fill.level-medium {
  background: #ffc107;
}

.level-fill.level-low {
  background: #fd7e14;
}

.level-fill.level-critical {
  background: #dc3545;
}

.soh {
  text-align: center;
  font-weight: 600;
}

.status-cell {
  text-align: center;
}

.action-cell {
  text-align: center;
}

.action-buttons {
  display: flex;
  gap: 8px;
  justify-content: center;
  align-items: center;
}

/* Стили для уровней заряда */
.level-high {
  color: #28a745;
  font-weight: 600;
}

.level-medium {
  color: #ffc107;
  font-weight: 600;
}

.level-low {
  color: #fd7e14;
  font-weight: 600;
}

.level-critical {
  color: #dc3545;
  font-weight: 600;
}

.level-unknown {
  color: #6c757d;
}

.empty { 
  text-align: center; 
  color: #777; 
}

.btn-take {
  padding: 8px 16px;
  background: #28a745;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  transition: all 0.3s ease;
  min-width: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

.btn-take:hover:not(:disabled) {
  background: #218838;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(40, 167, 69, 0.3);
}

.btn-take:disabled {
  background: #6c757d;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.btn-force-eject {
  padding: 8px 12px;
  background: #dc3545;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  transition: all 0.3s ease;
  min-width: 70px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

.btn-force-eject:hover:not(:disabled) {
  background: #c82333;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(220, 53, 69, 0.3);
}

.btn-force-eject:disabled {
  background: #6c757d;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.btn-take:disabled:hover {
  background: #6c757d;
  transform: none;
  box-shadow: none;
}
</style>

