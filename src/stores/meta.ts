import { reactive } from 'vue'
import { request } from '../api/client'
import type { Knowledge, Subject } from '../api/types'

export const meta = reactive({
  subjects: [] as Subject[],
  knowledge: [] as Knowledge[],
  loaded: false,
})

export async function loadMeta(force = false): Promise<void> {
  if (meta.loaded && !force) return
  const [subjects, knowledge] = await Promise.all([
    request<Subject[]>('/subjects'),
    request<Knowledge[]>('/knowledge'),
  ])
  meta.subjects = subjects
  meta.knowledge = knowledge
  meta.loaded = true
}

export async function reloadKnowledge(): Promise<void> {
  meta.knowledge = await request<Knowledge[]>('/knowledge')
}

export function pointsOf(subjectId: number | null): Knowledge[] {
  if (subjectId === null) return []
  return meta.knowledge.filter((point) => point.subject_id === subjectId)
}

export function subjectName(subjectId: number): string {
  return meta.subjects.find((subject) => subject.id === subjectId)?.name ?? '未分类'
}
