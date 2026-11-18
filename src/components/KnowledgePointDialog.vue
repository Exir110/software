<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { request } from '../api/client'
import type { Knowledge } from '../api/types'
import { loadMeta, meta } from '../stores/meta'
import { notify } from '../stores/toast'
import ModalShell from './ModalShell.vue'

const emit = defineEmits<{ close: []; saved: [point: Knowledge] }>()

const form = reactive({
  subject_id: 0,
  name: '',
  chapter: '',
  importance: 3,
})
const loading = ref(true)
const saving = ref(false)

onMounted(async () => {
  try {
    await loadMeta()
  } catch (error) {
    notify((error as Error).message, 'error')
  } finally {
    loading.value = false
  }
  if (meta.subjects.length) form.subject_id = meta.subjects[0].id
})

async function submit(): Promise<void> {
  if (!form.subject_id) {
    notify('请选择科目', 'error')
    return
  }
  if (!form.name.trim()) {
    notify('请输入知识点名称', 'error')
    return
  }
  saving.value = true
  try {
    const point = await request<Knowledge>('/knowledge', {
      method: 'POST',
      body: {
        subject_id: form.subject_id,
        name: form.name.trim(),
        chapter: form.chapter.trim(),
        importance: form.importance,
        difficulty: 3,
      },
    })
    notify('知识点已创建，初始掌握度为 50%')
    emit('saved', point)
    emit('close')
  } catch (error) {
    notify((error as Error).message, 'error')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <ModalShell title="添加知识点" overline="Knowledge point" @close="emit('close')">
    <div v-if="loading" class="loading-state">正在加载科目…</div>
    <template v-else>
      <label>科目
        <select v-model="form.subject_id">
          <option v-for="subject in meta.subjects" :key="subject.id" :value="subject.id">{{ subject.name }}</option>
        </select>
      </label>
      <label>知识点名称<input v-model="form.name" maxlength="64" placeholder="例如：条件概率"></label>
      <label>所属章节<input v-model="form.chapter" maxlength="64" placeholder="例如：概率论 · 随机变量"></label>
      <label>重要度（1-5）<input v-model.number="form.importance" type="number" min="1" max="5"></label>
      <p class="dialog-lead">新知识点会为所有账号建立 50% 的初始掌握度，之后可通过记录练习更新。</p>
      <button class="primary-button full-button" type="button" :disabled="saving" @click="submit">
        {{ saving ? '正在保存…' : '创建知识点' }}
      </button>
    </template>
  </ModalShell>
</template>
