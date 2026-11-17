export function todayISO(): string {
  const now = new Date()
  const offset = now.getTimezoneOffset()
  return new Date(now.getTime() - offset * 60_000).toISOString().slice(0, 10)
}

export function weekdayLabel(date = new Date()): string {
  return `星期${'日一二三四五六'[date.getDay()]}`
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const date = new Date(`${iso.slice(0, 10)}T00:00:00`)
  if (Number.isNaN(date.getTime())) return iso
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

export function fmtShortDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const date = new Date(`${iso.slice(0, 10)}T00:00:00`)
  if (Number.isNaN(date.getTime())) return iso
  return `${String(date.getMonth() + 1).padStart(2, '0')}.${String(date.getDate()).padStart(2, '0')}`
}

export function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return `${fmtDate(iso)} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

export function daysBetween(iso: string): number {
  const target = new Date(`${iso.slice(0, 10)}T00:00:00`)
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  return Math.max(Math.ceil((target.getTime() - today.getTime()) / 86_400_000), 0)
}
