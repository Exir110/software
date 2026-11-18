<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

defineProps<{
  title: string
  overline?: string
  wide?: boolean
}>()

const emit = defineEmits<{ close: [] }>()
const root = ref<HTMLElement | null>(null)

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') {
    event.stopPropagation()
    emit('close')
  }
}

onMounted(async () => {
  document.addEventListener('keydown', onKeydown)
  await nextTick()
  const focusable = root.value?.querySelector<HTMLElement>(
    'input, select, textarea',
  )
  focusable?.focus()
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <div class="modal-backdrop" @click.self="emit('close')">
    <div ref="root" class="modal" :class="{ 'modal-wide': wide }" role="dialog" aria-modal="true" :aria-label="title">
      <div class="modal-heading">
        <div>
          <p v-if="overline" class="overline">{{ overline }}</p>
          <h2>{{ title }}</h2>
        </div>
        <button class="icon-button" type="button" aria-label="关闭" @click="emit('close')">×</button>
      </div>
      <slot />
    </div>
  </div>
</template>
