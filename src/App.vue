<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

type TaskStatus = '待开始' | '进行中' | '已完成'
type Task = {
  id: number
  title: string
  subject: string
  category: string
  time: string
  duration: number
  status: TaskStatus
  priority: '高' | '中' | '低'
  mastery: number
  note?: string
}

type Knowledge = {
  id: number
  name: string
  subject: string
  chapter: string
  mastery: number
  trend: 'up' | 'down' | 'steady'
  questions: number
}

const navItems = [
  { id: 'overview', label: '学习总览', icon: '⌂' },
  { id: 'tasks', label: '今日任务', icon: '✓' },
  { id: 'knowledge', label: '知识追踪', icon: '◔' },
  { id: 'wrong', label: '错题本', icon: '▱' },
  { id: 'plan', label: '备考计划', icon: '◫' },
]

const activeNav = ref('overview')
const showMobileNav = ref(false)
const showAddTask = ref(false)
const showGoalEditor = ref(false)
const toast = ref('')
const currentDate = new Date()
const selectedSubject = ref('全部')
const taskFilter = ref<'全部' | TaskStatus>('全部')
const planGeneratedAt = ref('今天 08:40')
const aiBusy = ref(false)
const baseStudyMinutes = 46
const examDate = new Date('2026-12-19T00:00:00')
const newTaskTitle = ref('')
const newTaskSubject = ref('数学')
const newTaskDuration = ref(45)

const defaultTasks: Task[] = [
  { id: 1, title: '定积分的几何意义', subject: '数学', category: '高等数学 · 积分', time: '08:30', duration: 45, status: '已完成', priority: '高', mastery: 41, note: '完成例题 1-8，整理换元积分步骤' },
  { id: 2, title: '英语长难句精读', subject: '英语', category: '阅读理解 · 句法', time: '10:00', duration: 35, status: '已完成', priority: '中', mastery: 68, note: '精读真题 2019 Text 2' },
  { id: 3, title: '操作系统进程同步', subject: '408', category: '操作系统 · 进程管理', time: '14:00', duration: 50, status: '进行中', priority: '高', mastery: 52, note: '完成信号量与管程对比' },
  { id: 4, title: '线性代数错题回炉', subject: '数学', category: '线性代数 · 矩阵', time: '16:00', duration: 40, status: '待开始', priority: '高', mastery: 36, note: '回顾秩与线性方程组判定' },
  { id: 5, title: '政治选择题训练', subject: '政治', category: '马原 · 唯物辩证法', time: '19:30', duration: 30, status: '待开始', priority: '低', mastery: 77, note: '完成肖 1000 第 4 章' },
]

const defaultKnowledge: Knowledge[] = [
  { id: 1, name: '定积分', subject: '数学', chapter: '高等数学 · 积分', mastery: 41, trend: 'down', questions: 18 },
  { id: 2, name: '线性方程组', subject: '数学', chapter: '线性代数 · 矩阵', mastery: 52, trend: 'steady', questions: 24 },
  { id: 3, name: '长难句分析', subject: '英语', chapter: '阅读理解 · 句法', mastery: 68, trend: 'up', questions: 32 },
  { id: 4, name: '进程同步', subject: '408', chapter: '操作系统 · 进程管理', mastery: 56, trend: 'up', questions: 21 },
  { id: 5, name: '唯物辩证法', subject: '政治', chapter: '马原 · 哲学原理', mastery: 77, trend: 'up', questions: 46 },
  { id: 6, name: '矩阵秩', subject: '数学', chapter: '线性代数 · 矩阵', mastery: 36, trend: 'down', questions: 15 },
]

const tasks = ref<Task[]>(loadStorage('ytx-tasks', defaultTasks))
const knowledge = ref<Knowledge[]>(loadStorage('ytx-knowledge', defaultKnowledge))
const isGoalSet = ref(loadStorage('ytx-goal-set', true))
const aiMessage = ref('根据最近 7 天的练习表现，我建议今天优先完成「线性代数错题回炉」。它的掌握度只有 36%，且连续两次出现同类错误。')
const wrongQuestions = ref([
  { id: 1, title: '二重积分换元后的积分区域判断', subject: '数学', error: '区域边界识别错误', date: '昨天', color: 'red' },
  { id: 2, title: 'PV 操作系统中的信号量取值', subject: '408', error: '同步关系理解不完整', date: '9 月 29 日', color: 'orange' },
  { id: 3, title: '考研英语真题 Text 3 第 27 题', subject: '英语', error: '定位句与干扰项混淆', date: '9 月 28 日', color: 'blue' },
])

const subjects = computed(() => ['全部', ...new Set(tasks.value.map((task) => task.subject))])
const completedToday = computed(() => tasks.value.filter((task) => task.status === '已完成').length)
const studyMinutes = computed(() => baseStudyMinutes + tasks.value.filter((task) => task.status === '已完成').reduce((sum, task) => sum + task.duration, 0))
const pendingTaskCount = computed(() => tasks.value.filter((task) => task.status !== '已完成').length)
const goalDays = computed(() => {
  const today = new Date(currentDate.getFullYear(), currentDate.getMonth(), currentDate.getDate())
  const exam = new Date(examDate.getFullYear(), examDate.getMonth(), examDate.getDate())
  return Math.max(0, Math.ceil((exam.getTime() - today.getTime()) / 86400000))
})
const weekdayLabel = computed(() => `星期${'日一二三四五六'[currentDate.getDay()]}`)
const todayWeekIndex = computed(() => (currentDate.getDay() + 6) % 7)
const filteredTasks = computed(() => tasks.value.filter((task) => {
  const subjectMatch = selectedSubject.value === '全部' || task.subject === selectedSubject.value
  const filterMatch = taskFilter.value === '全部' || task.status === taskFilter.value
  return subjectMatch && filterMatch
}))
const completedTasks = computed(() => tasks.value.filter((task) => task.status === '已完成').length)
const completionRate = computed(() => Math.round((completedTasks.value / tasks.value.length) * 100))
const weakKnowledge = computed(() => [...knowledge.value].sort((a, b) => a.mastery - b.mastery).slice(0, 3))
const averageMastery = computed(() => Math.round(knowledge.value.reduce((sum, item) => sum + item.mastery, 0) / knowledge.value.length))
const activePageTitle = computed(() => navItems.find((item) => item.id === activeNav.value)?.label ?? '学习总览')
const formattedDate = computed(() => `${currentDate.getMonth() + 1}月${currentDate.getDate()}日 · 星期${'日一二三四五六'[currentDate.getDay()]}`)

watch(tasks, (value) => localStorage.setItem('ytx-tasks', JSON.stringify(value)), { deep: true })
watch(knowledge, (value) => localStorage.setItem('ytx-knowledge', JSON.stringify(value)), { deep: true })

onMounted(() => {
  window.setTimeout(() => {
    toast.value = ''
  }, 1500)
})

function loadStorage<T>(key: string, fallback: T): T {
  try {
    const value = localStorage.getItem(key)
    return value ? JSON.parse(value) as T : fallback
  } catch {
    return fallback
  }
}

function notify(message: string) {
  toast.value = message
  window.setTimeout(() => {
    toast.value = ''
  }, 2600)
}

function changePage(id: string) {
  activeNav.value = id
  showMobileNav.value = false
}

function toggleTask(task: Task) {
  if (task.status === '已完成') {
    task.status = '进行中'
    notify(`已将「${task.title}」恢复为进行中`)
    return
  }
  task.status = '已完成'
  const target = knowledge.value.find((item) => task.category.includes(item.chapter.split(' · ')[1]) || task.title.includes(item.name))
  if (target) target.mastery = Math.min(100, target.mastery + 4)
  notify(`完成任务：${task.title}`)
}

function startTask(task: Task) {
  task.status = task.status === '进行中' ? '待开始' : '进行中'
  notify(task.status === '进行中' ? `已开始「${task.title}」` : `已暂停「${task.title}」`)
}

function addTask() {
  if (!newTaskTitle.value.trim()) {
    notify('请先输入任务名称')
    return
  }
  tasks.value.push({
    id: Date.now(),
    title: newTaskTitle.value.trim(),
    subject: newTaskSubject.value,
    category: '自定义任务',
    time: '21:00',
    duration: newTaskDuration.value,
    status: '待开始',
    priority: '中',
    mastery: 50,
  })
  newTaskTitle.value = ''
  newTaskDuration.value = 45
  showAddTask.value = false
  notify('任务已加入今日计划')
}

function generatePlan() {
  aiBusy.value = true
  window.setTimeout(() => {
    const weak = weakKnowledge.value[0]
    tasks.value = tasks.value.map((task) => task.status === '待开始' ? { ...task, priority: task.title.includes(weak.name) ? '高' : task.priority } : task)
    planGeneratedAt.value = '刚刚更新'
    aiMessage.value = `计划已重新排序：优先处理「${weak.name}」，再完成「${weakKnowledge.value[1].name}」巩固。依据是掌握度、最近错题频率和距离考试的剩余时间。`
    aiBusy.value = false
    notify('AI 已完成今日计划优化')
  }, 900)
}

function updateGoal() {
  isGoalSet.value = true
  localStorage.setItem('ytx-goal-set', 'true')
  showGoalEditor.value = false
  notify('备考目标已保存')
}

function resetDemo() {
  tasks.value = defaultTasks.map((task) => ({ ...task }))
  knowledge.value = defaultKnowledge.map((item) => ({ ...item }))
  notify('演示数据已恢复')
}

function goToTasks() {
  activeNav.value = 'tasks'
  window.scrollTo({ top: 0, behavior: 'smooth' })
}
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar" :class="{ 'sidebar-open': showMobileNav }">
      <div class="brand">
        <div class="brand-mark">研</div>
        <div>
          <strong>研途智学</strong>
          <span>个人备考工作台</span>
        </div>
      </div>

      <nav class="primary-nav" aria-label="主导航">
        <button
          v-for="item in navItems"
          :key="item.id"
          class="nav-item"
          :class="{ active: activeNav === item.id }"
          type="button"
          @click="changePage(item.id)"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span>{{ item.label }}</span>
          <span v-if="item.id === 'tasks'" class="nav-count">{{ pendingTaskCount }}</span>
        </button>
      </nav>

      <div class="sidebar-spacer"></div>

      <div class="goal-mini-card">
        <span class="eyebrow">距离考试</span>
        <strong>{{ goalDays }}<small> 天</small></strong>
        <div class="mini-progress"><span style="width: 64%"></span></div>
        <span class="muted-text">已完成基础阶段 64%</span>
      </div>

      <button class="profile-button" type="button" @click="showGoalEditor = true">
        <span class="avatar">林</span>
        <span class="profile-copy"><strong>林同学</strong><small>考研目标设置</small></span>
        <span class="dots">···</span>
      </button>
    </aside>

    <main class="main-content">
      <header class="topbar">
        <button class="mobile-menu" type="button" aria-label="打开导航" @click="showMobileNav = !showMobileNav">☰</button>
        <div class="breadcrumb"><span>我的空间</span><b>/</b><strong>{{ activePageTitle }}</strong></div>
        <div class="topbar-actions">
          <button class="icon-button" type="button" title="搜索">⌕</button>
          <button class="icon-button notification-button" type="button" title="通知" @click="notify('你有 2 条学习提醒')">♧<i></i></button>
          <button class="date-chip" type="button" @click="notify('今天是你的第 38 个备考日')">◷ {{ formattedDate }}</button>
        </div>
      </header>

      <div v-if="activeNav === 'overview'" class="page-content">
        <section class="hero-row">
          <div>
            <p class="overline">{{ weekdayLabel }}，状态不错</p>
            <h1>把今天学明白，<em>上岸会更近。</em></h1>
            <p class="hero-subtitle">早上好，林同学。今天是你备考的第 38 天，保持这个节奏。</p>
          </div>
          <button class="primary-button" type="button" @click="goToTasks"><span>＋</span> 添加学习任务</button>
        </section>

        <section class="stats-grid">
          <article class="stat-card accent-card">
            <div class="stat-icon coral">◷</div>
            <div class="stat-label">今日学习时长</div>
            <strong>{{ Math.floor(studyMinutes / 60) }}<small>h</small> {{ studyMinutes % 60 }}<small>m</small></strong>
            <div class="stat-foot"><span class="positive">↑ 18%</span> 较昨日</div>
          </article>
          <article class="stat-card">
            <div class="stat-icon mint">✓</div>
            <div class="stat-label">今日任务完成</div>
            <strong>{{ completedToday }}<small> / {{ tasks.length }}</small></strong>
            <div class="stat-foot"><span class="positive">{{ completionRate }}%</span> 完成率</div>
          </article>
          <article class="stat-card">
            <div class="stat-icon lavender">◔</div>
            <div class="stat-label">整体掌握度</div>
            <strong>{{ averageMastery }}<small>%</small></strong>
            <div class="stat-foot"><span class="positive">↑ 4.2%</span> 本周提升</div>
          </article>
          <article class="stat-card">
            <div class="stat-icon yellow">⚑</div>
            <div class="stat-label">连续学习</div>
            <strong>12<small> 天</small></strong>
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
              <button class="text-button" type="button" @click="activeNav = 'tasks'">查看全部 <span>→</span></button>
            </div>
            <div class="task-list">
              <div v-for="task in tasks.slice(0, 4)" :key="task.id" class="task-row" :class="{ done: task.status === '已完成' }">
                <button class="task-check" :class="{ checked: task.status === '已完成' }" type="button" :aria-label="`完成${task.title}`" @click="toggleTask(task)">{{ task.status === '已完成' ? '✓' : '' }}</button>
                <div class="task-main">
                  <div class="task-title-line"><strong>{{ task.title }}</strong><span class="priority-dot" :class="task.priority === '高' ? 'high' : task.priority === '中' ? 'medium' : 'low'"></span></div>
                  <span>{{ task.category }} · {{ task.duration }} 分钟</span>
                </div>
                <div class="task-time">{{ task.time }}</div>
                <button v-if="task.status !== '已完成'" class="play-button" type="button" title="开始任务" @click="startTask(task)">{{ task.status === '进行中' ? 'Ⅱ' : '▶' }}</button>
                <span v-else class="done-label">已完成</span>
              </div>
            </div>
            <button class="add-task-row" type="button" @click="showAddTask = true"><span>＋</span> 添加一个任务</button>
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
            <div class="ai-message">{{ aiMessage }}</div>
            <div class="recommendation">
              <div class="recommendation-icon">↗</div>
              <div><span>推荐优先级</span><strong>{{ weakKnowledge[0].name }} · {{ weakKnowledge[0].mastery }}% 掌握</strong></div>
              <button type="button" title="查看推荐" @click="activeNav = 'knowledge'">→</button>
            </div>
            <button class="ai-action" type="button" :disabled="aiBusy" @click="generatePlan">{{ aiBusy ? '正在分析学习数据…' : '让 AI 重新安排今日计划' }} <span>✦</span></button>
            <span class="ai-footnote">基于最近 7 天学习记录生成 · {{ planGeneratedAt }}</span>
          </article>
        </section>

        <section class="lower-grid">
          <article class="panel mastery-panel">
            <div class="panel-heading">
              <div><p class="overline">Knowledge tracking</p><h2>知识掌握情况</h2></div>
              <button class="icon-button subtle" type="button" title="打开知识追踪" @click="activeNav = 'knowledge'">↗</button>
            </div>
            <div class="mastery-chart">
              <div class="chart-y"><span>100%</span><span>75%</span><span>50%</span><span>25%</span><span>0%</span></div>
              <div class="chart-body">
                <div class="grid-line" style="top: 0%"></div><div class="grid-line" style="top: 25%"></div><div class="grid-line" style="top: 50%"></div><div class="grid-line" style="top: 75%"></div><div class="grid-line" style="top: 100%"></div>
                <div class="bars">
                  <div v-for="item in knowledge.slice(0, 5)" :key="item.id" class="bar-group">
                    <div class="bar-value">{{ item.mastery }}%</div>
                    <div class="bar-track"><div class="bar-fill" :class="item.mastery < 50 ? 'weak' : item.mastery < 70 ? 'mid' : 'strong'" :style="{ height: `${item.mastery}%` }"></div></div>
                    <span>{{ item.name.length > 5 ? item.name.slice(0, 5) + '…' : item.name }}</span>
                  </div>
                </div>
              </div>
            </div>
            <div class="chart-legend"><span><i class="legend weak"></i>需要重点复习</span><span><i class="legend mid"></i>正在巩固</span><span><i class="legend strong"></i>掌握良好</span></div>
          </article>

          <article class="panel streak-panel">
            <div class="panel-heading"><div><p class="overline">Weekly rhythm</p><h2>本周学习节奏</h2></div><span class="week-label">9.28 - 10.4</span></div>
            <div class="week-chart">
              <div class="week-columns">
                <div v-for="(day, index) in ['一', '二', '三', '四', '五', '六', '日']" :key="day" class="day-column">
                  <div class="day-bar-track"><div class="day-bar" :class="{ today: index === todayWeekIndex }" :style="{ height: `${[68, 82, 58, 74, 42, 24, 0][index]}%` }"></div></div>
                  <span :class="{ todayText: index === todayWeekIndex }">{{ day }}</span>
                </div>
              </div>
              <div class="week-total"><strong>8.6h</strong><span>本周已学习</span><b>↑ 12%</b></div>
            </div>
          </article>
        </section>
      </div>

      <div v-else-if="activeNav === 'tasks'" class="page-content inner-page">
        <section class="page-title-row"><div><p class="overline">Study queue</p><h1>今日任务</h1><p>把任务拆小，把进度做实。</p></div><button class="primary-button" type="button" @click="showAddTask = true"><span>＋</span> 新建任务</button></section>
        <section class="filter-bar">
          <div class="segmented"><button v-for="filter in ['全部', '待开始', '进行中', '已完成'] as const" :key="filter" :class="{ active: taskFilter === filter }" type="button" @click="taskFilter = filter">{{ filter }}</button></div>
          <select v-model="selectedSubject" aria-label="筛选科目"><option v-for="subject in subjects" :key="subject">{{ subject }}</option></select>
          <span class="filter-summary">{{ filteredTasks.length }} 个任务 · 预计 {{ filteredTasks.reduce((sum, task) => sum + task.duration, 0) }} 分钟</span>
        </section>
        <section class="panel full-panel">
          <div v-for="task in filteredTasks" :key="task.id" class="task-detail-row" :class="{ done: task.status === '已完成' }">
            <button class="task-check large" :class="{ checked: task.status === '已完成' }" type="button" @click="toggleTask(task)">{{ task.status === '已完成' ? '✓' : '' }}</button>
            <div class="task-main"><div class="task-title-line"><strong>{{ task.title }}</strong><span class="tag" :class="task.priority === '高' ? 'tag-red' : task.priority === '中' ? 'tag-yellow' : 'tag-green'">{{ task.priority }}优先级</span></div><span>{{ task.category }} · 预计 {{ task.duration }} 分钟</span><p v-if="task.note">{{ task.note }}</p></div>
            <span class="detail-time">{{ task.time }}</span>
            <button class="outline-button" type="button" @click="startTask(task)">{{ task.status === '进行中' ? '暂停' : task.status === '已完成' ? '再做一次' : '开始' }}</button>
          </div>
          <div v-if="!filteredTasks.length" class="empty-state">没有符合当前筛选条件的任务。</div>
        </section>
      </div>

      <div v-else-if="activeNav === 'knowledge'" class="page-content inner-page">
        <section class="page-title-row"><div><p class="overline">Knowledge tracking</p><h1>知识追踪</h1><p>掌握度会随着你的练习和复习动态更新。</p></div><button class="outline-button" type="button" @click="notify('知识数据已刷新')">↻ 刷新数据</button></section>
        <section class="knowledge-summary"><div class="summary-main"><span>当前平均掌握度</span><strong>{{ averageMastery }}<small>%</small></strong><div class="progress-line"><span :style="{ width: `${averageMastery}%` }"></span></div><small>较上周提升 4.2%</small></div><div class="summary-item"><span>重点薄弱知识点</span><strong>{{ knowledge.filter((item) => item.mastery < 50).length }} 个</strong><small>建议优先复习</small></div><div class="summary-item"><span>已追踪知识点</span><strong>{{ knowledge.length }} 个</strong><small>覆盖 4 门科目</small></div></section>
        <section class="knowledge-grid"><article v-for="item in knowledge" :key="item.id" class="knowledge-card"><div class="knowledge-card-top"><span class="subject-mark" :class="item.subject === '数学' ? 'math' : item.subject === '英语' ? 'english' : item.subject === '政治' ? 'politics' : 'computer'">{{ item.subject }}</span><span class="trend" :class="item.trend">{{ item.trend === 'up' ? '↗' : item.trend === 'down' ? '↘' : '→' }}</span></div><h3>{{ item.name }}</h3><span class="knowledge-chapter">{{ item.chapter }}</span><div class="knowledge-score"><strong>{{ item.mastery }}%</strong><span>{{ item.questions }} 次练习</span></div><div class="progress-line"><span :class="item.mastery < 50 ? 'weak-line' : ''" :style="{ width: `${item.mastery}%` }"></span></div><button class="card-link" type="button" @click="notify(`已为「${item.name}」生成复习建议`)">查看复习建议 <span>→</span></button></article></section>
      </div>

      <div v-else-if="activeNav === 'wrong'" class="page-content inner-page">
        <section class="page-title-row"><div><p class="overline">Error review</p><h1>错题本</h1><p>错题不是负担，是下一次提分的入口。</p></div><button class="primary-button" type="button" @click="notify('已打开错题录入')"><span>＋</span> 录入错题</button></section>
        <section class="wrong-layout"><article class="panel full-panel"><div class="panel-heading"><div><h2>最近错题</h2><span class="panel-caption">按最近发生排序</span></div><button class="text-button" type="button" @click="notify('筛选功能即将接入')">筛选 <span>⌄</span></button></div><div v-for="question in wrongQuestions" :key="question.id" class="wrong-row"><span class="wrong-index" :class="question.color">{{ question.id }}</span><div class="task-main"><strong>{{ question.title }}</strong><span>{{ question.subject }} · {{ question.error }}</span></div><span class="wrong-date">{{ question.date }}</span><button class="icon-button subtle" type="button" title="分析错题" @click="notify(`AI 正在分析：${question.title}`)">✦</button></div></article><article class="panel ai-mini-card"><div class="ai-badge">✦</div><p class="overline">AI 错题分析</p><h2>你最近的错误有规律可循</h2><p>近 7 天的错题中，<strong>42%</strong> 与“审题不完整”有关。建议在每道题开始前先写出已知条件。</p><button class="ai-action" type="button" @click="notify('已生成错题归因报告')">生成归因报告 <span>→</span></button></article></section>
      </div>

      <div v-else class="page-content inner-page">
        <section class="page-title-row"><div><p class="overline">Exam roadmap</p><h1>备考计划</h1><p>从现在到上岸，每一个阶段都看得见。</p></div><button class="primary-button" type="button" @click="generatePlan"><span>✦</span> AI 优化计划</button></section>
        <section class="timeline panel"><div class="timeline-header"><div><span class="eyebrow">2026 考研</span><h2>数学一 · 英语一 · 政治 · 408</h2></div><span class="goal-date">考试日 2026.12.19</span></div><div class="timeline-track"><div class="phase done-phase"><span>01</span><strong>基础阶段</strong><small>7.01 - 8.31</small></div><div class="phase current-phase"><span>02</span><strong>强化阶段</strong><small>9.01 - 10.31</small><i>进行中</i></div><div class="phase"><span>03</span><strong>冲刺阶段</strong><small>11.01 - 11.30</small></div><div class="phase"><span>04</span><strong>模考阶段</strong><small>12.01 - 12.18</small></div></div></section><section class="plan-columns"><article class="panel"><div class="panel-heading"><div><p class="overline">This week</p><h2>本周目标</h2></div><span class="completion-badge">64%</span></div><div class="goal-list"><div><span class="goal-check done">✓</span><div><strong>完成高数积分章节</strong><small>预计 4 小时 · 已完成</small></div></div><div><span class="goal-check done">✓</span><div><strong>精读 3 篇英语真题</strong><small>预计 2 小时 · 已完成</small></div></div><div><span class="goal-check"> </span><div><strong>完成操作系统进程管理</strong><small>预计 3 小时 · 进行中</small></div></div><div><span class="goal-check"> </span><div><strong>整理本周错题</strong><small>预计 1 小时 · 待开始</small></div></div></div></article><article class="panel schedule-card"><p class="overline">Schedule insight</p><h2>计划执行得比上周稳定</h2><div class="big-insight">+18<span>%</span></div><p>最近 7 天平均每天完成 4.2 个任务。照这个节奏，你会在 11 月 24 日前完成第一轮重点知识复习。</p><button class="text-button" type="button" @click="notify('已打开详细执行分析')">查看执行分析 <span>→</span></button></article></section>
      </div>
    </main>

    <Transition name="toast"><div v-if="toast" class="toast-message">✓ {{ toast }}</div></Transition>

    <div v-if="showAddTask" class="modal-backdrop" @click.self="showAddTask = false">
      <div class="modal">
        <div class="modal-heading"><div><p class="overline">New task</p><h2>添加学习任务</h2></div><button class="icon-button" type="button" @click="showAddTask = false">×</button></div>
        <label>任务名称<input v-model="newTaskTitle" placeholder="例如：概率论条件概率"></label>
        <div class="form-row"><label>科目<select v-model="newTaskSubject"><option>数学</option><option>英语</option><option>政治</option><option>408</option></select></label><label>预计时长<input v-model.number="newTaskDuration" type="number" min="15" step="5"></label></div>
        <button class="primary-button full-button" type="button" @click="addTask">加入今日计划</button>
      </div>
    </div>

      <div v-if="showGoalEditor" class="modal-backdrop" @click.self="showGoalEditor = false">
      <div class="modal goal-modal"><div class="modal-heading"><div><p class="overline">Your goal</p><h2>备考目标</h2></div><button class="icon-button" type="button" @click="showGoalEditor = false">×</button></div><div class="goal-visual"><strong>{{ goalDays }}</strong><span>天后考试</span></div><p>当前目标：冲刺 985 院校计算机相关专业，目标总分 390 分。</p><button class="primary-button full-button" type="button" @click="updateGoal">保存目标</button><button class="text-button center-button" type="button" @click="resetDemo">恢复演示数据</button></div>
    </div>
  </div>
</template>
