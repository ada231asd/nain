<template>
  <div v-if="isVisible" class="modal-overlay" @click="closeModal">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h2>Редактировать павербанк</h2>
        <button @click="closeModal" class="close-btn">&times;</button>
      </div>
      
      <div class="modal-body">
        <form @submit.prevent="savePowerbank">
          <div class="form-group">
            <label for="serial_number">Серийный номер:</label>
            <input 
              id="serial_number"
              v-model="formData.serial_number" 
              type="text" 
              required 
              class="form-input"
            />
          </div>
          
          <div class="form-group">
            <label for="org_unit_id">Группа/Подгруппа:</label>
            <select 
              id="org_unit_id"
              v-model="formData.org_unit_id" 
              class="form-select"
            >
              <option value="">Выберите группу</option>
              <template v-for="group in groups" :key="group.org_unit_id">
                <optgroup :label="group.name">
                  <option :value="group.org_unit_id">{{ group.name }}</option>
                  <option 
                    v-for="subgroup in getSubgroupsForGroup(group.org_unit_id)" 
                    :key="subgroup.org_unit_id" 
                    :value="subgroup.org_unit_id"
                  >
                    &nbsp;&nbsp;{{ subgroup.name }}
                  </option>
                </optgroup>
              </template>
              <!-- Отладочная информация -->
              <option v-if="groups.length === 0" disabled>Нет доступных групп</option>
            </select>
          </div>
          
          <div class="form-group">
            <label for="soh">SOH (State of Health):</label>
            <input 
              id="soh"
              v-model.number="formData.soh" 
              type="number" 
              min="0" 
              max="100" 
              class="form-input"
            />
          </div>
          
          <div class="form-group">
            <label for="status">Статус:</label>
            <select 
              id="status"
              v-model="formData.status" 
              class="form-select"
            >
              <option value="active">Активный</option>
              <option value="user_reported_broken">Сломан (сообщил пользователь)</option>
              <option value="system_error">Ошибка системы</option>
              <option value="written_off">Списан</option>
            </select>
          </div>
          
          <div class="form-group">
            <label for="write_off_reason">Причина списания:</label>
            <select 
              id="write_off_reason"
              v-model="formData.write_off_reason" 
              class="form-select"
              :disabled="formData.status !== 'written_off'"
            >
              <option value="none">Нет</option>
              <option value="broken">Сломан</option>
              <option value="lost">Потерян</option>
              <option value="other">Другое</option>
            </select>
          </div>
          
          <div class="form-actions">
            <button type="button" @click="closeModal" class="btn btn-secondary">
              Отмена
            </button>
            <button type="submit" class="btn btn-primary" :disabled="isLoading">
              {{ isLoading ? 'Сохранение...' : 'Сохранить' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { useAdminStore } from '../stores/admin'

const props = defineProps({
  isVisible: {
    type: Boolean,
    default: false
  },
  powerbank: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close', 'saved'])

const adminStore = useAdminStore()

const isLoading = ref(false)

const formData = ref({
  serial_number: '',
  org_unit_id: null,
  soh: 100,
  status: 'active',
  write_off_reason: 'none'
})

// Получаем группы и подгруппы из store
const groups = computed(() => {
  return adminStore.groups
})
const subgroups = computed(() => {
  return adminStore.subgroups
})

// Функция для получения подгрупп для конкретной группы
const getSubgroupsForGroup = (groupId) => {
  const result = subgroups.value.filter(sub => sub.parent_org_unit_id === groupId)
  return result
}

// Следим за изменениями powerbank
watch(() => props.powerbank, (newPowerbank) => {
  if (newPowerbank) {
    formData.value = {
      serial_number: newPowerbank.serial_number || '',
      org_unit_id: newPowerbank.org_unit_id || null,
      soh: newPowerbank.soh || 100,
      status: newPowerbank.status || 'active',
      write_off_reason: newPowerbank.write_off_reason || 'none'
    }
  }
}, { immediate: true })

// Следим за видимостью модального окна и загружаем данные если нужно
watch(() => props.isVisible, async (isVisible) => {
  if (isVisible) {
    // Если данных нет, загружаем их
    if (adminStore.groups.length === 0) {
      try {
        await adminStore.fetchOrgUnits()
      } catch (error) {
        // Error handled silently
      }
    }
  }
})

// Следим за изменениями статуса для сброса причины списания
watch(() => formData.value.status, (newStatus) => {
  if (newStatus !== 'written_off') {
    formData.value.write_off_reason = 'none'
  }
})

const closeModal = () => {
  emit('close')
}

const savePowerbank = async () => {
  if (!props.powerbank?.id) return
  
  isLoading.value = true
  try {
    await adminStore.updatePowerbank(props.powerbank.id, formData.value)
    emit('saved')
    closeModal()
  } catch (error) {
    // Ошибка обновления павербанка
  } finally {
    isLoading.value = false
  }
}
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
  border-radius: 8px;
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #e0e0e0;
}

.modal-header h2 {
  margin: 0;
  color: #333;
  font-size: 1.5rem;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #666;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  color: #333;
}

.modal-body {
  padding: 20px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: 500;
  color: #333;
}

.form-input,
.form-select {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  box-sizing: border-box;
}

.form-input:focus,
.form-select:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
}

.form-select:disabled {
  background-color: #f8f9fa;
  color: #6c757d;
  cursor: not-allowed;
}

.form-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid #e0e0e0;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-primary {
  background-color: #007bff;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: #0056b3;
}

.btn-primary:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}

.btn-secondary {
  background-color: #6c757d;
  color: white;
}

.btn-secondary:hover {
  background-color: #545b62;
}

.debug-info {
  margin-bottom: 5px;
  padding: 5px;
  background-color: #f8f9fa;
  border-radius: 4px;
  border: 1px solid #dee2e6;
}

.debug-info small {
  color: #6c757d;
  font-size: 12px;
}
</style>
