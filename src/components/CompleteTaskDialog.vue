<script setup lang="ts">
import { reactive, ref } from 'vue'
import { request } from '../api/client'
import type { Task, TaskCompleteResult } from '../api/types'
import { notify } from '../stores/toast'
import ModalShell from './ModalShell.vue'

const props = defineProps<{ task: Task }>()
const emit = defineEmits<{ close: []; completed: [result: TaskCompleteResult] }>()

const form = reactive({
  minutes: props.task.duration_minutes,
  correct_count: '' as string,
  total_count: '' as string,
  self_rating: 3,
  note: '',
})
const saving = ref(false)

async function submit(): Promise<void> {
  const hasCounts = form.correct_count !== '' || form.total_count !== ''
  if (hasCounts && (form.correct_count === '' || form.total_count === '')) {
    notify('做对题数和总题数需要同时填写', 'error')
    return
  }
  const correct = hasCounts ? Number(form.correct_count) : null
  const total = hasCounts ? Number(form.total_count) : null
  if (hasCounts && (correct === null || total === null || correct > total)) {
    notify('做对题数不能大于总题数', 'error')
    return
  }
  saving.value = true
  try {
    const result = await request<TaskCompleteResult>(`/tasks/${props.task.id}/complete`, {
      method: 'POST',
      body: {
        minutes: form.minutes,
        correct_count: correct,
        total_count: total,
        self_rating: form.self_rating,
        note: form.note.trim(),
      },
    })
    notify(result.message)
    emit('completed', result)
    emit('close')
  } catch (error) {
    notify((error as Error).message, 'error')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <ModalShell title="完成学习任务" overline="Study record" wide @close="emit('close')">
    <p class="dialog-lead">
      「{{ task.title }}」完成后会写入学习记录。
      <template v-if="task.knowledge_point_id">并按正确率和自评更新「{{ task.knowledge_point }}」的掌握度。</template>
      <template v-else>该任务未关联知识点，不会更新掌握度。</template>
    </p>
    <div class="form-row">
      <label>实际学习分钟<input v-model.number="form.minutes" type="number" min="1" max="720"></label>
      <label>自评掌握（1-5）
        <select v-model.number="form.self_rating">
          <option :value="1">1 · 完全没懂</option>
          <option :value="2">2 · 比较模糊</option>
          <option :value="3">3 · 基本掌握</option>
          <option :value="4">4 · 比较熟练</option>
          <option :value="5">5 · 非常熟练</option>
        </select>
      </label>
    </div>
    <div class="form-row">
      <label>做对题数（可选）<input v-model="form.correct_count" type="number" min="0" placeholder="例如：9"></label>
      <label>总题数（可选）<input v-model="form.total_count" type="number" min="0" placeholder="例如：10"></label>
    </div>
    <label>学习备注<textarea v-model="form.note" rows="2" maxlength="1000" placeholder="可选：记录本次的收获或问题"></textarea></label>
    <button class="primary-button full-button" type="button" :disabled="saving" @click="submit">
      {{ saving ? '正在保存…' : '完成并保存记录' }}
    </button>
  </ModalShell>
</template>
