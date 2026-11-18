<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { request } from '../api/client'
import type { Knowledge, PracticeResult, StudyRecordItem } from '../api/types'
import { meta, loadMeta } from '../stores/meta'
import { notify } from '../stores/toast'
import { fmtDate, fmtDateTime } from '../utils'
import KnowledgePointDialog from '../components/KnowledgePointDialog.vue'
import PracticeDialog from '../components/PracticeDialog.vue'

const knowledge = ref<Knowledge[]>([])
const records = ref<StudyRecordItem[]>([])
const showPointDialog = ref(false)
const recordDeleting = ref<number | null>(null)
const loading = ref(true)
const loadError = ref('')
const selectedSubject = ref(0)
const practicing = ref<Knowledge | null>(null)
const expanded = ref<number | null>(null)

async function load(): Promise<void> {
  loading.value = true
  loadError.value = ''
  try {
    await loadMeta()
    const [points, log] = await Promise.all([
      request<Knowledge[]>('/knowledge'),
      request<StudyRecordItem[]>('/records?limit=20'),
    ])
    knowledge.value = points
    records.value = log
  } catch (error) {
    loadError.value = (error as Error).message
  } finally {
    loading.value = false
  }
}

onMounted(load)

const filtered = computed(() =>
  selectedSubject.value
    ? knowledge.value.filter((item) => item.subject_id === selectedSubject.value)
    : knowledge.value,
)
const average = computed(() => {
  if (!knowledge.value.length) return 0
  return Math.round(knowledge.value.reduce((sum, item) => sum + item.mastery, 0) / knowledge.value.length)
})
const weakCount = computed(() => knowledge.value.filter((item) => item.mastery < 50).length)
const subjectCount = computed(() => new Set(knowledge.value.map((item) => item.subject)).size)

function subjectClass(subject: string): string {
  if (subject === '数学') return 'math'
  if (subject === '英语') return 'english'
  if (subject === '政治') return 'politics'
  return 'computer'
}

function advice(item: Knowledge): string {
  if (item.mastery < 50) return '掌握度低于 50%，建议先回到定义与基础例题，再做 5-10 道同类题并记录正确率。'
  if (item.mastery < 70) return '基础已经具备，建议用变式题巩固，并把最近错题按错误类型归类。'
  return '掌握良好，建议保持间隔复习，每周安排一次综合题或整卷训练。'
}

async function refresh(): Promise<void> {
  await load()
  notify('知识数据已刷新')
}

async function loadRecords(): Promise<void> {
  records.value = await request<StudyRecordItem[]>('/records?limit=20')
}

function onSaved(result: PracticeResult): void {
  const index = knowledge.value.findIndex((item) => item.id === result.knowledge.id)
  if (index >= 0) knowledge.value[index] = result.knowledge
  knowledge.value = [...knowledge.value].sort((a, b) => a.mastery - b.mastery)
  void loadRecords()
}

async function removeRecord(record: StudyRecordItem): Promise<void> {
  if (!window.confirm('删除这条学习记录？对应的掌握度变化会回滚，关联任务会恢复为待开始。')) return
  recordDeleting.value = record.id
  try {
    await request<void>(`/records/${record.id}`, { method: 'DELETE' })
    notify('学习记录已删除，掌握度已回滚')
    await load()
  } catch (error) {
    notify((error as Error).message, 'error')
  } finally {
    recordDeleting.value = null
  }
}
</script>

<template>
  <div class="page-content inner-page">
    <section class="page-title-row">
      <div>
        <p class="overline">Knowledge tracking</p>
        <h1>知识追踪</h1>
        <p>掌握度会随着你的练习和复习动态更新。</p>
      </div>
      <div class="title-actions">
        <button class="outline-button" type="button" @click="showPointDialog = true">＋ 添加知识点</button>
        <button class="outline-button" type="button" @click="refresh">↻ 刷新数据</button>
      </div>
    </section>

    <div v-if="loading" class="loading-state">正在加载知识点…</div>
    <div v-else-if="loadError" class="error-state">
      <p>{{ loadError }}</p>
      <button class="outline-button" type="button" @click="load">重试</button>
    </div>
    <template v-else>
      <section class="knowledge-summary">
        <div class="summary-main">
          <span>当前平均掌握度</span>
          <strong>{{ average }}<small>%</small></strong>
          <div class="progress-line"><span :style="{ width: `${average}%` }"></span></div>
          <small>按练习正确率与自评动态更新</small>
        </div>
        <div class="summary-item">
          <span>重点薄弱知识点</span>
          <strong>{{ weakCount }} 个</strong>
          <small>掌握度低于 50%</small>
        </div>
        <div class="summary-item">
          <span>已追踪知识点</span>
          <strong>{{ knowledge.length }} 个</strong>
          <small>覆盖 {{ subjectCount }} 门科目</small>
        </div>
      </section>

      <section class="filter-bar">
        <select v-model.number="selectedSubject" aria-label="筛选科目">
          <option :value="0">全部科目</option>
          <option v-for="subject in meta.subjects" :key="subject.id" :value="subject.id">{{ subject.name }}</option>
        </select>
        <span class="filter-summary">{{ filtered.length }} 个知识点 · 按掌握度从低到高排序</span>
      </section>

      <section class="knowledge-grid">
        <article v-for="item in filtered" :key="item.id" class="knowledge-card">
          <div class="knowledge-card-top">
            <span class="subject-mark" :class="subjectClass(item.subject)">{{ item.subject }}</span>
            <span class="trend" :class="item.trend">{{ item.trend === 'up' ? '↗' : item.trend === 'down' ? '↘' : '→' }}</span>
          </div>
          <h3>{{ item.name }}</h3>
          <span class="knowledge-chapter">{{ item.chapter }}</span>
          <div class="knowledge-score">
            <strong>{{ item.mastery }}%</strong>
            <span>{{ item.questions }} 次练习</span>
          </div>
          <div class="progress-line"><span :class="item.mastery < 50 ? 'weak-line' : ''" :style="{ width: `${item.mastery}%` }"></span></div>
          <div v-if="expanded === item.id" class="knowledge-detail">
            <p>{{ advice(item) }}</p>
            <p class="muted-line">重要度 {{ item.importance }}/5 · 最近练习 {{ fmtDate(item.last_practiced_at) }}</p>
          </div>
          <div class="knowledge-actions">
            <button class="card-link" type="button" @click="expanded = expanded === item.id ? null : item.id">
              {{ expanded === item.id ? '收起建议' : '查看复习建议' }} <span>→</span>
            </button>
            <button class="outline-button" type="button" @click="practicing = item">记录练习</button>
          </div>
        </article>
      </section>
      <div v-if="!filtered.length" class="empty-state">该科目下还没有知识点。</div>

      <section class="panel records-panel">
        <div class="panel-heading">
          <div><p class="overline">Study log</p><h2>最近学习记录</h2></div>
          <span class="panel-caption">删除记录会回滚对应掌握度</span>
        </div>
        <div v-for="record in records" :key="record.id" class="record-row">
          <div class="record-main">
            <strong>{{ record.task_title || record.knowledge_point || '学习记录' }}</strong>
            <span>
              {{ fmtDateTime(record.created_at) }} · {{ record.minutes }} 分钟
              <template v-if="record.total_count"> · {{ record.correct_count }}/{{ record.total_count }}</template>
              · 自评 {{ record.self_rating }}/5
            </span>
            <p v-if="record.note">{{ record.note }}</p>
          </div>
          <span class="record-delta" :class="{ down: (record.mastery_delta ?? 0) < 0 }">
            {{ record.mastery_delta === null ? '—' : `${record.mastery_delta > 0 ? '+' : ''}${record.mastery_delta.toFixed(1)}%` }}
          </span>
          <button
            class="outline-button danger-button"
            type="button"
            :disabled="recordDeleting === record.id"
            @click="removeRecord(record)"
          >删除</button>
        </div>
        <div v-if="!records.length" class="empty-state">还没有学习记录。</div>
      </section>
    </template>

    <PracticeDialog
      v-if="practicing"
      :point="practicing"
      @close="practicing = null"
      @saved="onSaved"
    />
    <KnowledgePointDialog
      v-if="showPointDialog"
      @close="showPointDialog = false"
      @saved="load"
    />
  </div>
</template>

