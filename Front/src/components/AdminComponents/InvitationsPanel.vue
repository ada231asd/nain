<template>
  <div class="invitations-panel">
    <h2>Приглашения</h2>
    
    <!-- Форма создания приглашения -->
    <div class="create-invitation-form">
      <h3>Создать приглашение</h3>
      <div class="form-group">
        <label>Организационная единица</label>
        <select v-model="selectedOrgUnit" class="form-control">
          <option value="">Выберите организацию</option>
          <option v-for="org in orgUnits" :key="org.org_unit_id" :value="org.org_unit_id">
            {{ org.name }} ({{ org.unit_type }})
          </option>
        </select>
      </div>
      
      <div class="form-group">
        <label>Роль</label>
        <select v-model="selectedRole" class="form-control">
          <option value="user">Пользователь</option>
          <option value="subgroup_admin">Администратор подгруппы</option>
          <option value="group_admin">Администратор группы</option>
        </select>
      </div>
      
      <button @click="generateInvitation" :disabled="isGenerating" class="btn btn-primary">
        {{ isGenerating ? 'Генерация...' : 'Создать приглашение' }}
      </button>
    </div>
    
    <!-- Результат создания приглашения -->
    <div v-if="invitationResult" class="invitation-result">
      <h3>Приглашение создано</h3>
      <div class="invitation-link">
        <label>Ссылка:</label>
        <div class="link-container">
          <input type="text" :value="invitationResult.invitation_link" readonly class="link-input" />
          <button @click="copyLink" class="btn btn-secondary">Копировать</button>
        </div>
      </div>
      
      <div class="qr-code-container">
        <label>QR-код:</label>
        <div ref="qrCodeRef" class="qr-code-display"></div>
        <button @click="downloadQR" class="btn btn-secondary">Скачать QR-код</button>
      </div>
    </div>
    
    <!-- Список приглашений -->
    <div class="invitations-list">
      <h3>Все приглашения</h3>
      <div v-if="loading" class="loading">Загрузка...</div>
      <div v-else-if="invitations.length === 0" class="no-invitations">
        Приглашения не найдены
      </div>
      <table v-else class="invitations-table">
        <thead>
          <tr>
            <th>Организация</th>
            <th>Роль</th>
            <th>Создал</th>
            <th>Дата создания</th>
            <th>Статус</th>
            <th>Действия</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="invitation in invitations" :key="invitation.id">
            <td>{{ invitation.org_unit_name }}</td>
            <td>{{ invitation.role }}</td>
            <td>{{ invitation.created_by_name }}</td>
            <td>{{ formatDate(invitation.created_at) }}</td>
            <td>
              <span :class="['status-badge', invitation.used ? 'used' : 'active']">
                {{ invitation.used ? 'Использовано' : 'Активно' }}
              </span>
            </td>
            <td>
              <button @click="showInvitationDetails(invitation)" class="btn btn-sm">Показать</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    
    <!-- Модальное окно с деталями приглашения -->
    <div v-if="selectedInvitation" class="modal" @click.self="selectedInvitation = null">
      <div class="modal-content">
        <h3>Детали приглашения</h3>
        <div class="invitation-details">
          <p><strong>Организация:</strong> {{ selectedInvitation.org_unit_name }}</p>
          <p><strong>Роль:</strong> {{ selectedInvitation.role }}</p>
          <p><strong>Создал:</strong> {{ selectedInvitation.created_by_name }}</p>
          <p><strong>Дата:</strong> {{ formatDate(selectedInvitation.created_at) }}</p>
          <p><strong>Статус:</strong> {{ selectedInvitation.used ? 'Использовано' : 'Активно' }}</p>
          
          <div class="invitation-link-section">
            <label>Ссылка приглашения:</label>
            <div class="link-container">
              <input type="text" :value="getInvitationLink(selectedInvitation.token)" readonly class="link-input" />
              <button @click="copyInvitationLink(selectedInvitation.token)" class="btn btn-secondary">Копировать</button>
            </div>
          </div>
          
          <div class="qr-code-section">
            <label>QR-код:</label>
            <div ref="invitationQRRef" class="qr-code-display-small"></div>
            <button @click="downloadInvitationQR(selectedInvitation.token)" class="btn btn-secondary">Скачать</button>
          </div>
        </div>
        <button @click="selectedInvitation = null" class="btn btn-primary">Закрыть</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue';
import { pythonAPI } from '../../api/pythonApi';
import QRCode from 'qrcode';

const orgUnits = ref([]);
const selectedOrgUnit = ref('');
const selectedRole = ref('user');
const isGenerating = ref(false);
const invitationResult = ref(null);
const invitations = ref([]);
const loading = ref(false);
const selectedInvitation = ref(null);
const qrCodeRef = ref(null);
const invitationQRRef = ref(null);

const loadOrgUnits = async () => {
  try {
    const response = await pythonAPI.getOrgUnits();
    orgUnits.value = response.data || response;
  } catch (error) {
    console.error('Ошибка загрузки организационных единиц:', error);
  }
};

const generateInvitation = async () => {
  if (!selectedOrgUnit.value) {
    alert('Выберите организационную единицу');
    return;
  }
  
  isGenerating.value = true;
  try {
    const response = await pythonAPI.generateInvitation({
      org_unit_id: selectedOrgUnit.value,
      role: selectedRole.value
    });
    
    invitationResult.value = response;
    
    // Генерируем QR-код
    await nextTick();
    if (qrCodeRef.value) {
      await QRCode.toCanvas(qrCodeRef.value, response.invitation_link, {
        width: 200,
        margin: 2
      });
    }
    
    // Перезагружаем список приглашений
    await loadInvitations();
  } catch (error) {
    console.error('Ошибка создания приглашения:', error);
    alert('Не удалось создать приглашение: ' + (error.message || 'Неизвестная ошибка'));
  } finally {
    isGenerating.value = false;
  }
};

const copyLink = () => {
  if (invitationResult.value) {
    navigator.clipboard.writeText(invitationResult.value.invitation_link);
    alert('Ссылка скопирована в буфер обмена');
  }
};

const downloadQR = async () => {
  if (!qrCodeRef.value) return;
  
  try {
    const dataURL = await QRCode.toDataURL(invitationResult.value.invitation_link, {
      width: 400,
      margin: 2
    });
    
    const link = document.createElement('a');
    link.download = `invitation-qr-${Date.now()}.png`;
    link.href = dataURL;
    link.click();
  } catch (error) {
    console.error('Ошибка скачивания QR-кода:', error);
  }
};

const loadInvitations = async () => {
  loading.value = true;
  try {
    const response = await pythonAPI.listInvitations();
    invitations.value = response.invitations || [];
  } catch (error) {
    console.error('Ошибка загрузки приглашений:', error);
  } finally {
    loading.value = false;
  }
};

const showInvitationDetails = async (invitation) => {
  selectedInvitation.value = invitation;
  
  await nextTick();
  if (invitationQRRef.value) {
    const link = getInvitationLink(invitation.token);
    try {
      await QRCode.toCanvas(invitationQRRef.value, link, {
        width: 150,
        margin: 2
      });
    } catch (error) {
      console.error('Ошибка генерации QR-кода:', error);
    }
  }
};

const getInvitationLink = (token) => {
  const baseUrl = window.location.origin;
  return `${baseUrl}/register?invitation=${token}`;
};

const copyInvitationLink = (token) => {
  const link = getInvitationLink(token);
  navigator.clipboard.writeText(link);
  alert('Ссылка скопирована в буфер обмена');
};

const downloadInvitationQR = async (token) => {
  const link = getInvitationLink(token);
  try {
    const dataURL = await QRCode.toDataURL(link, {
      width: 400,
      margin: 2
    });
    
    const downloadLink = document.createElement('a');
    downloadLink.download = `invitation-qr-${token}-${Date.now()}.png`;
    downloadLink.href = dataURL;
    downloadLink.click();
  } catch (error) {
    console.error('Ошибка скачивания QR-кода:', error);
  }
};

const formatDate = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleString('ru-RU');
};

onMounted(async () => {
  await loadOrgUnits();
  await loadInvitations();
});
</script>

<style scoped>
.invitations-panel {
  padding: 2rem;
}

h2, h3 {
  margin-bottom: 1rem;
}

.create-invitation-form {
  background: var(--bg-secondary);
  padding: 1.5rem;
  border-radius: 8px;
  margin-bottom: 2rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.form-control {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--background-color);
  color: var(--text-primary);
}

.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 500;
}

.btn-primary {
  background: var(--primary-color);
  color: white;
}

.btn-secondary {
  background: var(--bg-secondary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.invitation-result {
  background: var(--bg-secondary);
  padding: 1.5rem;
  border-radius: 8px;
  margin-bottom: 2rem;
}

.invitation-link,
.qr-code-container {
  margin-bottom: 1rem;
}

.invitation-link label,
.qr-code-container label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.link-container {
  display: flex;
  gap: 0.5rem;
}

.link-input {
  flex: 1;
  padding: 0.5rem;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--background-color);
  color: var(--text-primary);
}

.qr-code-display {
  margin: 1rem 0;
  padding: 1rem;
  background: white;
  border-radius: 8px;
  display: inline-block;
}

.invitations-list {
  background: var(--bg-secondary);
  padding: 1.5rem;
  border-radius: 8px;
}

.invitations-table {
  width: 100%;
  border-collapse: collapse;
}

.invitations-table th,
.invitations-table td {
  padding: 0.75rem;
  text-align: left;
  border-bottom: 1px solid var(--border-color);
}

.invitations-table th {
  font-weight: 600;
  background: var(--bg-tertiary);
}

.status-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.875rem;
}

.status-badge.active {
  background: #d4edda;
  color: #155724;
}

.status-badge.used {
  background: #f8d7da;
  color: #721c24;
}

.modal {
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
  background: var(--background-color);
  padding: 2rem;
  border-radius: 8px;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
}

.invitation-details p {
  margin-bottom: 0.5rem;
}

.invitation-link-section,
.qr-code-section {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border-color);
}

.qr-code-display-small {
  margin: 1rem 0;
  padding: 0.5rem;
  background: white;
  border-radius: 8px;
  display: inline-block;
}

.loading,
.no-invitations {
  text-align: center;
  padding: 2rem;
  color: var(--text-secondary);
}
</style>

