<template>
  <div class="register-container">
    <h2>Регистрация</h2>
    <form @submit.prevent="handleSubmit">
      <BaseInput v-model="form.phone_e164" label="Телефон" placeholder="+79001234567" />
      <BaseInput v-model="form.email" type="email" label="Email" placeholder="test@example.com" />
      <BaseInput v-model="form.fio" label="ФИО (опционально)" placeholder="Иван Иванов" />
      <BaseButton type="submit" :disabled="isLoading">
        {{ isLoading ? 'Регистрация...' : 'Зарегистрироваться' }}
      </BaseButton>
    </form>
    <div class="auth-switch">
      <p>Есть аккаунт? <router-link to="/login">Войти</router-link></p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useAuthStore } from '../stores/auth';
import { useRouter } from 'vue-router';
import BaseInput from '../components/BaseInput.vue';
import BaseButton from '../components/BaseButton.vue';

const auth = useAuthStore();
const router = useRouter();
const form = ref({
  phone_e164: '',
  email: '',
  fio: ''
});
const isLoading = ref(false);

async function handleSubmit() {
  // Валидация обязательных полей
  if (!form.value.email || !form.value.phone_e164) {
    // Пожалуйста, заполните все обязательные поля
    return;
  }

  // Валидация формата email
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(form.value.email)) {
    // Неверный формат email
    return;
  }

  // Валидация формата телефона (+E164)
  const phoneRegex = /^\+[1-9]\d{1,14}$/;
  if (!phoneRegex.test(form.value.phone_e164)) {
    // Неверный формат телефона. Используйте формат +E164 (например, +79001234567)
    return;
  }

  isLoading.value = true;
  try {
    const response = await auth.register({
      phone_e164: form.value.phone_e164,
      email: form.value.email,
      fio: form.value.fio || null
    });

    // После регистрации перенаправляем на страницу входа
    router.push('/login');
  } catch (err) {
    // Не удалось зарегистрироваться
  } finally {
    isLoading.value = false;
  }
}
</script>

<style scoped>
.register-container {
  max-width: 400px;
  margin: 0 auto;
  padding: 2rem;
  background-color: var(--background-color);
  color: var(--text-primary);
}
h2 {
  margin-bottom: 1rem;
  color: var(--text-primary);
}
form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.auth-switch {
  margin-top: 1rem;
  text-align: center;
}
.auth-switch a {
  color: var(--primary-color);
  text-decoration: none;
}
.auth-switch a:hover {
  text-decoration: underline;
}
</style>
