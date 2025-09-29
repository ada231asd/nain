<template>
  <button
    :class="[
      'base-button',
      `base-button--${variant}`,
      `base-button--${size}`,
      { 'base-button--loading': loading, 'base-button--disabled': disabled }
    ]"
    :disabled="disabled || loading"
    @click="handleClick"
  >
    <span v-if="loading" class="base-button__loader"></span>
    <slot v-else />
  </button>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  variant: {
    type: String,
    default: 'primary',
    validator: (value) => ['primary', 'secondary', 'success', 'danger', 'warning', 'outline'].includes(value)
  },
  size: {
    type: String,
    default: 'medium',
    validator: (value) => ['small', 'medium', 'large'].includes(value)
  },
  loading: {
    type: Boolean,
    default: false
  },
  disabled: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['click'])

const handleClick = (event) => {
  if (!props.loading && !props.disabled) {
    emit('click', event)
  }
}
</script>

<style scoped>
.base-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: none;
  border-radius: 8px;
  font-family: inherit;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  text-decoration: none;
  position: relative;
  min-width: 80px;
}

.base-button:focus {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}

.base-button--small {
  padding: 8px 16px;
  font-size: 14px;
  min-height: 36px;
}

.base-button--medium {
  padding: 12px 24px;
  font-size: 16px;
  min-height: 44px;
}

.base-button--large {
  padding: 16px 32px;
  font-size: 18px;
  min-height: 52px;
}

/* Primary variant */
.base-button--primary {
  background-color: var(--primary-color);
  color: white;
}

.base-button--primary:hover:not(:disabled) {
  background-color: var(--primary-dark);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

/* Secondary variant */
.base-button--secondary {
  background-color: var(--secondary-color);
  color: white;
}

.base-button--secondary:hover:not(:disabled) {
  background-color: var(--secondary-dark);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

/* Success variant */
.base-button--success {
  background-color: var(--success-color);
  color: white;
}

.base-button--success:hover:not(:disabled) {
  background-color: var(--success-dark);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

/* Danger variant */
.base-button--danger {
  background-color: var(--danger-color);
  color: white;
}

.base-button--danger:hover:not(:disabled) {
  background-color: var(--danger-dark);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

/* Warning variant */
.base-button--warning {
  background-color: var(--warning-color);
  color: white;
}

.base-button--warning:hover:not(:disabled) {
  background-color: var(--warning-dark);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

/* Outline variant */
.base-button--outline {
  background-color: transparent;
  color: var(--primary-color);
  border: 2px solid var(--primary-color);
}

.base-button--outline:hover:not(:disabled) {
  background-color: var(--primary-color);
  color: white;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

/* Loading state */
.base-button--loading {
  cursor: wait;
}

.base-button__loader {
  width: 16px;
  height: 16px;
  border: 2px solid transparent;
  border-top: 2px solid currentColor;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Disabled state */
.base-button--disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none !important;
  box-shadow: none !important;
}

/* Mobile optimizations */
@media (max-width: 768px) {
  .base-button--medium {
    padding: 10px 20px;
    font-size: 15px;
    min-height: 40px;
  }
  
  .base-button--large {
    padding: 14px 28px;
    font-size: 16px;
    min-height: 48px;
  }
}

/* Touch device optimizations */
@media (hover: none) and (pointer: coarse) {
  .base-button:hover:not(:disabled) {
    transform: none;
    box-shadow: none;
  }
  
  .base-button:active:not(:disabled) {
    transform: scale(0.98);
  }
}
</style>
