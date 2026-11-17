<script setup lang="ts">
import { reactive, ref } from 'vue'
import { request } from '../api/client'
import type { Knowledge, PracticeResult } from '../api/types'
import { notify } from '../stores/toast'
import ModalShell from './ModalShell.vue'

const props = defineProps<{ point: Knowledge }>()
const emit = defineEmits<{ close: []; saved: [result: PracticeResult] }>()

const form = reactive({
  minutes: 20,
  correct_count: 8,
  total_count: 10,
  self_rating: 3,
  note: '',
})
const saving = ref(false)

async function submit(): Promise<void> {
  if (form.total_count < 1) {
    notify('总题数至少为 1', 'error')
    return
  }
  if (form.correct_count > form.total_count) {
    notify('做对题数不能大于总题数', 'error')
    return
  }
  saving.value = true
  try {
    const result = await request<PracticeResult>(`/knowledge/${props.point.id}/practice`, {
      method: 'POST',
      body: {
        minutes: form.minutes,
        correct_count: form.correct_count,
        total_count: form.total_count,
        self_rating: form.self_rating,
        note: form.note.trim(),
      },
    })
    notify(result.message)
    emit('saved', result)
    emit('close')
  } catch (error) {
    notify((error as Error).message, 'error')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <ModalShell title="记录一次练习" :overline="point.subject" wide @close="emit('close')">
    <p class="dialog-lead">
      「{{ point.name }}」当前掌握度 {{ point.mastery }}%，已有 {{ point.questions }} 次练习记录。
    </p>
    <div class="form-row">
      <label>练习分钟<input v-model.number="form.minutes" type="number" min="1" max="720"></label>
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
      <label>做对题数<input v-model.number="form.correct_count" type="number" min="0"></label>
      <label>总题数<input v-model.number="form.total_count" type="number" min="1"></label>
    </div>
    <label>练习备注<textarea v-model="form.note" rows="2" maxlength="1000" placeholder="可选：错在哪里、下次注意什么"></textarea></label>
    <button class="primary-button full-button" type="button" :disabled="saving" @click="submit">
      {{ saving ? '正在保存…' : '保存练习记录' }}
    </button>
  </ModalShell>
</template>
