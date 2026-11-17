<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { request } from '../api/client'
import type { WrongAnalysis, WrongQuestion } from '../api/types'
import { loadMeta, meta } from '../stores/meta'
import { notify } from '../stores/toast'
import { fmtDate } from '../utils'
import WrongAnalysisDialog from '../components/WrongAnalysisDialog.vue'
import WrongQuestionDialog from '../components/WrongQuestionDialog.vue'

const questions = ref<WrongQuestion[]>([])
const loading = ref(true)
const loadError = ref('')
const statusFilter = ref('全部')
const subjectFilter = ref('全部')
const showDialog = ref(false)
const analyzing = ref<number | null>(null)
const activeAnalysis = ref<{ title: string; analysis: WrongAnalysis } | null>(null)

async function load(): Promise<void> {
  loading.value = true
  loadError.value = ''
  try {
    await loadMeta()
    questions.value = await request<WrongQuestion[]>('/wrong-questions')
  } catch (error) {
    loadError.value = (error as Error).message
  } finally {
    loading.value = false
  }
}

onMounted(load)

const subjects = computed(() => [...new Set(questions.value.map((item) => item.subject))])
const filtered = computed(() =>
  questions.value.filter((item) => {
    if (statusFilter.value !== '全部' && item.status !== statusFilter.value) return false
    if (subjectFilter.value !== '全部' && item.subject !== subjectFilter.value) return false
    return true
  }),
)

const topError = computed(() => {
  const counts = new Map<string, number>()
  for (const item of questions.value) {
    const key = item.error_type || '未标注错误类型'
    counts.set(key, (counts.get(key) ?? 0) + 1)
  }
  let best = ''
  let bestCount = 0
  for (const [key, count] of counts) {
    if (count > bestCount) {
      best = key
      bestCount = count
    }
  }
  const share = questions.value.length ? Math.round((bestCount / questions.value.length) * 100) : 0
  return { label: best, share, count: bestCount }
})

function indexColor(index: number): string {
  return ['red', 'orange', 'blue'][index % 3]
}

async function analyze(question: WrongQuestion): Promise<void> {
  analyzing.value = question.id
  try {
    const result = await request<WrongAnalysis>(`/wrong-questions/${question.id}/analyze`, { method: 'POST' })
    question.analysis = result.analysis
    activeAnalysis.value = { title: question.title, analysis: result }
    notify('AI 分析已完成')
  } catch (error) {
    notify((error as Error).message, 'error')
  } finally {
    analyzing.value = null
  }
}

async function toggleStatus(question: WrongQuestion): Promise<void> {
  const next = question.status === '已掌握' ? '待复习' : '已掌握'
  try {
    const updated = await request<WrongQuestion>(`/wrong-questions/${question.id}`, {
      method: 'PATCH',
      body: { status: next },
    })
    question.status = updated.status
    notify(next === '已掌握' ? '已标记为掌握' : '已放回待复习')
  } catch (error) {
    notify((error as Error).message, 'error')
  }
}

async function remove(question: WrongQuestion): Promise<void> {
  if (!window.confirm(`删除错题「${question.title}」？`)) return
  try {
    await request<void>(`/wrong-questions/${question.id}`, { method: 'DELETE' })
    questions.value = questions.value.filter((item) => item.id !== question.id)
    notify('错题已删除')
  } catch (error) {
    notify((error as Error).message, 'error')
  }
}
</script>

<template>
  <div class="page-content inner-page">
    <section class="page-title-row">
      <div>
        <p class="overline">Error review</p>
        <h1>错题本</h1>
        <p>错题不是负担，是下一次提分的入口。</p>
      </div>
      <button class="primary-button" type="button" @click="showDialog = true"><span>＋</span> 录入错题</button>
    </section>

    <div v-if="loading" class="loading-state">正在加载错题…</div>
    <div v-else-if="loadError" class="error-state">
      <p>{{ loadError }}</p>
      <button class="outline-button" type="button" @click="load">重试</button>
    </div>
    <template v-else>
      <section class="filter-bar">
        <div class="segmented">
          <button
            v-for="item in ['全部', '待复习', '已掌握']"
            :key="item"
            :class="{ active: statusFilter === item }"
            type="button"
            @click="statusFilter = item"
          >{{ item }}</button>
        </div>
        <select v-model="subjectFilter" aria-label="筛选科目">
          <option>全部</option>
          <option v-for="subject in subjects" :key="subject">{{ subject }}</option>
        </select>
        <span class="filter-summary">{{ filtered.length }} 道错题</span>
      </section>

      <section class="wrong-layout">
        <article class="panel full-panel">
          <div class="panel-heading">
            <div>
              <h2>错题列表</h2>
              <span class="panel-caption">按最近录入排序</span>
            </div>
          </div>
          <div v-for="(question, index) in filtered" :key="question.id" class="wrong-row">
            <span class="wrong-index" :class="indexColor(index)">{{ index + 1 }}</span>
            <div class="task-main">
              <div class="task-title-line">
                <strong>{{ question.title }}</strong>
                <span class="tag" :class="question.status === '已掌握' ? 'tag-green' : 'tag-yellow'">{{ question.status }}</span>
              </div>
              <span>
                {{ question.subject }}
                <template v-if="question.knowledge_point"> · {{ question.knowledge_point }}</template>
                <template v-if="question.error_type"> · {{ question.error_type }}</template>
                <template v-if="question.source"> · {{ question.source }}</template>
              </span>
              <p v-if="question.analysis" class="analysis-preview">{{ question.analysis }}</p>
            </div>
            <span class="wrong-date">{{ fmtDate(question.created_at) }}</span>
            <div class="row-actions">
              <button class="outline-button" type="button" :disabled="analyzing === question.id" @click="analyze(question)">
                {{ analyzing === question.id ? '分析中…' : 'AI 分析' }}
              </button>
              <button class="outline-button" type="button" @click="toggleStatus(question)">
                {{ question.status === '已掌握' ? '待复习' : '已掌握' }}
              </button>
              <button class="outline-button danger-button" type="button" @click="remove(question)">删除</button>
            </div>
          </div>
          <div v-if="!filtered.length" class="empty-state">当前筛选下没有错题。</div>
        </article>

        <article class="panel ai-mini-card">
          <div class="ai-badge">✦</div>
          <p class="overline">AI 错题分析</p>
          <h2 v-if="questions.length">你最近的错误有规律可循</h2>
          <h2 v-else>还没有足够的错题数据</h2>
          <p v-if="questions.length">
            近 {{ questions.length }} 道错题中，<strong>{{ topError.share }}%</strong>
            与“{{ topError.label }}”有关（{{ topError.count }} 道）。建议先处理同类错误，再扩展新题。
          </p>
          <p v-else>录入第一道错题后，这里会按错误类型自动汇总，并支持单题 AI 分析。</p>
          <button
            class="ai-action"
            type="button"
            :disabled="!questions.length"
            @click="analyze(filtered[0] ?? questions[0])"
          >分析最近一道错题 <span>→</span></button>
        </article>
      </section>
    </template>

    <WrongQuestionDialog v-if="showDialog" @close="showDialog = false" @saved="load" />
    <WrongAnalysisDialog
      v-if="activeAnalysis"
      :title="activeAnalysis.title"
      :analysis="activeAnalysis.analysis"
      @close="activeAnalysis = null"
    />
  </div>
</template>

