<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ApiError, request } from '../api/client'
import type { Goal } from '../api/types'
import { notify } from '../stores/toast'
import { todayISO } from '../utils'
import ModalShell from './ModalShell.vue'

const emit = defineEmits<{ close: []; saved: [] }>()

const form = reactive({
  exam_date: '',
  target_school: '',
  target_major: '',
  target_score: 380,
  daily_minutes: 180,
})
const daysRemaining = ref(0)
const loading = ref(true)
const saving = ref(false)

function defaultExamDate(): string {
  const today = new Date()
  const candidate = new Date(today.getFullYear(), 11, 19)
  if (candidate <= today) candidate.setFullYear(candidate.getFullYear() + 1)
  return candidate.toISOString().slice(0, 10)
}

function syncDays(): void {
  if (!form.exam_date) {
    daysRemaining.value = 0
    return
  }
  const target = new Date(`${form.exam_date}T00:00:00`)
  const today = new Date()
  const diff = Math.ceil((target.getTime() - new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime()) / 86_400_000)
  daysRemaining.value = Math.max(diff, 0)
}

onMounted(async () => {
  try {
    const goal = await request<Goal>('/goals/current')
    Object.assign(form, {
      exam_date: goal.exam_date,
      target_school: goal.target_school,
      target_major: goal.target_major,
      target_score: goal.target_score,
      daily_minutes: goal.daily_minutes,
    })
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 404) {
      notify((error as Error).message, 'error')
    }
    form.exam_date = defaultExamDate()
  } finally {
    loading.value = false
    syncDays()
  }
})

async function save(): Promise<void> {
  if (!form.exam_date) {
    notify('请选择考试日期', 'error')
    return
  }
  if (form.exam_date < todayISO()) {
    notify('考试日期不能早于今天', 'error')
    return
  }
  saving.value = true
  try {
    await request<Goal>('/goals/current', {
      method: 'PUT',
      body: {
        exam_date: form.exam_date,
        target_school: form.target_school.trim(),
        target_major: form.target_major.trim(),
        target_score: form.target_score,
        daily_minutes: form.daily_minutes,
      },
    })
    notify('备考目标已保存')
    emit('saved')
    emit('close')
  } catch (error) {
    notify((error as Error).message, 'error')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <ModalShell title="备考目标" overline="Your goal" @close="emit('close')">
    <div v-if="loading" class="loading-state">正在读取目标…</div>
    <template v-else>
      <div class="goal-visual"><strong>{{ daysRemaining }}</strong><span>天后考试</span></div>
      <label>考试日期<input v-model="form.exam_date" type="date" :min="todayISO()" @change="syncDays"></label>
      <div class="form-row">
        <label>目标院校<input v-model="form.target_school" maxlength="128" placeholder="例如：某某大学"></label>
        <label>目标专业<input v-model="form.target_major" maxlength="128" placeholder="例如：计算机科学与技术"></label>
      </div>
      <div class="form-row">
        <label>目标总分<input v-model.number="form.target_score" type="number" min="100" max="500" step="5"></label>
        <label>每日学习分钟<input v-model.number="form.daily_minutes" type="number" min="30" max="720" step="15"></label>
      </div>
      <button class="primary-button full-button" type="button" :disabled="saving" @click="save">
        {{ saving ? '正在保存…' : '保存目标' }}
      </button>
    </template>
  </ModalShell>
</template>
