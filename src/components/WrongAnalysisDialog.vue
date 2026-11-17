<script setup lang="ts">
import type { WrongAnalysis } from '../api/types'
import ModalShell from './ModalShell.vue'

defineProps<{
  title: string
  analysis: WrongAnalysis
}>()

defineEmits<{ close: [] }>()
</script>

<template>
  <ModalShell title="AI 错题分析" overline="AI analysis" wide @close="$emit('close')">
    <p class="dialog-lead">{{ title }}</p>
    <div class="analysis-block">{{ analysis.analysis }}</div>
    <p class="analysis-subtitle">下一步建议</p>
    <ol class="analysis-list">
      <li v-for="(item, index) in analysis.suggestions" :key="index">{{ item }}</li>
    </ol>
    <p class="analysis-provider">生成方式：{{ analysis.provider === 'openai' ? '大模型' : '本地规则（未配置模型时的降级结果）' }}</p>
  </ModalShell>
</template>
