<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { request } from '../api/client'
import type { Dashboard, Knowledge, PlanResponse, Task, TaskCompleteResult } from '../api/types'
import { notify } from '../stores/toast'
import { fmtShortDate, todayISO, weekdayLabel } from '../utils'
import CompleteTaskDialog from '../components/CompleteTaskDialog.vue'
import TaskDialog from '../components/TaskDialog.vue'

const emit = defineEmits<{ navigate: [page: string] }>()

const dashboard = ref<Dashboard | null>(null)
const knowledge = ref<Knowledge[]>([])
const loading = ref(true)
const loadError = ref('')
const aiBusy = ref(false)
const aiMessage = ref('')
const planGeneratedAt = ref('')
const showTaskDialog = ref(false)
const completing = ref<Task | null>(null)

async function load(): Promise<void> {
  loading.value = true
  loadError.value = ''
  try {
    const [dash, points] = await Promise.all([
      request<Dashboard>('/dashboard'),
      request<Knowledge[]>('/knowledge'),
    ])
    dashboard.value = dash
    knowledge.value = points
  } catch (error) {
    loadError.value = (error as Error).message
  } finally {
    loading.value = false
  }
}

onMounted(load)

const weak = computed(() => dashboard.value?.weak_points ?? [])
const todayTasks = computed(() => (dashboard.value?.tasks ?? []).slice(0, 4))
const chartPoints = computed(() => [...knowledge.value].sort((a, b) => a.mastery - b.mastery).slice(0, 5))
const weekly = computed(() => dashboard.value?.weekly ?? [])
const weekMax = computed(() => Math.max(...weekly.value.map((item) => item.minutes), 30))
const weekTotal = computed(() => weekly.value.reduce((sum, item) => sum + item.minutes, 0))
const today = todayISO()

const aiText = computed(() => {
  if (aiMessage.value) return aiMessage.value
  const first = weak.value[0]
  if (!first) return '完成第一个学习任务后，系统会结合练习记录给出建议。'
  return `当前最薄弱的是「${first.name}」，掌握度 ${first.mastery}%。建议今天优先安排一次专项练习，并记录正确率。`
})

function minutesText(minutes: number): string {
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`
}

function barHeight(minutes: number): string {
  return `${Math.max((minutes / weekMax.value) * 100, minutes > 0 ? 4 : 0)}%`
}

async function startTask(task: Task): Promise<void> {
  try {
    if (task.status === '进行中') {
      await request<Task>(`/tasks/${task.id}`, { method: 'PATCH', body: { status: '待开始' } })
      notify('已暂停任务')
    } else {
      await request<Task>(`/tasks/${task.id}/start`, { method: 'POST' })
      notify('已开始任务')
    }
    await load()
  } catch (error) {
    notify((error as Error).message, 'error')
  }
}

async function optimizePlan(): Promise<void> {
  aiBusy.value = true
  try {
    const result = await request<PlanResponse>('/ai/plan', { method: 'POST' })
    aiMessage.value = result.message
    planGeneratedAt.value = '刚刚生成'
    notify('AI 已重新安排今日计划')
    await load()
  } catch (error) {
    notify((error as Error).message, 'error')
  } finally {
    aiBusy.value = false
  }
}

async function onCompleted(_result: TaskCompleteResult): Promise<void> {
  completing.value = null
  await load()
}
</script>

<template>
  <div class="page-content">
    <div v-if="loading" class="loading-state">正在加载学习数据…</div>
    <div v-else-if="loadError" class="error-state">
      <p>{{ loadError }}</p>
      <button class="outline-button" type="button" @click="load">重试</button>
    </div>
    <template v-else-if="dashboard">
      <section class="hero-row">
        <div>
          <p class="overline">{{ weekdayLabel() }}，状态不错</p>
          <h1>把今天学明白，<em>上岸会更近。</em></h1>
          <p class="hero-subtitle">
            距离考试还有 <strong>{{ dashboard.days_to_exam }}</strong> 天，今日目标
            {{ dashboard.study_goal_minutes }} 分钟。
          </p>
        </div>
        <button class="primary-button" type="button" @click="showTaskDialog = true"><span>＋</span> 添加学习任务</button>
      </section>

      <section class="stats-grid">
        <article class="stat-card accent-card">
          <div class="stat-icon coral">◷</div>
          <div class="stat-label">今日学习时长</div>
          <strong>{{ minutesText(dashboard.today_minutes) }}</strong>
          <div class="stat-foot"><span class="muted-text">目标 {{ dashboard.study_goal_minutes }} 分钟</span></div>
        </article>
        <article class="stat-card">
          <div class="stat-icon mint">✓</div>
          <div class="stat-label">今日任务完成</div>
          <strong>{{ dashboard.today_completed }}<small> / {{ dashboard.today_total }}</small></strong>
          <div class="stat-foot"><span class="positive">{{ dashboard.completion_rate }}%</span> 完成率</div>
        </article>
        <article class="stat-card">
          <div class="stat-icon lavender">◔</div>
          <div class="stat-label">整体掌握度</div>
          <strong>{{ dashboard.average_mastery }}<small>%</small></strong>
          <div class="stat-foot"><span class="muted-text">基于 {{ knowledge.length }} 个知识点</span></div>
        </article>
        <article class="stat-card">
          <div class="stat-icon yellow">⚑</div>
          <div class="stat-label">连续学习</div>
          <strong>{{ dashboard.streak_days }}<small> 天</small></strong>
          <div class="stat-foot"><span class="muted-text">保持你的节奏</span></div>
        </article>
      </section>

      <section class="dashboard-grid">
        <article class="panel today-panel">
          <div class="panel-heading">
            <div>
              <p class="overline">Plan for today</p>
              <h2>今日任务</h2>
            </div>
            <button class="text-button" type="button" @click="emit('navigate', 'tasks')">查看全部 <span>→</span></button>
          </div>
          <div v-if="todayTasks.length" class="task-list">
            <div v-for="task in todayTasks" :key="task.id" class="task-row" :class="{ done: task.status === '已完成' }">
              <button
                class="task-check"
                :class="{ checked: task.status === '已完成' }"
                type="button"
                :aria-label="`完成${task.title}`"
                :disabled="task.status === '已完成'"
                @click="completing = task"
              >{{ task.status === '已完成' ? '✓' : '' }}</button>
              <div class="task-main">
                <div class="task-title-line">
                  <strong>{{ task.title }}</strong>
                  <span class="priority-dot" :class="task.priority === '高' ? 'high' : task.priority === '中' ? 'medium' : 'low'"></span>
                </div>
                <span>{{ task.category }} · {{ task.duration_minutes }} 分钟</span>
              </div>
              <div class="task-time">{{ task.start_time }}</div>
              <button
                v-if="task.status !== '已完成'"
                class="play-button"
                type="button"
                :title="task.status === '进行中' ? '暂停任务' : '开始任务'"
                @click="startTask(task)"
              >{{ task.status === '进行中' ? 'Ⅱ' : '▶' }}</button>
              <span v-else class="done-label">已完成</span>
            </div>
          </div>
          <div v-else class="empty-state">今天还没有任务，先添加一个吧。</div>
          <button class="add-task-row" type="button" @click="showTaskDialog = true"><span>＋</span> 添加一个任务</button>
        </article>

        <article class="panel ai-panel">
          <div class="ai-panel-top">
            <div class="ai-badge">✦</div>
            <div>
              <p class="overline">AI 学习教练</p>
              <h2>今天这样学更高效</h2>
            </div>
            <span class="live-dot">在线</span>
          </div>
          <div class="ai-message">{{ aiText }}</div>
          <div v-if="weak[0]" class="recommendation">
            <div class="recommendation-icon">↗</div>
            <div>
              <span>推荐优先级</span>
              <strong>{{ weak[0].name }} · {{ weak[0].mastery }}% 掌握</strong>
            </div>
            <button type="button" title="查看知识追踪" @click="emit('navigate', 'knowledge')">→</button>
          </div>
          <button class="ai-action" type="button" :disabled="aiBusy" @click="optimizePlan">
            {{ aiBusy ? '正在分析学习数据…' : '让 AI 重新安排今日计划' }} <span>✦</span>
          </button>
          <span class="ai-footnote">
            基于任务、掌握度与剩余备考时间生成{{ planGeneratedAt ? ` · ${planGeneratedAt}` : '' }}
          </span>
        </article>
      </section>

      <section class="lower-grid">
        <article class="panel mastery-panel">
          <div class="panel-heading">
            <div><p class="overline">Knowledge tracking</p><h2>知识掌握情况</h2></div>
            <button class="icon-button subtle" type="button" title="打开知识追踪" @click="emit('navigate', 'knowledge')">↗</button>
          </div>
          <div v-if="chartPoints.length" class="mastery-chart">
            <div class="chart-y"><span>100%</span><span>75%</span><span>50%</span><span>25%</span><span>0%</span></div>
            <div class="chart-body">
              <div class="grid-line" style="top: 0%"></div><div class="grid-line" style="top: 25%"></div><div class="grid-line" style="top: 50%"></div><div class="grid-line" style="top: 75%"></div><div class="grid-line" style="top: 100%"></div>
              <div class="bars">
                <div v-for="item in chartPoints" :key="item.id" class="bar-group">
                  <div class="bar-value">{{ item.mastery }}%</div>
                  <div class="bar-track">
                    <div
                      class="bar-fill"
                      :class="item.mastery < 50 ? 'weak' : item.mastery < 70 ? 'mid' : 'strong'"
                      :style="{ height: `${item.mastery}%` }"
                    ></div>
                  </div>
                  <span>{{ item.name.length > 5 ? item.name.slice(0, 5) + '…' : item.name }}</span>
                </div>
              </div>
            </div>
          </div>
          <div v-else class="empty-state">还没有知识点数据。</div>
          <div class="chart-legend">
            <span><i class="legend weak"></i>需要重点复习</span>
            <span><i class="legend mid"></i>正在巩固</span>
            <span><i class="legend strong"></i>掌握良好</span>
          </div>
        </article>

        <article class="panel streak-panel">
          <div class="panel-heading">
            <div><p class="overline">Weekly rhythm</p><h2>本周学习节奏</h2></div>
            <span class="week-label">{{ fmtShortDate(weekly[0]?.date) }} - {{ fmtShortDate(weekly[weekly.length - 1]?.date) }}</span>
          </div>
          <div class="week-chart">
            <div class="week-columns">
              <div v-for="item in weekly" :key="item.date" class="day-column">
                <div class="day-bar-track">
                  <div class="day-bar" :class="{ today: item.date === today }" :style="{ height: barHeight(item.minutes) }"></div>
                </div>
                <span :class="{ todayText: item.date === today }">{{ item.day }}</span>
              </div>
            </div>
            <div class="week-total">
              <strong>{{ (weekTotal / 60).toFixed(1) }}h</strong><span>本周已学习</span>
              <b>{{ dashboard.streak_days }} 天连续</b>
            </div>
          </div>
        </article>
      </section>
    </template>

    <TaskDialog v-if="showTaskDialog" :default-date="today" @close="showTaskDialog = false" @saved="load" />
    <CompleteTaskDialog
      v-if="completing"
      :task="completing"
      @close="completing = null"
      @completed="onCompleted"
    />
  </div>
</template>
