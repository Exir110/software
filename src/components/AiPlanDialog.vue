<script setup lang="ts">
import type { PlanResponse } from '../api/types'
import ModalShell from './ModalShell.vue'

defineProps<{
  result: PlanResponse
  applying?: boolean
}>()

const emit = defineEmits<{ close: []; apply: [] }>()
</script>

<template>
  <ModalShell title="AI 计划预览" overline="Plan preview" wide @close="emit('close')">
    <div class="plan-provider">
      <span class="provider-badge">{{ result.provider === 'openai' ? '大模型' : '本地规则' }}</span>
      <span class="muted-text">预览不会修改任务；点击“应用计划”后才会写入时间与优先级。</span>
    </div>
    <p class="dialog-lead">{{ result.message }}</p>

    <div v-if="result.recommendations.length" class="ai-plan-list">
      <div v-for="item in result.recommendations" :key="item.task_id" class="ai-plan-row">
        <span class="plan-time">{{ item.start_time }}</span>
        <div class="plan-copy">
          <strong>{{ item.title }}</strong>
          <small>{{ item.duration_minutes }} 分钟 · {{ item.priority }}优先级 · {{ item.reason }}</small>
        </div>
      </div>
    </div>
    <div v-else class="empty-state">今天没有可排入的任务。</div>

    <div v-if="result.deferred.length" class="deferred-block">
      <p class="analysis-subtitle">未排入今天（{{ result.deferred.length }} 个）</p>
      <div v-for="item in result.deferred" :key="item.task_id" class="deferred-row">
        <strong>{{ item.title }}</strong>
        <small>{{ item.reason }}</small>
      </div>
    </div>

    <ul v-if="result.warnings.length" class="warning-list">
      <li v-for="(warning, index) in result.warnings" :key="index">{{ warning }}</li>
    </ul>

    <div class="modal-actions">
      <button class="outline-button" type="button" @click="emit('close')">取消</button>
      <button
        class="primary-button"
        type="button"
        :disabled="applying || !result.recommendations.length"
        @click="emit('apply')"
      >{{ applying ? '正在应用…' : '应用计划' }}</button>
    </div>
  </ModalShell>
</template>
