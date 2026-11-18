<script setup lang="ts">
import type { SummaryResponse } from '../api/types'
import ModalShell from './ModalShell.vue'

defineProps<{ result: SummaryResponse }>()
defineEmits<{ close: [] }>()
</script>

<template>
  <ModalShell title="今日学习总结" overline="Daily summary" @close="$emit('close')">
    <div class="analysis-block">{{ result.summary }}</div>
    <p class="analysis-provider">
      生成方式：{{ result.provider === 'openai' ? '大模型' : '本地规则（未配置模型时的降级结果）' }}
    </p>
    <button class="primary-button full-button" type="button" @click="$emit('close')">知道了</button>
  </ModalShell>
</template>
