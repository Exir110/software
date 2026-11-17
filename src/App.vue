<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import type { Component } from 'vue'
import { request } from './api/client'
import type { Dashboard } from './api/types'
import { logout, restoreSession, session } from './stores/session'
import { notify, toast } from './stores/toast'
import { weekdayLabel } from './utils'
import GoalDialog from './components/GoalDialog.vue'
import KnowledgePage from './pages/KnowledgePage.vue'
import LoginPage from './pages/LoginPage.vue'
import OverviewPage from './pages/OverviewPage.vue'
import PlanPage from './pages/PlanPage.vue'
import TasksPage from './pages/TasksPage.vue'
import WrongPage from './pages/WrongPage.vue'

const navItems = [
  { id: 'overview', label: '学习总览', icon: '⌂' },
  { id: 'tasks', label: '今日任务', icon: '✓' },
  { id: 'knowledge', label: '知识追踪', icon: '◔' },
  { id: 'wrong', label: '错题本', icon: '▱' },
  { id: 'plan', label: '备考计划', icon: '◫' },
] as const

const pages: Record<string, Component> = {
  overview: OverviewPage,
  tasks: TasksPage,
  knowledge: KnowledgePage,
  wrong: WrongPage,
  plan: PlanPage,
}

const validPages = new Set<string>(navItems.map((item) => item.id))

function readHash(): string {
  const raw = window.location.hash.replace(/^#\/?/, '')
  return validPages.has(raw) ? raw : 'overview'
}

const activeNav = ref(readHash())
const showMobileNav = ref(false)
const showGoalDialog = ref(false)
const shell = reactive({
  daysToExam: 0,
  todayCompleted: 0,
  todayTotal: 0,
  streak: 0,
  average: 0,
})

const currentPage = computed<Component>(() => pages[activeNav.value] ?? OverviewPage)
const activePageTitle = computed(
  () => navItems.find((item) => item.id === activeNav.value)?.label ?? '学习总览',
)
const pendingCount = computed(() => Math.max(shell.todayTotal - shell.todayCompleted, 0))
const todayRate = computed(() =>
  shell.todayTotal ? Math.round((shell.todayCompleted / shell.todayTotal) * 100) : 0,
)
const formattedDate = computed(() => {
  const now = new Date()
  return `${now.getMonth() + 1}月${now.getDate()}日 · ${weekdayLabel(now)}`
})

const notifyTitle = computed(() => {
  if (!shell.todayTotal) return '今天还没有任务'
  return pendingCount.value ? `还有 ${pendingCount.value} 个任务待完成` : '今日任务已完成'
})
const notifyMessage = computed(() => {
  if (!shell.todayTotal) return '今天还没有任务，先添加一个学习任务吧'
  return pendingCount.value ? `今天还有 ${pendingCount.value} 个任务待完成` : '今天的任务已经全部完成'
})

async function refreshShell(): Promise<void> {
  if (!session.user) return
  try {
    const dashboard = await request<Dashboard>('/dashboard')
    shell.daysToExam = dashboard.days_to_exam
    shell.todayCompleted = dashboard.today_completed
    shell.todayTotal = dashboard.today_total
    shell.streak = dashboard.streak_days
    shell.average = dashboard.average_mastery
  } catch {
    // 页面自己会显示具体错误，这里静默失败即可
  }
}

function changePage(id: string): void {
  if (!validPages.has(id)) return
  activeNav.value = id
  showMobileNav.value = false
  if (window.location.hash !== `#/${id}`) window.location.hash = `#/${id}`
}

function onHashChange(): void {
  activeNav.value = readHash()
}

function handleUnauthorized(): void {
  logout()
  activeNav.value = 'overview'
}

function handleLogout(): void {
  logout()
  activeNav.value = 'overview'
  window.history.replaceState(null, '', window.location.pathname + window.location.search)
}

watch(activeNav, () => {
  void refreshShell()
})

watch(
  () => session.user,
  (user) => {
    if (user) void refreshShell()
  },
)

onMounted(async () => {
  window.addEventListener('hashchange', onHashChange)
  window.addEventListener('ytx-unauthorized', handleUnauthorized)
  await restoreSession()
})

onBeforeUnmount(() => {
  window.removeEventListener('hashchange', onHashChange)
  window.removeEventListener('ytx-unauthorized', handleUnauthorized)
})
</script>

<template>
  <div v-if="session.checking" class="boot-screen">正在恢复登录状态…</div>
  <LoginPage v-else-if="!session.user" />

  <div v-else class="app-shell">
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
          <span v-if="item.id === 'tasks' && pendingCount" class="nav-count">{{ pendingCount }}</span>
        </button>
      </nav>

      <div class="sidebar-spacer"></div>

      <div class="goal-mini-card">
        <span class="eyebrow">距离考试</span>
        <strong>{{ shell.daysToExam }}<small> 天</small></strong>
        <div class="mini-progress"><span :style="{ width: `${todayRate}%` }"></span></div>
        <span class="muted-text">今日完成 {{ shell.todayCompleted }}/{{ shell.todayTotal }} · 掌握度 {{ shell.average }}%</span>
      </div>

      <div class="profile-row">
        <button class="profile-button" type="button" @click="showGoalDialog = true">
          <span class="avatar">{{ session.user.display_name.slice(0, 1) }}</span>
          <span class="profile-copy"><strong>{{ session.user.display_name }}</strong><small>考研目标设置</small></span>
        </button>
        <button class="icon-button" type="button" title="退出登录" aria-label="退出登录" @click="handleLogout">⎋</button>
      </div>
    </aside>

    <main class="main-content">
      <header class="topbar">
        <button class="mobile-menu" type="button" aria-label="打开导航" @click="showMobileNav = !showMobileNav">☰</button>
        <div class="breadcrumb"><span>我的空间</span><b>/</b><strong>{{ activePageTitle }}</strong></div>
        <div class="topbar-actions">
          <span class="sync-badge" title="数据已保存到后端数据库">后端数据</span>
          <button
            class="icon-button notification-button"
            type="button"
            :title="notifyTitle"
            @click="notify(notifyMessage)"
          >♧<i v-if="pendingCount"></i></button>
          <button class="date-chip" type="button" @click="notify(`已连续学习 ${shell.streak} 天`)">◷ {{ formattedDate }}</button>
        </div>
      </header>

      <component :is="currentPage" @navigate="changePage" />
    </main>
  </div>

  <Transition name="toast">
    <div v-if="toast.message" class="toast-message" :class="{ 'toast-error': toast.kind === 'error' }">
      {{ toast.kind === 'error' ? '!' : '✓' }} {{ toast.message }}
    </div>
  </Transition>

  <GoalDialog
    v-if="showGoalDialog"
    @close="showGoalDialog = false"
    @saved="refreshShell"
  />
</template>

