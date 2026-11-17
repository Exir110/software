<script setup lang="ts">
defineProps<{
  title: string
  overline?: string
  wide?: boolean
}>()

defineEmits<{ close: [] }>()
</script>

<template>
  <div class="modal-backdrop" @click.self="$emit('close')">
    <div class="modal" :class="{ 'modal-wide': wide }">
      <div class="modal-heading">
        <div>
          <p v-if="overline" class="overline">{{ overline }}</p>
          <h2>{{ title }}</h2>
        </div>
        <button class="icon-button" type="button" aria-label="关闭" @click="$emit('close')">×</button>
      </div>
      <slot />
    </div>
  </div>
</template>
