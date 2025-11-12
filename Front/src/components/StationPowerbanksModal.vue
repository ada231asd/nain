<template>
  <div v-if="isVisible" class="modal-overlay" @click="$emit('close')">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <div class="header-info">
          <h3>Станция {{ station?.box_id || station?.station_id || '' }}</h3>
          <p class="station-subtitle">Управление аккумуляторами</p>
        </div>
        <button class="btn-close" @click="$emit('close')">&times;</button>
      </div>

      <div class="modal-body">
        
        <div class="table-wrapper">
          <table class="pb-table">
            <thead>
              <tr>
                <th>Слот</th>
                <th>Терминал ID</th>
                <th>Заряд</th>
                <th>SOH</th>
                <th>Статус</th>
                <th>Действие</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(pb, idx) in powerbanks"
                :key="pb.id || pb.terminal_id || idx"
                :class="getRowClass(pb)"
                :data-terminal="getPowerbankIdentifier(pb)"
                :data-slot="pb.slot_number || idx + 1"
              >
                <td class="slot-number">{{ pb.slot_number || idx + 1 }}</td>
                <td class="battery-id">{{ formatDisplayId(pb.terminal_id || pb.powerbank_serial || pb.serial_number || '-') }}</td>
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
                <td colspan="6" class="empty">Нет данных об аккумуляторах</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, watch, nextTick } from 'vue'

const props = defineProps({
  isVisible: { type: Boolean, default: false },
  station: { type: Object, default: null },
  powerbanks: { type: Array, default: () => [] },
  isBorrowing: { type: Boolean, default: false },
  highlightedPowerbankId: { type: [String, Number], default: null },
  highlightedSlotNumber: { type: [String, Number], default: null }
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

const isLikelyHex = (value) => {
  if (value == null) return false
  const s = String(value).trim()
  if (s.length < 4 || s.length % 2 !== 0) return false
  return /^[0-9a-fA-F]+$/.test(s)
}

const decodeHexAscii = (hex) => {
  try {
    const bytes = hex.match(/.{1,2}/g) || []
    const chars = bytes.map(b => String.fromCharCode(parseInt(b, 16)))
    const ascii = chars.join('')
    // Убираем нули и непечатаемые
    const cleaned = ascii.replace(/\x00+/g, '').replace(/[^\x20-\x7E]/g, '')
    return cleaned
  } catch {
    return null
  }
}

const formatHybridId = (hex) => {
  const s = String(hex).toUpperCase()
  if (s.length < 8 || s.length % 2 !== 0) return null
  const prefixHex = s.slice(0, 8)
  const restHex = s.slice(8)
  try {
    const prefixBytes = prefixHex.match(/.{1,2}/g) || []
    const prefixAscii = prefixBytes.map(b => String.fromCharCode(parseInt(b, 16))).join('')
    if (/^[A-Za-z0-9]{4}$/.test(prefixAscii)) {
      return prefixAscii + restHex
    }
  } catch {}
  return null
}

const formatDisplayId = (value) => {
  if (value == null || value === '') return '-'
  const raw = String(value).trim()
  if (isLikelyHex(raw)) {
    const hybrid = formatHybridId(raw)
    if (hybrid) return hybrid
    const decoded = decodeHexAscii(raw)
    if (decoded && decoded.length >= 4) {
      return decoded
    }
  }
  return raw
}

const getPowerbankIdentifier = (pb) => {
  if (!pb) return ''
  return pb.terminal_id || pb.powerbank_serial || pb.serial_number || pb.id || ''
}

const isPowerbankHighlighted = (pb) => {
  if (!pb) return false
  const targetTerminal = props.highlightedPowerbankId
  const targetSlot = props.highlightedSlotNumber

  if (targetTerminal === null && targetSlot === null) {
    return false
  }

  const identifier = getPowerbankIdentifier(pb)
  const slotValue = pb.slot_number ?? null

  const matchesTerminal = targetTerminal !== null && identifier !== '' && String(identifier) === String(targetTerminal)
  const matchesSlot = targetSlot !== null && slotValue !== null && String(slotValue) === String(targetSlot)

  return matchesTerminal || matchesSlot
}

const getBatteryStatusClass = (pb) => {
  // Ошибочный, если есть флаги ошибок слота или статус powerbank не 'active'
  const slotError = pb.error_typec || pb.error_lightning || pb.error_microusb || pb.powerbank_error || pb.has_errors
  const isBrokenStatus = pb.powerbank_status === 'system_error' || pb.powerbank_status === 'written_off' || pb.powerbank_status === 'user_reported_broken'
  return (slotError || isBrokenStatus) ? 'status-error' : 'status-ok'
}

const getBatteryStatusText = (pb) => {
  const slotError = pb.error_typec || pb.error_lightning || pb.error_microusb || pb.powerbank_error || pb.has_errors
  if (slotError) return 'ERROR'
  if (pb.powerbank_status === 'system_error' || pb.powerbank_status === 'user_reported_broken') return 'BROKEN'
  if (pb.powerbank_status === 'written_off') return 'WRITTEN OFF'
  return 'NORMAL'
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
  // Нельзя выдавать, если статус не active или есть ошибки
  const slotError = pb.error_typec || pb.error_lightning || pb.error_microusb || pb.powerbank_error || pb.has_errors
  const notActive = pb.powerbank_status && pb.powerbank_status !== 'active'
  const hasMinCharge = pb.level >= 20
  return !slotError && !notActive && hasMinCharge
}

const getBorrowButtonTitle = (pb) => {
  if (!canBorrowPowerbank(pb)) {
    const reasons = []
    if (pb.powerbank_status && pb.powerbank_status !== 'active') {
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
  const slotError = pb.error_typec || pb.error_lightning || pb.error_microusb || pb.powerbank_error || pb.has_errors
  const broken = pb.powerbank_status && pb.powerbank_status !== 'active'
  const isAvailable = canBorrowPowerbank(pb)

  const classes = []

  if (slotError || broken) {
    classes.push('row-error')
  } else if (isAvailable) {
    classes.push('row-available')
  } else {
    classes.push('row-unavailable')
  }

  if (isPowerbankHighlighted(pb)) {
    classes.push('row-highlight')
  }

  return classes.join(' ')
}

const scrollHighlightedIntoView = async () => {
  if (!props.isVisible) return
  if (props.highlightedPowerbankId === null && props.highlightedSlotNumber === null) return
  if (typeof window === 'undefined') return

  await nextTick()

  const rows = document.querySelectorAll('.pb-table tbody tr')
  const targetTerminal = props.highlightedPowerbankId !== null ? String(props.highlightedPowerbankId) : null
  const targetSlot = props.highlightedSlotNumber !== null ? String(props.highlightedSlotNumber) : null

  for (const row of rows) {
    const rowTerminal = row.getAttribute('data-terminal')
    const rowSlot = row.getAttribute('data-slot')
    const matchesTerminal = targetTerminal && rowTerminal === targetTerminal
    const matchesSlot = targetSlot && rowSlot === targetSlot

    if (matchesTerminal || matchesSlot) {
      row.scrollIntoView({ block: 'center', behavior: 'smooth' })
      row.classList.add('row-highlight-active')
      if (row.dataset.highlightTimeout) {
        window.clearTimeout(Number(row.dataset.highlightTimeout))
      }
      const timeoutId = window.setTimeout(() => {
        row.classList.remove('row-highlight-active')
        delete row.dataset.highlightTimeout
      }, 1600)
      row.dataset.highlightTimeout = String(timeoutId)
      break
    }
  }
}

watch(
  () => [props.isVisible, props.powerbanks, props.highlightedPowerbankId, props.highlightedSlotNumber],
  () => {
    if (!props.isVisible) return
    scrollHighlightedIntoView()
  }
)
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

.pb-table tbody tr.row-highlight {
  box-shadow: inset 0 0 0 2px rgba(13, 110, 253, 0.4);
  position: relative;
}

.pb-table tbody tr.row-highlight-active {
  animation: highlight-pulse 1.2s ease-out;
}

@keyframes highlight-pulse {
  0% {
    box-shadow: inset 0 0 0 0 rgba(13, 110, 253, 0.6);
  }
  50% {
    box-shadow: inset 0 0 0 4px rgba(13, 110, 253, 0.35);
  }
  100% {
    box-shadow: inset 0 0 0 2px rgba(13, 110, 253, 0.25);
  }
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

