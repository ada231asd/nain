    <template>
  <div v-if="isVisible" class="modal-overlay" @click="$emit('close')">
    <div class="modal-content" @click.stop>
      <h2>Добавить адрес</h2>
      <div class="form">
        <input v-model="street" placeholder="Улица" class="input" />
        <input v-model="house" placeholder="Дом" class="input" />
        <input v-model="city" placeholder="Город" class="input" />
        <input v-model="postal" placeholder="Индекс" class="input" />
      </div>
      <div class="actions" style="margin-top: 12px; display: flex; gap: 8px;">
        <button class="btn-primary" @click="save">Сохранить</button>
        <button class="btn-close" @click="$emit('close')">Закрыть</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  isVisible: { type: Boolean, default: false }
})

const emit = defineEmits(['close', 'address-added'])

const street = ref('')
const house = ref('')
const city = ref('')
const postal = ref('')

const save = () => {
  emit('address-added', {
    street: street.value || null,
    house: house.value || null,
    city: city.value || null,
    postal_code: postal.value || null
  })
}
</script>
