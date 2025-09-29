<template>
  <div v-if="isVisible" class="modal-overlay" @click="$emit('close')">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h2>{{ isEdit ? 'Редактировать станцию' : 'Добавить станцию' }}</h2>
        <button class="btn-close" @click="$emit('close')">&times;</button>
      </div>
      
      <div class="form">
        <!-- Показываем статус, группу и адрес при редактировании -->
        <template v-if="isEdit">
          <div class="form-group">
            <label>Статус *</label>
            <select v-model="status" class="input" required>
              <option value="pending">Ожидает</option>
              <option value="active">Активна</option>
              <option value="inactive">Неактивна</option>
              <option value="maintenance">Сервис</option>
            </select>
            <small v-if="status === 'active' && station?.status === 'pending'" class="form-hint">
              ⚠️ Для активации станции потребуется ввести секретный ключ и назначить группу
            </small>
          </div>
          
          <div class="form-group">
            <label>Организационная единица</label>
            <select v-model="org_unit_id" class="input">
              <option value="">Выберите организационную единицу</option>
              <option v-for="orgUnit in orgUnits" :key="orgUnit.org_unit_id" :value="orgUnit.org_unit_id">
                {{ orgUnit.name }} ({{ orgUnit.unit_type === 'group' ? 'Группа' : 'Подгруппа' }})
              </option>
            </select>
          </div>
          
        </template>
        
        <!-- При создании новой станции показываем все поля -->
        <template v-else>
          <div class="form-group">
            <label>ID бокса (box_id) *</label>
            <input v-model="box_id" placeholder="TEST_STATION_001" class="input" required />
          </div>
          
          <div class="form-group">
            <label>ICCID (сим-карты)</label>
            <input v-model="iccid" placeholder="ICCID сим-карты" class="input" />
          </div>
          
          <div class="form-group">
            <label>Всего слотов *</label>
            <input v-model.number="slots_declared" placeholder="4" type="number" min="1" class="input" required />
          </div>
          
          <div class="form-group">
            <label>Статус *</label>
            <select v-model="status" class="input" required>
              <option value="pending">Ожидает</option>
              <option value="active">Активна</option>
              <option value="inactive">Неактивна</option>
              <option value="maintenance">Сервис</option>
            </select>
          </div>
          
          <div class="form-group">
            <label>Организационная единица</label>
            <select v-model="org_unit_id" class="input">
              <option value="">Выберите организационную единицу</option>
              <option v-for="orgUnit in orgUnits" :key="orgUnit.org_unit_id" :value="orgUnit.org_unit_id">
                {{ orgUnit.name }}
              </option>
            </select>
          </div>
          
          <div class="form-group">
            <label>ID адреса</label>
            <input v-model.number="address_id" placeholder="ID адреса" type="number" class="input" />
          </div>
          
          <div class="form-group">
            <label>Название (необязательно)</label>
            <input v-model="name" placeholder="Название станции" class="input" />
          </div>
          
          <div class="form-group">
            <label>Код (отображаемый)</label>
            <input v-model="code" placeholder="Код для отображения" class="input" />
          </div>
        </template>
      </div>
      
      <div class="actions">
        <button class="btn-primary" @click="save" :disabled="!isFormValid">Сохранить</button>
        <button class="btn-secondary" @click="$emit('close')">Отмена</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed, onMounted } from 'vue'
import { useAdminStore } from '../stores/admin'

const props = defineProps({
  isVisible: { type: Boolean, default: false },
  station: { type: Object, default: null }
})

const emit = defineEmits(['close', 'station-added', 'station-edited', 'station-activation-required'])

const adminStore = useAdminStore()

const name = ref('')
const code = ref('')
const box_id = ref('')
const iccid = ref('')
const address_id = ref(null)
const slots_declared = ref(null)
const status = ref('pending')
const org_unit_id = ref(null)

const isEdit = computed(() => !!(props.station && (props.station.station_id || props.station.id)))

const orgUnits = computed(() => adminStore.orgUnits)

const isFormValid = computed(() => {
  if (isEdit.value) {
    // При редактировании проверяем статус (группа необязательна)
    return status.value
  } else {
    // При создании проверяем все обязательные поля
    return box_id.value && slots_declared.value && status.value
  }
})

watch(
  () => props.station,
  (st) => {
    if (st) {
      name.value = st.name || ''
      code.value = st.code || ''
      box_id.value = st.box_id || ''
      iccid.value = st.iccid || ''
      address_id.value = st.address_id ?? null
      slots_declared.value = st.slots_declared ?? null
      status.value = st.status || 'pending'
      org_unit_id.value = st.org_unit_id ?? null
    } else {
      name.value = ''
      code.value = ''
      box_id.value = ''
      iccid.value = ''
      address_id.value = null
      slots_declared.value = null
      status.value = 'pending'
      org_unit_id.value = null
    }
  },
  { immediate: true }
)

// Отслеживаем изменение статуса для активации
watch(status, (newStatus, oldStatus) => {
  // Если статус изменился с "pending" на "active" при редактировании
  // И исходный статус станции был "pending"
  if (isEdit.value && 
      oldStatus === 'pending' && 
      newStatus === 'active' && 
      props.station?.status === 'pending') {
    // Эмитим событие о необходимости активации
    emit('station-activation-required', props.station)
    // Возвращаем статус обратно к "pending"
    status.value = 'pending'
  }
})

const save = () => {
  if (!isFormValid.value) return
  
  if (isEdit.value) {
    // При редактировании отправляем статус, группу и адрес
    const payload = {
      status: status.value,
      org_unit_id: org_unit_id.value || null,
      address_id: address_id.value || null
    }
    const id = props.station.station_id || props.station.id
    emit('station-edited', { id, data: payload })
  } else {
    // При создании отправляем все поля
    const payload = {
      name: name.value || null,
      code: code.value || null,
      box_id: box_id.value,
      iccid: iccid.value || null,
      address_id: address_id.value || null,
      slots_declared: slots_declared.value,
      status: status.value,
      org_unit_id: org_unit_id.value || null
    }
    emit('station-added', payload)
  }
}

onMounted(async () => {
  if (orgUnits.value.length === 0) {
    await adminStore.fetchOrgUnits()
  }
})
</script>

<style scoped>
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
}

.modal-content {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #e9ecef;
}

.modal-header h2 {
  margin: 0;
  color: #333;
  font-size: 1.5rem;
  font-weight: 600;
}

.btn-close {
  background: none;
  border: none;
  font-size: 24px;
  color: #666;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.btn-close:hover {
  color: #333;
  background: #f8f9fa;
}

.form {
  padding: 24px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  color: #333;
  font-weight: 500;
  font-size: 14px;
}

.input {
  width: 100%;
  padding: 12px 16px;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  font-size: 14px;
  transition: border-color 0.2s ease;
  box-sizing: border-box;
}

.input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.input:invalid {
  border-color: #dc3545;
}

.form-hint {
  display: block;
  margin-top: 4px;
  color: #856404;
  font-size: 12px;
  line-height: 1.4;
}

.actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  padding: 20px 24px;
  border-top: 1px solid #e9ecef;
  background: #f8f9fa;
}

.btn-primary {
  padding: 12px 24px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: background-color 0.2s ease;
}

.btn-primary:hover:not(:disabled) {
  background: #5a6fd8;
}

.btn-primary:disabled {
  background: #6c757d;
  cursor: not-allowed;
}

.btn-secondary {
  padding: 12px 24px;
  background: #6c757d;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: background-color 0.2s ease;
}

.btn-secondary:hover {
  background: #5a6268;
}

/* Mobile styles */
@media (max-width: 768px) {
  .modal-content {
    width: 95%;
    margin: 20px;
  }
  
  .modal-header {
    padding: 16px 20px;
  }
  
  .form {
    padding: 20px;
  }
  
  .actions {
    padding: 16px 20px;
    flex-direction: column;
  }
  
  .btn-primary,
  .btn-secondary {
    width: 100%;
  }
}
</style>
