<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { request } from '../api/client'
import type { WrongQuestion } from '../api/types'
import { loadMeta, meta, pointsOf } from '../stores/meta'
import { notify } from '../stores/toast'
import ModalShell from './ModalShell.vue'

const emit = defineEmits<{ close: []; saved: [question: WrongQuestion] }>()

const form = reactive({
  title: '',
  subject_id: 0,
  knowledge_point_id: null as number | null,
  source: '',
  error_type: '',
})
const loadingMeta = ref(true)
const saving = ref(false)
const points = computed(() => pointsOf(form.subject_id || null))

onMounted(async () => {
  try {
    await loadMeta()
  } catch (error) {
    notify((error as Error).message, 'error')
  } finally {
    loadingMeta.value = false
  }
  if (meta.subjects.length) form.subject_id = meta.subjects[0].id
})

watch(
  () => form.subject_id,
  () => {
    if (
      form.knowledge_point_id !== null &&
      !points.value.some((point) => point.id === form.knowledge_point_id)
    ) {
      form.knowledge_point_id = null
    }
  },
)

async function submit(): Promise<void> {
  if (!form.title.trim()) {
    notify('请输入错题标题', 'error')
    return
  }
  if (!form.subject_id) {
    notify('请选择科目', 'error')
    return
  }
  saving.value = true
  try {
    const question = await request<WrongQuestion>('/wrong-questions', {
      method: 'POST',
      body: {
        title: form.title.trim(),
        subject_id: form.subject_id,
        knowledge_point_id: form.knowledge_point_id,
        source: form.source.trim(),
        error_type: form.error_type.trim(),
      },
    })
    notify('错题已录入')
    emit('saved', question)
    emit('close')
  } catch (error) {
    notify((error as Error).message, 'error')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <ModalShell title="录入错题" overline="Error review" wide @close="emit('close')">
    <div v-if="loadingMeta" class="loading-state">正在加载科目…</div>
    <template v-else>
      <label>题目 / 考点<input v-model="form.title" maxlength="256" placeholder="例如：二重积分换元后的积分区域判断"></label>
      <div class="form-row">
        <label>科目
          <select v-model="form.subject_id">
            <option v-for="subject in meta.subjects" :key="subject.id" :value="subject.id">{{ subject.name }}</option>
          </select>
        </label>
        <label>关联知识点
          <select v-model="form.knowledge_point_id">
            <option :value="null">不关联知识点</option>
            <option v-for="point in points" :key="point.id" :value="point.id">{{ point.name }}</option>
          </select>
        </label>
      </div>
      <div class="form-row">
        <label>来源<input v-model="form.source" maxlength="64" placeholder="例如：2019 真题"></label>
        <label>错误类型<input v-model="form.error_type" maxlength="64" placeholder="例如：审题不完整"></label>
      </div>
      <button class="primary-button full-button" type="button" :disabled="saving" @click="submit">
        {{ saving ? '正在保存…' : '保存错题' }}
      </button>
    </template>
  </ModalShell>
</template>
