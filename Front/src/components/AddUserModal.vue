<template>
  <div v-if="isVisible" class="modal-overlay" @click="$emit('close')">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h3>Добавить пользователя</h3>
        <button class="btn-close" @click="$emit('close')">&times;</button>
      </div>

      <form @submit.prevent="save" class="modal-form">
        <div class="form-group">
          <label>ФИО *</label>
          <input v-model="form.fio" type="text" class="form-input" placeholder="Иванов Иван Иванович" required />
        </div>
        <div class="form-group">
          <label>Телефон *</label>
          <input v-model="form.phone_e164" type="tel" class="form-input" placeholder="+7 (999) 123-45-67" required />
        </div>
        <div class="form-group">
          <label>Email *</label>
          <input v-model="form.email" type="email" class="form-input" placeholder="user@example.com" required />
        </div>
        <div class="form-group">
          <label>Пароль *</label>
          <input v-model="form.password" type="password" class="form-input" placeholder="Введите пароль" required />
        </div>

        <div class="modal-actions">
          <button type="submit" class="btn-save" :disabled="isLoading">Добавить пользователя</button>
          <button type="button" class="btn-cancel" @click="$emit('close')">Отмена</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'

const props = defineProps({
  isVisible: { type: Boolean, default: false }
})

const emit = defineEmits(['close', 'user-added'])

const isLoading = ref(false)
const form = reactive({
  fio: '',
  phone_e164: '',
  email: '',
  password: ''
})

const save = () => {
  isLoading.value = true
  try {
    emit('user-added', {
      fio: form.fio,
      phone_e164: form.phone_e164,
      email: form.email,
      password: form.password
    })
  } finally {
    isLoading.value = false
  }
}
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
@media (max-width: 768px) { .modal-content { min-width: 90vw; } }
</style>
