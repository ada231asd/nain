<template>
  <div class="demo-page">
    <div class="demo-header">
      <h1>Демонстрация системы QR-кодов</h1>
      <p>Тестирование функциональности QR-кодов для станций</p>
    </div>
    
    <div class="demo-content">
      <div class="demo-section">
        <h2>1. Генерация QR-кода</h2>
        <p>Администраторы могут генерировать QR-коды для станций, нажав кнопку 📱 на каждой станции в админ панели.</p>
        <div class="demo-link">
          <router-link to="/admin" class="demo-btn">Открыть админ панель</router-link>
        </div>
      </div>
      
      <div class="demo-section">
        <h2>2. Тестирование QR-кода</h2>
        <p>Пример ссылки QR-кода для станции:</p>
        <div class="demo-url">
          <code>https://redmine.primetech.ru:8443/Станция%20Центр</code>
        </div>
        <div class="demo-link">
          <a :href="demoUrl" target="_blank" class="demo-btn">Тестировать ссылку</a>
        </div>
      </div>
      
      <div class="demo-section">
        <h2>3. Процесс работы</h2>
        <div class="process-steps">
          <div class="step">
            <div class="step-number">1</div>
            <div class="step-content">
              <h3>Сканирование QR-кода</h3>
              <p>Пользователь сканирует QR-код станции</p>
            </div>
          </div>
          <div class="step">
            <div class="step-number">2</div>
            <div class="step-content">
              <h3>Перенаправление на авторизацию</h3>
              <p>Открывается страница входа с информацией о станции</p>
            </div>
          </div>
          <div class="step">
            <div class="step-number">3</div>
            <div class="step-content">
              <h3>Вход или регистрация</h3>
              <p>Пользователь входит в систему или регистрируется</p>
            </div>
          </div>
          <div class="step">
            <div class="step-number">4</div>
            <div class="step-content">
              <h3>Информация о станции</h3>
              <p>После авторизации показывается информация о станции</p>
            </div>
          </div>
        </div>
      </div>
      
      <div class="demo-section">
        <h2>4. Функции станции</h2>
        <div class="features-grid">
          <div class="feature-card">
            <div class="feature-icon">🔋</div>
            <h3>Взять пауэрбанк</h3>
            <p>Пользователь может взять доступный пауэрбанк</p>
          </div>
          <div class="feature-card">
            <div class="feature-icon">↩️</div>
            <h3>Вернуть пауэрбанк</h3>
            <p>Пользователь может вернуть свой пауэрбанк</p>
          </div>
          <div class="feature-card">
            <div class="feature-icon">ℹ️</div>
            <h3>Информация о станции</h3>
            <p>Просмотр подробной информации о станции</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const demoUrl = computed(() => {
  const baseUrl = window.location.origin;
  return `${baseUrl}/${encodeURIComponent('Станция Центр')}`;
});
</script>

<style scoped>
.demo-page {
  max-width: 1000px;
  margin: 0 auto;
  padding: 2rem;
  background-color: var(--background-color);
  color: var(--text-primary);
}

.demo-header {
  text-align: center;
  margin-bottom: 3rem;
}

.demo-header h1 {
  margin-bottom: 1rem;
  color: var(--text-primary);
}

.demo-header p {
  color: var(--text-secondary);
  font-size: 1.1rem;
}

.demo-content {
  display: flex;
  flex-direction: column;
  gap: 3rem;
}

.demo-section {
  background-color: var(--bg-secondary);
  padding: 2rem;
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.demo-section h2 {
  margin-bottom: 1rem;
  color: var(--text-primary);
}

.demo-section p {
  margin-bottom: 1.5rem;
  color: var(--text-secondary);
  line-height: 1.6;
}

.demo-link {
  margin-top: 1rem;
}

.demo-btn {
  display: inline-block;
  background-color: #3b82f6;
  color: white;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  text-decoration: none;
  font-weight: 500;
  transition: background-color 0.2s;
}

.demo-btn:hover {
  background-color: #2563eb;
}

.demo-url {
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 1rem;
  margin: 1rem 0;
  overflow-x: auto;
}

.demo-url code {
  font-family: 'Courier New', monospace;
  font-size: 0.9rem;
  color: #1e293b;
  word-break: break-all;
}

.process-steps {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  margin-top: 2rem;
}

.step {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 1.5rem;
  background-color: white;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.step-number {
  background-color: #3b82f6;
  color: white;
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  flex-shrink: 0;
}

.step-content h3 {
  margin-bottom: 0.5rem;
  color: var(--text-primary);
  font-size: 1.1rem;
}

.step-content p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  margin-top: 2rem;
}

.feature-card {
  background-color: white;
  padding: 2rem;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  text-align: center;
}

.feature-icon {
  font-size: 2.5rem;
  margin-bottom: 1rem;
}

.feature-card h3 {
  margin-bottom: 1rem;
  color: var(--text-primary);
}

.feature-card p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.9rem;
}

@media (max-width: 768px) {
  .demo-page {
    padding: 1rem;
  }
  
  .demo-section {
    padding: 1.5rem;
  }
  
  .process-steps {
    grid-template-columns: 1fr;
  }
  
  .features-grid {
    grid-template-columns: 1fr;
  }
}
</style>
