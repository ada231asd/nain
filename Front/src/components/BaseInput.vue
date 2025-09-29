<template>
  <div class="base-input">
    <label v-if="label" :for="inputId" class="base-input__label">
      {{ label }}
      <span v-if="required" class="base-input__required">*</span>
    </label>
    
    <div class="base-input__wrapper">
      <input
        :id="inputId"
        ref="inputRef"
        v-model="inputValue"
        :type="inputType"
        :placeholder="placeholder"
        :disabled="disabled"
        :readonly="readonly"
        :autocomplete="autocomplete"
        :autocorrect="autocorrect"
        :autocapitalize="autocapitalize"
        :spellcheck="spellcheck"
        class="base-input__field"
        :class="[
          `base-input__field--${size}`,
          { 
            'base-input__field--error': hasError,
            'base-input__field--success': hasSuccess,
            'base-input__field--focused': isFocused
          }
        ]"
        @input="handleInput"
        @focus="handleFocus"
        @blur="handleBlur"
        @keydown="handleKeydown"
      />
      
      <div v-if="icon" class="base-input__icon">
        <slot name="icon">
          <span class="base-input__icon-text">{{ icon }}</span>
        </slot>
      </div>
      
      <button
        v-if="clearable && inputValue"
        type="button"
        class="base-input__clear"
        @click="clearInput"
        aria-label="Очистить поле"
      >
        ✕
      </button>
    </div>
    
    <div v-if="hasError && errorMessage" class="base-input__error">
      {{ errorMessage }}
    </div>
    
    <div v-if="hasSuccess && successMessage" class="base-input__success">
      {{ successMessage }}
    </div>
    
    <div v-if="hint" class="base-input__hint">
      {{ hint }}
    </div>
    
    <div v-if="showCharacterCount" class="base-input__counter">
      {{ inputValue.length }}{{ maxlength ? `/${maxlength}` : '' }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch } from 'vue'

const props = defineProps({
  modelValue: {
    type: [String, Number],
    default: ''
  },
  label: {
    type: String,
    default: ''
  },
  placeholder: {
    type: String,
    default: ''
  },
  type: {
    type: String,
    default: 'text'
  },
  size: {
    type: String,
    default: 'medium',
    validator: (value) => ['small', 'medium', 'large'].includes(value)
  },
  required: {
    type: Boolean,
    default: false
  },
  disabled: {
    type: Boolean,
    default: false
  },
  readonly: {
    type: Boolean,
    default: false
  },
  clearable: {
    type: Boolean,
    default: false
  },
  maxlength: {
    type: [String, Number],
    default: null
  },
  minlength: {
    type: [String, Number],
    default: null
  },
  pattern: {
    type: String,
    default: ''
  },
  autocomplete: {
    type: String,
    default: 'off'
  },
  autocorrect: {
    type: String,
    default: 'off'
  },
  autocapitalize: {
    type: String,
    default: 'off'
  },
  spellcheck: {
    type: [String, Boolean],
    default: false
  },
  icon: {
    type: String,
    default: ''
  },
  error: {
    type: [String, Boolean],
    default: false
  },
  success: {
    type: [String, Boolean],
    default: false
  },
  hint: {
    type: String,
    default: ''
  },
  showCharacterCount: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'input', 'focus', 'blur', 'keydown', 'clear'])

const inputRef = ref(null)
const isFocused = ref(false)

const inputId = computed(() => `input-${Math.random().toString(36).substr(2, 9)}`)
const inputType = computed(() => props.type)
const inputValue = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const hasError = computed(() => !!props.error)
const hasSuccess = computed(() => !!props.success)
const errorMessage = computed(() => typeof props.error === 'string' ? props.error : '')
const successMessage = computed(() => typeof props.success === 'string' ? props.success : '')

const handleInput = (event) => {
  emit('input', event.target.value)
}

const handleFocus = (event) => {
  isFocused.value = true
  emit('focus', event)
}

const handleBlur = (event) => {
  isFocused.value = false
  emit('blur', event)
}

const handleKeydown = (event) => {
  emit('keydown', event)
}

const clearInput = () => {
  inputValue.value = ''
  emit('clear')
  nextTick(() => {
    inputRef.value?.focus()
  })
}

// Expose methods for parent components
defineExpose({
  focus: () => inputRef.value?.focus(),
  blur: () => inputRef.value?.blur(),
  select: () => inputRef.value?.select(),
  setSelectionRange: (start, end) => inputRef.value?.setSelectionRange(start, end)
})
</script>

<style scoped>
.base-input {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 100%;
}

.base-input__label {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  cursor: pointer;
  user-select: none;
}

.base-input__required {
  color: var(--danger-color);
  margin-left: 2px;
}

.base-input__wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.base-input__field {
  width: 100%;
  border: 2px solid var(--border-color);
  border-radius: 8px;
  background-color: var(--background-color);
  color: var(--text-primary);
  font-family: inherit;
  font-size: inherit;
  transition: all 0.2s ease;
  outline: none;
}

.base-input__field:focus {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.base-input__field--small {
  padding: 8px 12px;
  font-size: 14px;
  min-height: 36px;
}

.base-input__field--medium {
  padding: 12px 16px;
  font-size: 16px;
  min-height: 44px;
}

.base-input__field--large {
  padding: 16px 20px;
  font-size: 18px;
  min-height: 52px;
}

.base-input__field--error {
  border-color: var(--danger-color);
}

.base-input__field--error:focus {
  border-color: var(--danger-color);
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1);
}

.base-input__field--success {
  border-color: var(--success-color);
}

.base-input__field--success:focus {
  border-color: var(--success-color);
  box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.1);
}

.base-input__field--focused {
  border-color: var(--primary-color);
}

.base-input__field:disabled {
  background-color: var(--background-disabled);
  color: var(--text-disabled);
  cursor: not-allowed;
  opacity: 0.6;
}

.base-input__field:readonly {
  background-color: var(--background-readonly);
  cursor: default;
}

.base-input__icon {
  position: absolute;
  left: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  pointer-events: none;
}

.base-input__icon-text {
  font-size: 18px;
}

.base-input__field--small + .base-input__icon {
  left: 8px;
}

.base-input__field--large + .base-input__icon {
  left: 16px;
}

.base-input__field:has(+ .base-input__icon) {
  padding-left: 40px;
}

.base-input__field--small:has(+ .base-input__icon) {
  padding-left: 36px;
}

.base-input__field--large:has(+ .base-input__icon) {
  padding-left: 48px;
}

.base-input__clear {
  position: absolute;
  right: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border: none;
  background: none;
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: 50%;
  transition: all 0.2s ease;
  font-size: 14px;
}

.base-input__clear:hover {
  background-color: var(--background-hover);
  color: var(--text-primary);
}

.base-input__error {
  font-size: 12px;
  color: var(--danger-color);
  margin-top: 2px;
}

.base-input__success {
  font-size: 12px;
  color: var(--success-color);
  margin-top: 2px;
}

.base-input__hint {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 2px;
}

.base-input__counter {
  font-size: 12px;
  color: var(--text-secondary);
  text-align: right;
  margin-top: 2px;
}

/* Mobile optimizations */
@media (max-width: 768px) {
  .base-input__field--medium {
    padding: 10px 14px;
    font-size: 16px; /* Prevents zoom on iOS */
    min-height: 40px;
  }
  
  .base-input__field--large {
    padding: 14px 18px;
    font-size: 16px;
    min-height: 48px;
  }
}

/* Touch device optimizations */
@media (hover: none) and (pointer: coarse) {
  .base-input__field {
    min-height: 44px; /* Minimum touch target size */
  }
  
  .base-input__clear {
    min-width: 44px;
    min-height: 44px;
  }
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  .base-input__field {
    background-color: var(--background-dark);
    color: var(--text-primary-dark);
    border-color: var(--border-dark);
  }
  
  .base-input__field:focus {
    border-color: var(--primary-color);
  }
}
</style>
