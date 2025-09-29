<template>
  <div class="login-container">
    <h2>Вход по паролю</h2>
    <form @submit.prevent="handleSubmit">
      <BaseInput 
        v-model="form.phone_e164" 
        label="Телефон" 
        placeholder="+79001234567" 
        type="tel"
      />
      <BaseInput 
        v-model="form.password" 
        label="Пароль" 
        placeholder="Введите пароль" 
        type="password"
      />
      <BaseButton type="submit" :disabled="isLoading">
        {{ isLoading ? 'Вход...' : 'Войти' }}
      </BaseButton>
    </form>
    <div class="auth-switch">
      <p>Нет аккаунта? <router-link to="/register">Зарегистрироваться</router-link></p>
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
const form = ref({ phone_e164: '', password: '' });
const isLoading = ref(false);

async function handleSubmit() {
  // Валидация полей
  if (!form.value.phone_e164) {
    // Пожалуйста, введите номер телефона
    return;
  }

  if (!form.value.password) {
    // Пожалуйста, введите пароль
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
    await auth.login({
      phone_e164: form.value.phone_e164,
      password: form.value.password
    });
    router.push('/dashboard');
  } catch (err) {
    // Не удалось войти в систему
  } finally {
    isLoading.value = false;
  }
}
</script>

<style scoped>
.login-container {
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
