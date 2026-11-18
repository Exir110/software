<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { request } from '../api/client'
import type { Task, TaskCompleteResult, TaskStatus } from '../api/types'
import { loadMeta, meta } from '../stores/meta'
import { notify } from '../stores/toast'
import { todayISO } from '../utils'
import CompleteTaskDialog from '../components/CompleteTaskDialog.vue'
import TaskDialog from '../components/TaskDialog.vue'

const tasks = ref<Task[]>([])
const overdue = ref<Task[]>([])
const carrying = ref(false)
const loading = ref(true)
const loadError = ref('')
const taskFilter = ref<'全部' | TaskStatus>('全部')
const selectedSubject = ref(0)
const selectedDate = ref(todayISO())
const showTaskDialog = ref(false)
const editing = ref<Task | null>(null)
const completing = ref<Task | null>(null)

async function load(): Promise<void> {
  loading.value = true
  loadError.value = ''
  try {
    await loadMeta()
    const [list, overdueList] = await Promise.all([
      request<Task[]>(`/tasks?date=${selectedDate.value}`),
      request<Task[]>('/tasks/overdue'),
    ])
    tasks.value = list
    overdue.value = overdueList
  } catch (error) {
    loadError.value = (error as Error).message
  } finally {
    loading.value = false
  }
}

onMounted(load)

const filteredTasks = computed(() =>
  tasks.value.filter((task) => {
    if (taskFilter.value !== '全部' && task.status !== taskFilter.value) return false
    if (selectedSubject.value && task.subject_id !== selectedSubject.value) return false
    return true
  }),
)
const totalMinutes = computed(() =>
  filteredTasks.value
    .filter((task) => task.status !== '已完成')
    .reduce((sum, task) => sum + task.duration_minutes, 0),
)

function openCreate(): void {
  editing.value = null
  showTaskDialog.value = true
}

function openEdit(task: Task): void {
  editing.value = task
  showTaskDialog.value = true
}

async function onSaved(task: Task): Promise<void> {
  selectedDate.value = task.scheduled_date
  await load()
}

async function startTask(task: Task): Promise<void> {
  try {
    if (task.status === '进行中') {
      await request<Task>(`/tasks/${task.id}`, { method: 'PATCH', body: { status: '待开始' } })
      notify('任务已暂停')
    } else {
      await request<Task>(`/tasks/${task.id}/start`, { method: 'POST' })
      notify('任务已开始')
    }
    await load()
  } catch (error) {
    notify((error as Error).message, 'error')
  }
}

async function resetTask(task: Task): Promise<void> {
  if (!window.confirm(`把「${task.title}」重置为待开始？完成后会新增一条学习记录。`)) return
  try {
    await request<Task>(`/tasks/${task.id}`, { method: 'PATCH', body: { status: '待开始' } })
    notify('任务已重置为待开始')
    await load()
  } catch (error) {
    notify((error as Error).message, 'error')
  }
}

async function removeTask(task: Task): Promise<void> {
  if (!window.confirm(`删除任务「${task.title}」？已产生的学习记录会保留。`)) return
  try {
    await request<void>(`/tasks/${task.id}`, { method: 'DELETE' })
    notify('任务已删除')
    await load()
  } catch (error) {
    notify((error as Error).message, 'error')
  }
}

async function onCompleted(_result: TaskCompleteResult): Promise<void> {
  completing.value = null
  await load()
}

async function onDateChange(): Promise<void> {
  await load()
}

async function carryOver(): Promise<void> {
  carrying.value = true
  try {
    const moved = await request<Task[]>('/tasks/carry-over', { method: 'POST' })
    notify(moved.length ? `已顺延 ${moved.length} 个任务到今天` : '没有可顺延的任务')
    await load()
  } catch (error) {
    notify((error as Error).message, 'error')
  } finally {
    carrying.value = false
  }
}
</script>

<template>
  <div class="page-content inner-page">
    <section class="page-title-row">
      <div>
        <p class="overline">Study queue</p>
        <h1>今日任务</h1>
        <p>把任务拆小，把进度做实。</p>
      </div>
      <button class="primary-button" type="button" @click="openCreate"><span>＋</span> 新建任务</button>
    </section>

    <section class="filter-bar">
      <div class="segmented">
        <button
          v-for="filter in ['全部', '待开始', '进行中', '已完成'] as const"
          :key="filter"
          :class="{ active: taskFilter === filter }"
          type="button"
          @click="taskFilter = filter"
        >{{ filter }}</button>
      </div>
      <select v-model.number="selectedSubject" aria-label="筛选科目">
        <option :value="0">全部科目</option>
        <option v-for="subject in meta.subjects" :key="subject.id" :value="subject.id">{{ subject.name }}</option>
      </select>
      <input v-model="selectedDate" class="date-filter" type="date" aria-label="选择日期" @change="onDateChange">
      <span class="filter-summary">{{ filteredTasks.length }} 个任务 · 待完成预计 {{ totalMinutes }} 分钟</span>
    </section>

    <section v-if="overdue.length" class="overdue-banner">
      <div>
        <strong>{{ overdue.length }} 个任务已逾期</strong>
        <span>最早的是「{{ overdue[0].title }}」（{{ overdue[0].scheduled_date }}）。顺延会自动安排不冲突的时间。</span>
      </div>
      <button class="primary-button" type="button" :disabled="carrying" @click="carryOver">
        {{ carrying ? '正在顺延…' : '顺延到今天' }}
      </button>
    </section>

    <section class="panel full-panel">
      <div v-if="loading" class="loading-state">正在加载任务…</div>
      <div v-else-if="loadError" class="error-state">
        <p>{{ loadError }}</p>
        <button class="outline-button" type="button" @click="load">重试</button>
      </div>
      <template v-else>
        <div v-for="task in filteredTasks" :key="task.id" class="task-detail-row" :class="{ done: task.status === '已完成' }">
          <button
            class="task-check large"
            :class="{ checked: task.status === '已完成' }"
            type="button"
            :disabled="task.status === '已完成'"
            :title="task.status === '已完成' ? '已完成；如需重做请使用右侧“重置”' : '完成任务'"
            :aria-label="`完成${task.title}`"
            @click="completing = task"
          >{{ task.status === '已完成' ? '✓' : '' }}</button>
          <div class="task-main">
            <div class="task-title-line">
              <strong>{{ task.title }}</strong>
              <span class="tag" :class="task.priority === '高' ? 'tag-red' : task.priority === '中' ? 'tag-yellow' : 'tag-green'">{{ task.priority }}优先级</span>
              <span class="tag tag-plain">{{ task.status }}</span>
            </div>
            <span>{{ task.category }} · 预计 {{ task.duration_minutes }} 分钟<span v-if="task.mastery !== null"> · 掌握度 {{ task.mastery }}%</span></span>
            <p v-if="task.note">{{ task.note }}</p>
          </div>
          <span class="detail-time">{{ task.start_time }}</span>
          <div class="row-actions">
            <button v-if="task.status !== '已完成'" class="outline-button" type="button" @click="startTask(task)">
              {{ task.status === '进行中' ? '暂停' : '开始' }}
            </button>
            <button v-if="task.status !== '已完成'" class="outline-button" type="button" @click="completing = task">完成</button>
            <button v-else class="outline-button" type="button" @click="resetTask(task)">重置</button>
            <button class="outline-button" type="button" @click="openEdit(task)">编辑</button>
            <button class="outline-button danger-button" type="button" @click="removeTask(task)">删除</button>
          </div>
        </div>
        <div v-if="!filteredTasks.length" class="empty-state">没有符合当前筛选条件的任务。</div>
      </template>
    </section>

    <TaskDialog
      v-if="showTaskDialog"
      :task="editing"
      :default-date="selectedDate"
      @close="showTaskDialog = false"
      @saved="onSaved"
    />
    <CompleteTaskDialog
      v-if="completing"
      :task="completing"
      @close="completing = null"
      @completed="onCompleted"
    />
  </div>
</template>

