<template>
  <div class="login-container">
    <h2>Вход по паролю</h2>
    <div v-if="route.query.station || route.query.stationName" class="station-info">
      <div class="station-badge">
        <span class="station-icon">📍</span>
        <span>Станция: {{ route.query.stationName || route.query.station }}</span>
      </div>
      <p class="station-description">После входа вы будете перенаправлены к этой станции</p>
    </div>
    <form @submit.prevent="handleSubmit">
      <BaseInput 
        v-model="formattedPhone" 
        label="Телефон" 
        placeholder="+7 (999) 999-99-99" 
        type="tel"
        :error="phoneError"
        autocomplete="tel"
        @input="handlePhoneInput"
        @focus="handlePhoneFocus"
        @keydown="handlePhoneKeydown"
      />
      <BaseInput 
        v-model="form.password" 
        label="Пароль" 
        placeholder="Введите пароль" 
        type="password"
        :error="passwordError"
        autocomplete="current-password"
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
import { ref, nextTick, onMounted } from 'vue';
import { useAuthStore } from '../stores/auth';
import { useRouter, useRoute } from 'vue-router';
import BaseInput from '../components/BaseInput.vue';
import BaseButton from '../components/BaseButton.vue';

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();
const form = ref({ phone_e164: '', password: '' });
const isLoading = ref(false);
const phoneError = ref('');
const passwordError = ref('');
const formattedPhone = ref('');

// Функция форматирования телефона в маску +7 (999) 999-99-99
function formatPhone(value) {
  // Убираем все символы кроме цифр
  const numbers = value.replace(/\D/g, '');
  
  // Если номер начинается с 8, заменяем на 7
  let cleanNumbers = numbers;
  if (cleanNumbers.startsWith('8')) {
    cleanNumbers = '7' + cleanNumbers.slice(1);
  }
  
  // Если номер не начинается с 7, добавляем 7
  if (!cleanNumbers.startsWith('7') && cleanNumbers.length > 0) {
    cleanNumbers = '7' + cleanNumbers;
  }
  
  // Ограничиваем длину до 11 цифр (7 + 10)
  if (cleanNumbers.length > 11) {
    cleanNumbers = cleanNumbers.slice(0, 11);
  }
  
  // Форматируем в маску
  if (cleanNumbers.length === 0) return '';
  if (cleanNumbers.length === 1) return `+${cleanNumbers}`;
  if (cleanNumbers.length === 2) return `+${cleanNumbers}`;
  if (cleanNumbers.length === 3) return `+${cleanNumbers}`;
  if (cleanNumbers.length === 4) return `+${cleanNumbers.slice(0, 1)} (${cleanNumbers.slice(1)})`;
  if (cleanNumbers.length <= 7) return `+${cleanNumbers.slice(0, 1)} (${cleanNumbers.slice(1, 4)}) ${cleanNumbers.slice(4)}`;
  if (cleanNumbers.length <= 9) return `+${cleanNumbers.slice(0, 1)} (${cleanNumbers.slice(1, 4)}) ${cleanNumbers.slice(4, 7)}-${cleanNumbers.slice(7)}`;
  return `+${cleanNumbers.slice(0, 1)} (${cleanNumbers.slice(1, 4)}) ${cleanNumbers.slice(4, 7)}-${cleanNumbers.slice(7, 9)}-${cleanNumbers.slice(9)}`;
}

// Функция извлечения чистого номера телефона
function extractPhoneNumber(formattedValue) {
  const numbers = formattedValue.replace(/\D/g, '');
  
  // Если номер пустой, возвращаем пустую строку
  if (!numbers) {
    return '';
  }
  
  if (numbers.startsWith('8')) {
    return '+7' + numbers.slice(1);
  }
  if (numbers.startsWith('7')) {
    return '+' + numbers;
  }
  return '+' + numbers;
}

// Обработка ввода телефона
function handlePhoneInput(event) {
  const value = event.target.value;
  const cursorPosition = event.target.selectionStart;
  
  // Форматируем значение
  const formatted = formatPhone(value);
  formattedPhone.value = formatted;
  form.value.phone_e164 = extractPhoneNumber(formatted);
  
  // Восстанавливаем позицию курсора
  nextTick(() => {
    const input = event.target;
    let newCursorPosition = cursorPosition;
    
    // Если значение стало длиннее (добавились символы маски), корректируем позицию
    if (formatted.length > value.length) {
      newCursorPosition = Math.min(cursorPosition + (formatted.length - value.length), formatted.length);
    }
    
    input.setSelectionRange(newCursorPosition, newCursorPosition);
  });
}

// Обработка удаления символов (Backspace/Delete)
function handlePhoneKeydown(event) {
  const value = event.target.value;
  const cursorPosition = event.target.selectionStart;
  
  // Если нажали Backspace и курсор находится в позиции, где есть символ маски
  if (event.key === 'Backspace') {
    const maskPositions = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]; // позиции символов маски
    const maskChars = ['+', '7', ' ', '(', ')', ' ', '-', '-'];
    
    // Если курсор находится на символе маски, удаляем предыдущую цифру
    if (maskPositions.includes(cursorPosition - 1)) {
      event.preventDefault();
      
      // Находим предыдущую цифру и удаляем её
      let newValue = value;
      let pos = cursorPosition - 1;
      
      while (pos >= 0 && !/\d/.test(newValue[pos])) {
        pos--;
      }
      
      if (pos >= 0) {
        newValue = newValue.slice(0, pos) + newValue.slice(pos + 1);
        formattedPhone.value = formatPhone(newValue);
        form.value.phone_e164 = extractPhoneNumber(formattedPhone.value);
        
        nextTick(() => {
          event.target.setSelectionRange(pos, pos);
        });
      }
    }
  }
}

// Обработка фокуса на поле телефона
function handlePhoneFocus() {
  if (!formattedPhone.value) {
    formattedPhone.value = '+7 (';
  }
}

// Функция валидации телефона
function validatePhone(phone) {
  if (!phone) {
    return 'Пожалуйста, введите номер телефона';
  }
  
  // Проверяем формат E164: начинается с +7, затем 10 цифр
  const phoneRegex = /^\+7\d{10}$/;
  if (!phoneRegex.test(phone)) {
    return 'Неверный формат телефона. Введите полный номер';
  }
  
  return '';
}

// Функция валидации пароля
function validatePassword(password) {
  if (!password) {
    return 'Пожалуйста, введите пароль';
  }
  
  if (password.length < 6) {
    return 'Пароль должен содержать минимум 6 символов';
  }
  
  return '';
}

async function handleSubmit() {
  // Очищаем предыдущие ошибки
  phoneError.value = '';
  passwordError.value = '';
  
  // Валидация телефона
  const phoneValidationError = validatePhone(form.value.phone_e164);
  if (phoneValidationError) {
    phoneError.value = phoneValidationError;
  }
  
  // Валидация пароля
  const passwordValidationError = validatePassword(form.value.password);
  if (passwordValidationError) {
    passwordError.value = passwordValidationError;
  }
  
  // Если есть ошибки валидации, не отправляем форму
  if (phoneValidationError || passwordValidationError) {
    return;
  }

  isLoading.value = true;
  try {
    const loginData = {
      phone_e164: form.value.phone_e164,
      password: form.value.password
    };
    
    // Логируем данные перед отправкой
    console.log('🔐 Login data:', loginData);
    console.log('🔐 Formatted phone:', formattedPhone.value);
    console.log('🔐 Extracted phone:', form.value.phone_e164);
    
    await auth.login(loginData);
    
    // Проверяем, есть ли параметры станции для перенаправления
    if (route.query.station) {
      router.push(`/dashboard?station=${route.query.station}&stationName=${route.query.stationName}`);
    } else if (route.query.stationName) {
      // Для прямых ссылок на станции по имени
      router.push(`/dashboard?stationName=${route.query.stationName}`);
    } else {
      router.push('/dashboard');
    }
  } catch (err) {
    // Обработка ошибок авторизации
    if (err.message && err.message.includes('Неверный номер телефона, пароль или пользователь не подтвержден администратором')) {
      // Показываем сообщение о ожидании подтверждения для всех случаев неудачной авторизации
      phoneError.value = 'Ожидайте подтверждения администратора';
    } else if (err.message && err.message.includes('phone')) {
      phoneError.value = 'Неверный номер телефона';
    } else if (err.message && err.message.includes('password')) {
      passwordError.value = 'Неверный пароль';
    } else {
      phoneError.value = 'Не удалось войти в систему';
    }
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

.station-info {
  margin-bottom: 1.5rem;
  padding: 1rem;
  background-color: var(--bg-secondary);
  border-radius: 8px;
  border-left: 4px solid #3b82f6;
}

.station-badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: var(--text-primary);
}

.station-icon {
  font-size: 1.2rem;
}

.station-description {
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin: 0;
}
</style>
