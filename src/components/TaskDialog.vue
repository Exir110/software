<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { request } from '../api/client'
import type { Priority, Task, TaskPayload, TaskUpdatePayload } from '../api/types'
import { loadMeta, meta, pointsOf } from '../stores/meta'
import { notify } from '../stores/toast'
import ModalShell from './ModalShell.vue'

const props = defineProps<{
  task?: Task | null
  defaultDate?: string
}>()

const emit = defineEmits<{ close: []; saved: [task: Task] }>()

function todayISO(): string {
  const now = new Date()
  const offset = now.getTimezoneOffset()
  return new Date(now.getTime() - offset * 60_000).toISOString().slice(0, 10)
}

const form = reactive({
  title: '',
  subject_id: 0,
  knowledge_point_id: null as number | null,
  scheduled_date: props.defaultDate ?? todayISO(),
  start_time: '09:00',
  duration_minutes: 45,
  priority: '中' as Priority,
  note: '',
})

const points = computed(() => pointsOf(form.subject_id || null))
const loadingMeta = ref(true)
const saving = ref(false)

onMounted(async () => {
  try {
    await loadMeta()
  } catch (error) {
    notify((error as Error).message, 'error')
  } finally {
    loadingMeta.value = false
  }
  if (props.task) {
    Object.assign(form, {
      title: props.task.title,
      subject_id: props.task.subject_id,
      knowledge_point_id: props.task.knowledge_point_id,
      scheduled_date: props.task.scheduled_date,
      start_time: props.task.start_time,
      duration_minutes: props.task.duration_minutes,
      priority: props.task.priority,
      note: props.task.note,
    })
  } else if (meta.subjects.length) {
    form.subject_id = meta.subjects[0].id
  }
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

async function save(): Promise<void> {
  if (!form.title.trim()) {
    notify('请输入任务名称', 'error')
    return
  }
  if (!form.subject_id) {
    notify('请选择科目', 'error')
    return
  }
  saving.value = true
  try {
    let saved: Task
    if (props.task) {
      const payload: TaskUpdatePayload = {
        title: form.title.trim(),
        subject_id: form.subject_id,
        knowledge_point_id: form.knowledge_point_id,
        scheduled_date: form.scheduled_date,
        start_time: form.start_time,
        duration_minutes: form.duration_minutes,
        priority: form.priority,
        note: form.note.trim(),
      }
      saved = await request<Task>(`/tasks/${props.task.id}`, { method: 'PATCH', body: payload })
    } else {
      const payload: TaskPayload = {
        title: form.title.trim(),
        subject_id: form.subject_id,
        knowledge_point_id: form.knowledge_point_id,
        scheduled_date: form.scheduled_date,
        start_time: form.start_time,
        duration_minutes: form.duration_minutes,
        priority: form.priority,
        note: form.note.trim(),
      }
      saved = await request<Task>('/tasks', { method: 'POST', body: payload })
    }
    notify(props.task ? '任务已更新' : '任务已加入计划')
    emit('saved', saved)
    emit('close')
  } catch (error) {
    notify((error as Error).message, 'error')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <ModalShell :title="task ? '编辑学习任务' : '添加学习任务'" overline="Study task" wide @close="emit('close')">
    <div v-if="loadingMeta" class="loading-state">正在加载科目…</div>
    <template v-else>
      <label>任务名称<input v-model="form.title" maxlength="128" placeholder="例如：概率论条件概率"></label>
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
        <label>日期<input v-model="form.scheduled_date" type="date"></label>
        <label>开始时间<input v-model="form.start_time" type="time"></label>
      </div>
      <div class="form-row">
        <label>预计时长（分钟）<input v-model.number="form.duration_minutes" type="number" min="5" max="480" step="5"></label>
        <label>优先级
          <select v-model="form.priority">
            <option value="高">高</option>
            <option value="中">中</option>
            <option value="低">低</option>
          </select>
        </label>
      </div>
      <label>备注<textarea v-model="form.note" rows="2" maxlength="1000" placeholder="可选：本次学习要完成的内容"></textarea></label>
      <button class="primary-button full-button" type="button" :disabled="saving" @click="save">
        {{ saving ? '正在保存…' : task ? '保存修改' : '加入计划' }}
      </button>
    </template>
  </ModalShell>
</template>
