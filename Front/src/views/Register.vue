<template>
  <div class="register-container">
    <h2>Регистрация</h2>
    <div v-if="invitationInfo" class="invitation-info">
      <div class="invitation-badge">
        <span class="invitation-icon">🎫</span>
        <span>Приглашение от: {{ invitationInfo.org_unit_name }}</span>
      </div>
      <p class="invitation-description">Вы регистрируетесь в организации "{{ invitationInfo.org_unit_name }}" с ролью "{{ invitationInfo.role }}"</p>
    </div>
    <div v-if="route.query.station || route.query.stationName" class="station-info">
      <div class="station-badge">
        <span class="station-icon">📍</span>
        <span>Станция: {{ route.query.stationName || route.query.station }}</span>
      </div>
      <p class="station-description">После регистрации и входа вы будете перенаправлены к этой станции</p>
    </div>
    <form @submit.prevent="handleSubmit">
      <BaseInput 
        v-model="formattedPhone" 
        label="Телефон" 
        placeholder="+7 (999) 999-99-99" 
        type="tel"
        :error="phoneError"
        autocomplete="tel"
        required
        @input="handlePhoneInput"
        @focus="handlePhoneFocus"
        @blur="validatePhoneField"
        @keydown="handlePhoneKeydown"
      />
      <BaseInput 
        v-model="form.email" 
        type="email" 
        label="Email" 
        placeholder="test@example.com" 
        :error="emailError"
        autocomplete="email"
        required
        @blur="validateEmailField"
      />
      <BaseInput 
        v-model="form.fio" 
        label="ФИО (опционально)" 
        placeholder="Иван Иванов" 
        :error="fioError"
        autocomplete="name"
      />
      <BaseButton type="submit" :disabled="isLoading">
        {{ isLoading ? 'Регистрация...' : 'Зарегистрироваться' }}
      </BaseButton>
    </form>
    
    <!-- Сообщение об успешной регистрации -->
    <div v-if="successMessage" class="success-message">
      <div class="success-icon">✓</div>
      <div class="success-text">{{ successMessage }}</div>
    </div>
    
    <!-- Сообщение об ошибке сервера -->
    <div v-if="serverErrorMessage" class="error-message">
      <div class="error-icon">⚠</div>
      <div class="error-text">{{ serverErrorMessage }}</div>
    </div>
    
    <div class="auth-switch">
      <p>Есть аккаунт? <router-link to="/login">Войти</router-link></p>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue';
import { useAuthStore } from '../stores/auth';
import { useRouter, useRoute } from 'vue-router';
import BaseInput from '../components/BaseInput.vue';
import BaseButton from '../components/BaseButton.vue';
import { pythonAPI } from '../api/pythonApi';

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();
const form = ref({
  phone_e164: '',
  email: '',
  fio: ''
});
const isLoading = ref(false);
const phoneError = ref('');
const emailError = ref('');
const fioError = ref('');
const formattedPhone = ref('');
const successMessage = ref('');
const serverErrorMessage = ref('');
const invitationInfo = ref(null);
const invitationToken = ref(null);

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
  if (!phone || phone.trim() === '') {
    return 'Пожалуйста, введите номер телефона';
  }
  
  // Проверяем формат E164: начинается с +7, затем 10 цифр
  const phoneRegex = /^\+7\d{10}$/;
  if (!phoneRegex.test(phone.trim())) {
    return 'Неверный формат телефона. Введите полный номер';
  }
  
  return '';
}

// Функция валидации email
function validateEmail(email) {
  if (!email || email.trim() === '') {
    return 'Пожалуйста, введите email';
  }
  
  const trimmedEmail = email.trim();
  
  // Более строгая валидация email
  const emailRegex = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/;
  
  if (!emailRegex.test(trimmedEmail)) {
    return 'Неверный формат email. Пример: user@example.com';
  }
  
  // Дополнительные проверки
  if (trimmedEmail.length > 254) {
    return 'Email слишком длинный (максимум 254 символа)';
  }
  
  if (trimmedEmail.includes('..')) {
    return 'Email не может содержать две точки подряд';
  }
  
  return '';
}

// Функция валидации ФИО (опционально)
function validateFio(fio) {
  if (fio && fio.trim().length < 2) {
    return 'ФИО должно содержать минимум 2 символа';
  }
  
  if (fio && fio.trim().length > 100) {
    return 'ФИО не должно превышать 100 символов';
  }
  
  return '';
}

// Валидация телефона в реальном времени
function validatePhoneField() {
  phoneError.value = validatePhone(form.value.phone_e164);
}

// Валидация email в реальном времени
function validateEmailField() {
  emailError.value = validateEmail(form.value.email);
}

async function handleSubmit() {
  // Очищаем предыдущие ошибки и сообщения
  phoneError.value = '';
  emailError.value = '';
  fioError.value = '';
  successMessage.value = '';
  serverErrorMessage.value = '';
  
  // Валидация телефона
  const phoneValidationError = validatePhone(form.value.phone_e164);
  if (phoneValidationError) {
    phoneError.value = phoneValidationError;
  }
  
  // Валидация email
  const emailValidationError = validateEmail(form.value.email);
  if (emailValidationError) {
    emailError.value = emailValidationError;
  }
  
  // Валидация ФИО
  const fioValidationError = validateFio(form.value.fio);
  if (fioValidationError) {
    fioError.value = fioValidationError;
  }
  
  // Если есть ошибки валидации, не отправляем форму
  if (phoneValidationError || emailValidationError || fioValidationError) {
    return;
  }

  isLoading.value = true;
  try {
    const registrationData = {
      phone_e164: form.value.phone_e164?.trim(),
      email: form.value.email?.trim(),
      fio: form.value.fio?.trim() || null
    };
    
    // Если есть токен приглашения, добавляем его к данным регистрации
    if (invitationToken.value) {
      registrationData.invitation_token = invitationToken.value;
      console.log('🎫 Sending invitation token:', invitationToken.value);
    }
    
    // Логируем данные перед отправкой
    console.log('📝 Registration data:', registrationData);
    console.log('📝 Formatted phone:', formattedPhone.value);
    console.log('📝 Extracted phone:', form.value.phone_e164);
    
    const response = await auth.register(registrationData);

    // Отображаем сообщение об успехе из ответа сервера
    if (response && response.message) {
      successMessage.value = response.message;
    } else {
      successMessage.value = 'Регистрация прошла успешно! Проверьте email для получения пароля.';
    }

    // Очищаем форму после успешной регистрации
    form.value = {
      phone_e164: '',
      email: '',
      fio: ''
    };
    formattedPhone.value = '';

    // Через 3 секунды перенаправляем на страницу входа
    setTimeout(() => {
      if (route.query.station) {
        router.push(`/login?station=${route.query.station}&stationName=${route.query.stationName}`);
      } else if (route.query.stationName) {
        router.push(`/login?stationName=${route.query.stationName}`);
      } else {
        router.push('/login');
      }
    }, 3000);

  } catch (err) {
    console.log('🔍 Registration error:', err);
    
    // Проверяем, есть ли сообщение от сервера в ответе
    if (err.originalError && err.originalError.response && err.originalError.response.data) {
      const serverData = err.originalError.response.data;
      console.log('📨 Server response data:', serverData);
      
      // Если сервер вернул сообщение об ошибке, отображаем его
      if (serverData.error) {
        serverErrorMessage.value = serverData.error;
        return; // Не показываем дополнительные ошибки валидации
      }
      
      // Fallback: проверяем также message, если error нет
      if (serverData.message) {
        serverErrorMessage.value = serverData.message;
        return; // Не показываем дополнительные ошибки валидации
      }
    }
    
    // Обработка ошибок регистрации (fallback)
    if (err.message && err.message.includes('phone')) {
      phoneError.value = 'Телефон уже зарегистрирован';
    } else if (err.message && err.message.includes('email')) {
      emailError.value = 'Email уже зарегистрирован';
    } else {
      serverErrorMessage.value = err.message || 'Не удалось зарегистрироваться';
    }
  } finally {
    isLoading.value = false;
  }
}

// Загрузка информации о приглашении при монтировании компонента
onMounted(async () => {
  const invitationTokenParam = route.query.invitation;
  if (invitationTokenParam) {
    invitationToken.value = invitationTokenParam;
    console.log('🎫 Invitation token from URL:', invitationTokenParam);
    try {
      // Получаем информацию о приглашении из базы данных
      const response = await pythonAPI.getInvitationInfo(invitationTokenParam);
      console.log('✅ Invitation info response:', response);
      if (response.success && response.invitation) {
        invitationInfo.value = response.invitation;
      }
    } catch (error) {
      console.error('❌ Ошибка загрузки информации о приглашении:', error);
      serverErrorMessage.value = 'Ошибка загрузки приглашения. Попробуйте использовать другую ссылку.';
    }
  }
});
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

.success-message {
  margin-top: 1rem;
  padding: 1rem;
  background-color: var(--success-bg, #d4edda);
  border: 1px solid var(--success-border, #c3e6cb);
  border-radius: 0.375rem;
  color: var(--success-text, #155724);
  display: flex;
  align-items: center;
  gap: 0.75rem;
  animation: slideIn 0.3s ease-out;
}

.success-icon {
  background-color: #28a745;
  color: white;
  border-radius: 50%;
  width: 1.5rem;
  height: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 0.875rem;
  flex-shrink: 0;
}

.success-text {
  font-weight: 500;
  line-height: 1.4;
}

.error-message {
  margin-top: 1rem;
  padding: 1rem;
  background-color: var(--error-bg, #f8d7da);
  border: 1px solid var(--error-border, #f5c6cb);
  border-radius: 0.375rem;
  color: var(--error-text, #721c24);
  display: flex;
  align-items: center;
  gap: 0.75rem;
  animation: slideIn 0.3s ease-out;
}

.error-icon {
  background-color: var(--danger-color, #dc3545);
  color: white;
  border-radius: 50%;
  width: 1.5rem;
  height: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 0.875rem;
  flex-shrink: 0;
}

.error-text {
  font-weight: 500;
  line-height: 1.4;
}

.invitation-info {
  margin-bottom: 1.5rem;
  padding: 1rem;
  background-color: var(--bg-secondary);
  border-radius: 8px;
  border-left: 4px solid #10b981;
}

.invitation-badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: var(--text-primary);
}

.invitation-icon {
  font-size: 1.2rem;
}

.invitation-description {
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin: 0;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
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
