export type TaskStatus = '待开始' | '进行中' | '已完成'
export type Priority = '高' | '中' | '低'
export type GoalStatus = '待开始' | '进行中' | '已完成'

export interface User {
  id: number
  username: string
  display_name: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}

export interface Goal {
  exam_date: string
  target_school: string
  target_major: string
  target_score: number
  daily_minutes: number
  days_remaining: number
}

export interface Subject {
  id: number
  name: string
  code: string
}

export interface Knowledge {
  id: number
  name: string
  subject_id: number
  subject: string
  chapter: string
  mastery: number
  trend: 'up' | 'down' | 'steady'
  questions: number
  importance: number
  last_practiced_at: string | null
}

export interface Task {
  id: number
  title: string
  subject_id: number
  subject: string
  knowledge_point_id: number | null
  knowledge_point: string | null
  category: string
  scheduled_date: string
  start_time: string
  duration_minutes: number
  status: TaskStatus
  priority: Priority
  mastery: number | null
  note: string
}

export interface TaskPayload {
  title: string
  subject_id: number
  knowledge_point_id?: number | null
  scheduled_date?: string
  start_time?: string
  duration_minutes?: number
  priority?: Priority
  note?: string
}

export interface TaskUpdatePayload {
  title?: string
  subject_id?: number
  knowledge_point_id?: number | null
  status?: TaskStatus
  priority?: Priority
  note?: string
  start_time?: string
  duration_minutes?: number
  scheduled_date?: string
}

export interface TaskCompleteResult {
  task: Task
  record_id: number
  knowledge: Knowledge | null
  delta: number
  message: string
}

export interface WrongQuestion {
  id: number
  title: string
  subject: string
  knowledge_point: string | null
  source: string
  error_type: string
  analysis: string
  status: string
  review_count: number
  next_review_at: string | null
  due: boolean
  created_at: string
}

export interface WrongAnalysis {
  question_id: number
  analysis: string
  suggestions: string[]
  provider: string
}

export interface WeeklyPoint {
  date: string
  day: string
  minutes: number
}

export interface Dashboard {
  days_to_exam: number
  study_goal_minutes: number
  overdue_count: number
  ai_provider: string
  today_minutes: number
  today_completed: number
  today_total: number
  completion_rate: number
  average_mastery: number
  streak_days: number
  tasks: Task[]
  weak_points: Knowledge[]
  weekly: WeeklyPoint[]
}

export interface PlanPhase {
  index: number
  name: string
  start: string
  end: string
  status: 'done' | 'current' | 'upcoming'
}

export interface WeeklyGoal {
  id: number
  title: string
  target_minutes: number
  status: GoalStatus
  week_start: string
  progress: number
  progress_text: string
  auto: boolean
}

export interface PlanWeek {
  start: string
  end: string
  total_tasks: number
  completed_tasks: number
  completion_rate: number
  minutes: number
  avg_daily_tasks: number
  delta_week: number | null
  goals: WeeklyGoal[]
}

export interface Plan {
  exam_date: string | null
  days_remaining: number
  target_school: string
  target_major: string
  target_score: number
  daily_minutes: number
  ai_provider: string
  phases: PlanPhase[]
  week: PlanWeek
  insight: string
}

export interface PlanRecommendation {
  task_id: number
  title: string
  priority: string
  score: number
  reason: string
  start_time: string
  duration_minutes: number
}

export interface PlanResponse {
  message: string
  generated_at: string
  provider: string
  applied: boolean
  recommendations: PlanRecommendation[]
  deferred: PlanRecommendation[]
  warnings: string[]
}

export interface PracticeResult {
  knowledge: Knowledge
  delta: number
  message: string
}


export interface StudyRecordItem {
  id: number
  task_id: number | null
  task_title: string | null
  knowledge_point: string | null
  subject: string | null
  minutes: number
  correct_count: number
  total_count: number
  self_rating: number
  mastery_delta: number | null
  note: string
  created_at: string
}

export interface SummaryResponse {
  summary: string
  provider: string
  generated_at: string
}
