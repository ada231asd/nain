<template>
  <div v-if="isVisible" class="modal-overlay" @click="onClose">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h3>Редактирование пользователя</h3>
        <button class="btn-close" @click="onClose">&times;</button>
      </div>

      <form @submit.prevent="onSave" class="modal-form">
        <div class="form-group">
          <label>ФИО</label>
          <input v-model="localForm.fio" type="text" class="form-input" placeholder="Иванов Иван Иванович" />
        </div>
        <div class="form-group">
          <label>Телефон</label>
          <input v-model="localForm.phone_e164" type="tel" class="form-input" placeholder="+7 (999) 123-45-67" />
        </div>
        <div class="form-group">
          <label>Email</label>
          <input v-model="localForm.email" type="email" class="form-input" placeholder="user@example.com" />
        </div>
        <div class="form-group">
          <label>Роль</label>
          <select v-model="localForm.role" class="form-select">
            <option value="user">Пользователь</option>
            <option value="subgroup_admin">Администратор подгруппы</option>
            <option value="group_admin">Администратор группы</option>
            <option value="service_admin">Сервис-администратор</option>
          </select>
        </div>
        <div class="form-group">
          <label>Группа</label>
          <select v-model="localForm.parent_org_unit_id" class="form-select">
            <option value="">Без группы</option>
            <option 
              v-for="group in availableGroups" 
              :key="group.org_unit_id" 
              :value="group.org_unit_id"
            >
              {{ group.name }} ({{ group.unit_type }})
            </option>
          </select>
        </div>
        <div class="form-group">
          <label>Статус</label>
          <select v-model="localForm.статус" class="form-select">
            <option value="ожидает">Ожидает</option>
            <option value="активный">Активен</option>
          </select>
        </div>

        <div class="modal-actions">
          <button type="submit" class="btn-save" :disabled="isLoading">Сохранить</button>
          <button type="button" class="btn-cancel" @click="onClose">Отмена</button>
        </div>

        <div class="decision-actions" v-if="showDecisionButtons">
          <button type="button" class="btn-approve" @click="onApprove" :disabled="isLoading">✅ Одобрить</button>
          <button type="button" class="btn-reject" @click="onReject" :disabled="isLoading">❌ Отклонить</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, watch, ref } from 'vue'
import { useAdminStore } from '../stores/admin'

const props = defineProps({
  isVisible: { type: Boolean, default: false },
  user: { type: Object, default: null }
})

const emit = defineEmits(['close', 'save', 'approve', 'reject'])

const adminStore = useAdminStore()
const isLoading = ref(false)
const localForm = reactive({
  fio: '',
  phone_e164: '',
  email: '',
  role: 'user',
  parent_org_unit_id: '',
  статус: 'ожидает'
})

// Доступные группы для выбора
const availableGroups = computed(() => {
  return adminStore.orgUnits || []
})

watch(() => props.user, (u) => {
  if (u) {
    localForm.fio = u.fio || ''
    localForm.phone_e164 = u.phone_e164 || ''
    localForm.email = u.email || ''
    localForm.role = u.role || 'user'
    localForm.parent_org_unit_id = u.parent_org_unit_id || u.org_unit_id || ''
    localForm.статус = u.статус || u.status || 'ожидает'
  }
}, { immediate: true })

const showDecisionButtons = computed(() => localForm.статус === 'ожидает')

const onClose = () => emit('close')

const onSave = async () => {
  isLoading.value = true
  try {
    // Подготавливаем данные для отправки
    const formData = { ...localForm }
    
    // Преобразуем parent_org_unit_id в число или null
    if (formData.parent_org_unit_id === '' || formData.parent_org_unit_id === null) {
      delete formData.parent_org_unit_id
    } else {
      formData.parent_org_unit_id = parseInt(formData.parent_org_unit_id)
    }
    
    // Сервер ожидает поле "статус" (кириллица), оставляем как есть
    // Проверяем, что статус в правильном формате (pending/active/blocked)
    const statusMap = {
      'ожидает': 'pending',
      'активный': 'active', 
      'заблокирован': 'blocked',
      'отклонен': 'rejected'
    }
    if (formData.статус && statusMap[formData.статус]) {
      formData.статус = statusMap[formData.статус]
    }
    
    emit('save', formData)
  } finally {
    isLoading.value = false
  }
}

const onApprove = () => emit('approve')
const onReject = () => emit('reject')
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000;
}
.modal-content { background: white; border-radius: 12px; min-width: 420px; max-width: 90vw; box-shadow: 0 20px 40px rgba(0,0,0,0.2); }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid #e9ecef; }
.btn-close { background: none; border: none; font-size: 20px; color: #666; cursor: pointer; }
.modal-form { padding: 20px; }
.form-group { margin-bottom: 14px; }
.form-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; }
.form-input, .form-select { width: 100%; padding: 10px; border: 2px solid #e9ecef; border-radius: 8px; font-size: 14px; }
.form-input:focus, .form-select:focus { outline: none; border-color: #667eea; }
.modal-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 16px; }
.btn-save, .btn-cancel { padding: 10px 18px; border: none; border-radius: 8px; cursor: pointer; }
.btn-save { background: #28a745; color: white; }
.btn-cancel { background: #6c757d; color: white; }
.decision-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 12px; }
.btn-approve { background: #28a745; color: white; padding: 8px 14px; border: none; border-radius: 6px; cursor: pointer; }
.btn-reject { background: #dc3545; color: white; padding: 8px 14px; border: none; border-radius: 6px; cursor: pointer; }
@media (max-width: 768px) { .modal-content { min-width: 90vw; } }
</style>
