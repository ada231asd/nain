<template>
  <div id="app">
    <router-view />
  </div>
</template>

<script setup>
import { onMounted } from 'vue';
import { useAuthStore } from './stores/auth';

const authStore = useAuthStore();

// Инициализация пользователя при запуске приложения
onMounted(async () => {
  // Инициализируем аутентификацию (проверяет токен и загружает профиль если нужно)
  await authStore.initializeAuth();
});
</script>

<style>
/* Global styles */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html {
  font-size: 16px;
  scroll-behavior: smooth;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  line-height: 1.5;
  color: var(--text-primary, #1e293b);
  background-color: var(--background-color, #ffffff);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

#app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* Typography */
h1, h2, h3, h4, h5, h6 {
  font-weight: 600;
  line-height: 1.25;
  color: #1e293b;
  margin-bottom: 8px;
}

h1 { font-size: 30px; }
h2 { font-size: 24px; }
h3 { font-size: 20px; }
h4 { font-size: 18px; }
h5 { font-size: 16px; }
h6 { font-size: 14px; }

p {
  margin-bottom: 16px;
  line-height: 1.75;
}

a {
  color: #3b82f6;
  text-decoration: none;
  transition: color 0.2s ease;
}

a:hover {
  color: #2563eb;
}

/* Form elements */
input, textarea, select, button {
  font-family: inherit;
  font-size: inherit;
  line-height: inherit;
}

/* Mobile-first responsive design */
@media (max-width: 768px) {
  html {
    font-size: 14px;
  }
  
  .container {
    padding: 0 16px;
  }
}

/* Utility classes */
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 16px;
  width: 100%;
}

.text-center { text-align: center; }
.text-left { text-align: left; }
.text-right { text-align: right; }

.text-primary { color: #1e293b; }
.text-secondary { color: #64748b; }
.text-tertiary { color: #94a3b8; }

.bg-primary { background-color: #ffffff; }
.bg-secondary { background-color: #f8fafc; }
.bg-tertiary { background-color: #f1f5f9; }

/* Spacing utilities */
.mt-1 { margin-top: 4px; }
.mt-2 { margin-top: 8px; }
.mt-3 { margin-top: 16px; }
.mt-4 { margin-top: 24px; }
.mt-5 { margin-top: 32px; }

.mb-1 { margin-bottom: 4px; }
.mb-2 { margin-bottom: 8px; }
.mb-3 { margin-bottom: 16px; }
.mb-4 { margin-bottom: 24px; }
.mb-5 { margin-bottom: 32px; }

.ml-1 { margin-left: 4px; }
.ml-2 { margin-left: 8px; }
.ml-3 { margin-left: 16px; }
.ml-4 { margin-left: 24px; }
.ml-5 { margin-left: 32px; }

.mr-1 { margin-right: 4px; }
.mr-2 { margin-right: 8px; }
.mr-3 { margin-right: 16px; }
.mr-4 { margin-right: 24px; }
.mr-5 { margin-right: 32px; }

.p-1 { padding: 4px; }
.p-2 { padding: 8px; }
.p-3 { padding: 16px; }
.p-4 { padding: 24px; }
.p-5 { padding: 32px; }

.pt-1 { padding-top: 4px; }
.pt-2 { padding-top: 8px; }
.pt-3 { padding-top: 16px; }
.pt-4 { padding-top: 24px; }
.pt-5 { padding-top: 32px; }

.pb-1 { padding-bottom: 4px; }
.pb-2 { padding-bottom: 8px; }
.pb-3 { padding-bottom: 16px; }
.pb-4 { padding-bottom: 24px; }
.pb-5 { padding-bottom: 32px; }

.pl-1 { padding-left: 4px; }
.pl-2 { padding-left: 8px; }
.pl-3 { padding-left: 16px; }
.pl-4 { padding-left: 24px; }
.pl-5 { padding-left: 32px; }

.pr-1 { padding-right: 4px; }
.pr-2 { padding-right: 8px; }
.pr-3 { padding-right: 16px; }
.pr-4 { padding-right: 24px; }
.pr-5 { padding-right: 32px; }

/* Flexbox utilities */
.flex { display: flex; }
.flex-col { flex-direction: column; }
.flex-row { flex-direction: row; }
.flex-wrap { flex-wrap: wrap; }
.flex-nowrap { flex-wrap: nowrap; }

.items-center { align-items: center; }
.items-start { align-items: flex-start; }
.items-end { align-items: flex-end; }
.items-stretch { align-items: stretch; }

.justify-center { justify-content: center; }
.justify-start { justify-content: flex-start; }
.justify-end { justify-content: flex-end; }
.justify-between { justify-content: space-between; }
.justify-around { justify-content: space-around; }

.flex-1 { flex: 1; }
.flex-auto { flex: auto; }
.flex-none { flex: none; }

/* Grid utilities */
.grid { display: grid; }
.grid-cols-1 { grid-template-columns: repeat(1, minmax(0, 1fr)); }
.grid-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.grid-cols-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.grid-cols-4 { grid-template-columns: repeat(4, minmax(0, 1fr)); }

.gap-1 { gap: 4px; }
.gap-2 { gap: 8px; }
.gap-3 { gap: 16px; }
.gap-4 { gap: 24px; }
.gap-5 { gap: 32px; }

/* Border radius utilities */
.rounded { border-radius: 8px; }
.rounded-sm { border-radius: 4px; }
.rounded-lg { border-radius: 12px; }
.rounded-xl { border-radius: 16px; }
.rounded-full { border-radius: 9999px; }

/* Shadow utilities */
.shadow-sm { box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05); }
.shadow-md { box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06); }
.shadow-lg { box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05); }
.shadow-xl { box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04); }

/* Responsive utilities */
@media (min-width: 640px) {
  .sm\:grid-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .sm\:grid-cols-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .sm\:grid-cols-4 { grid-template-columns: repeat(4, minmax(0, 1fr)); }
}

@media (min-width: 768px) {
  .md\:grid-cols-2 { grid-template-columns: repeat(2, minmax(0, 1px)); }
  .md\:grid-cols-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .md\:grid-cols-4 { grid-template-columns: repeat(4, minmax(0, 1fr)); }
}

@media (min-width: 1024px) {
  .lg\:grid-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .lg\:grid-cols-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .lg\:grid-cols-4 { grid-template-columns: repeat(4, minmax(0, 1fr)); }
}

/* Print styles */
@media print {
  .no-print { display: none !important; }
}

</style>
