<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { request } from '../api/client'
import type { Plan, PlanResponse, WeeklyGoal } from '../api/types'
import { notify } from '../stores/toast'
import { fmtShortDate } from '../utils'

const plan = ref<Plan | null>(null)
const loading = ref(true)
const loadError = ref('')
const aiBusy = ref(false)
const aiMessage = ref('')
const showGoalForm = ref(false)
const newGoal = reactive({ title: '', target_minutes: 60 })
const savingGoal = ref(false)

async function load(): Promise<void> {
  loading.value = true
  loadError.value = ''
  try {
    plan.value = await request<Plan>('/plan')
  } catch (error) {
    loadError.value = (error as Error).message
  } finally {
    loading.value = false
  }
}

onMounted(load)

const phases = computed(() => plan.value?.phases ?? [])
const week = computed(() => plan.value?.week ?? null)
const doneGoals = computed(() => week.value?.goals.filter((goal) => goal.status === '已完成').length ?? 0)
const totalGoals = computed(() => week.value?.goals.length ?? 0)
const goalRate = computed(() => (totalGoals.value ? Math.round((doneGoals.value / totalGoals.value) * 100) : 0))

function phaseClass(status: string): string {
  if (status === 'done') return 'done-phase'
  if (status === 'current') return 'current-phase'
  return ''
}

function range(start: string, end: string): string {
  const format = (iso: string) => {
    const date = new Date(`${iso}T00:00:00`)
    return `${date.getMonth() + 1}.${String(date.getDate()).padStart(2, '0')}`
  }
  return `${format(start)} - ${format(end)}`
}

async function optimize(): Promise<void> {
  aiBusy.value = true
  try {
    const result = await request<PlanResponse>('/ai/plan', { method: 'POST' })
    aiMessage.value = result.message
    notify('AI 已重新计算任务优先级与时间')
    await load()
  } catch (error) {
    notify((error as Error).message, 'error')
  } finally {
    aiBusy.value = false
  }
}

async function toggleGoal(goal: WeeklyGoal): Promise<void> {
  const next = goal.status === '已完成' ? '待开始' : '已完成'
  try {
    const updated = await request<WeeklyGoal>(`/plan/goals/${goal.id}`, {
      method: 'PATCH',
      body: { status: next },
    })
    Object.assign(goal, updated)
  } catch (error) {
    notify((error as Error).message, 'error')
  }
}

async function addGoal(): Promise<void> {
  if (!newGoal.title.trim()) {
    notify('请输入周目标内容', 'error')
    return
  }
  savingGoal.value = true
  try {
    await request<WeeklyGoal>('/plan/goals', {
      method: 'POST',
      body: { title: newGoal.title.trim(), target_minutes: newGoal.target_minutes },
    })
    notify('周目标已添加')
    newGoal.title = ''
    newGoal.target_minutes = 60
    showGoalForm.value = false
    await load()
  } catch (error) {
    notify((error as Error).message, 'error')
  } finally {
    savingGoal.value = false
  }
}

async function removeGoal(goal: WeeklyGoal): Promise<void> {
  if (!window.confirm(`删除周目标「${goal.title}」？`)) return
  try {
    await request<void>(`/plan/goals/${goal.id}`, { method: 'DELETE' })
    if (plan.value) plan.value.week.goals = plan.value.week.goals.filter((item) => item.id !== goal.id)
    notify('周目标已删除')
  } catch (error) {
    notify((error as Error).message, 'error')
  }
}
</script>

<template>
  <div class="page-content inner-page">
    <section class="page-title-row">
      <div>
        <p class="overline">Exam roadmap</p>
        <h1>备考计划</h1>
        <p>从现在到上岸，每一个阶段都看得见。</p>
      </div>
      <button class="primary-button" type="button" :disabled="aiBusy" @click="optimize">
        <span>✦</span> {{ aiBusy ? '正在重排…' : 'AI 优化计划' }}
      </button>
    </section>

    <div v-if="loading" class="loading-state">正在加载备考计划…</div>
    <div v-else-if="loadError" class="error-state">
      <p>{{ loadError }}</p>
      <button class="outline-button" type="button" @click="load">重试</button>
    </div>
    <template v-else-if="plan">
      <section class="timeline panel">
        <div class="timeline-header">
          <div>
            <span class="eyebrow">{{ plan.exam_date ? `${plan.exam_date.slice(0, 4)} 考研` : '备考计划' }}</span>
            <h2>数学一 · 英语一 · 政治 · 408</h2>
          </div>
          <span class="goal-date">
            {{ plan.exam_date ? `考试日 ${plan.exam_date.split('-').join('.')}` : '尚未设置考试日期' }}
            · 剩余 {{ plan.days_remaining }} 天
          </span>
        </div>
        <div v-if="phases.length" class="timeline-track">
          <div v-for="phase in phases" :key="phase.index" class="phase" :class="phaseClass(phase.status)">
            <span>{{ String(phase.index).padStart(2, '0') }}</span>
            <strong>{{ phase.name }}</strong>
            <small>{{ range(phase.start, phase.end) }}</small>
            <i v-if="phase.status === 'current'">进行中</i>
            <i v-else-if="phase.status === 'done'" class="phase-done">已完成</i>
          </div>
        </div>
        <div v-else class="empty-state">设置考试目标后会自动生成阶段时间轴。</div>
      </section>

      <section class="plan-columns">
        <article class="panel">
          <div class="panel-heading">
            <div>
              <p class="overline">This week</p>
              <h2>本周目标</h2>
            </div>
            <span class="completion-badge">{{ goalRate }}%</span>
          </div>
          <div class="goal-list">
            <div v-for="goal in week?.goals ?? []" :key="goal.id">
              <button
                class="goal-check"
                :class="{ done: goal.status === '已完成' }"
                type="button"
                :aria-label="`切换${goal.title}`"
                @click="toggleGoal(goal)"
              >{{ goal.status === '已完成' ? '✓' : '' }}</button>
              <div class="goal-copy">
                <strong>{{ goal.title }}</strong>
                <small>预计 {{ Math.round(goal.target_minutes / 6) / 10 }} 小时 · {{ goal.status }}</small>
              </div>
              <button class="goal-remove" type="button" title="删除目标" @click="removeGoal(goal)">×</button>
            </div>
            <div v-if="!week?.goals.length" class="empty-state">本周还没有目标。</div>
          </div>

          <form v-if="showGoalForm" class="inline-form" @submit.prevent="addGoal">
            <input v-model="newGoal.title" maxlength="128" placeholder="例如：完成高数积分章节">
            <input v-model.number="newGoal.target_minutes" type="number" min="10" max="1200" step="10" aria-label="预计分钟">
            <button class="primary-button" type="submit" :disabled="savingGoal">{{ savingGoal ? '保存中…' : '添加' }}</button>
          </form>
          <button v-else class="add-task-row" type="button" @click="showGoalForm = true"><span>＋</span> 添加周目标</button>
        </article>

        <article class="panel schedule-card">
          <p class="overline">Schedule insight</p>
          <h2>{{ aiMessage ? 'AI 已更新今日计划' : '计划执行情况' }}</h2>
          <div class="big-insight" v-if="week?.delta_week !== null && week?.delta_week !== undefined">
            {{ week.delta_week > 0 ? '+' : '' }}{{ week.delta_week }}<span>%</span>
          </div>
          <div class="big-insight" v-else>{{ week?.avg_daily_tasks ?? 0 }}<span>个/学习日</span></div>
          <p>{{ aiMessage || plan.insight }}</p>
          <div class="plan-mini-stats">
            <span>本周任务 <b>{{ week?.completed_tasks }} / {{ week?.total_tasks }}</b></span>
            <span>学习时长 <b>{{ ((week?.minutes ?? 0) / 60).toFixed(1) }}h</b></span>
          </div>
          <button class="text-button" type="button" @click="load">刷新执行数据 <span>→</span></button>
        </article>
      </section>
    </template>
  </div>
</template>

