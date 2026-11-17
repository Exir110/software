import { reactive } from 'vue'

export type ToastKind = 'ok' | 'error'

export const toast = reactive({
  message: '',
  kind: 'ok' as ToastKind,
})

let timer: number | undefined

export function notify(message: string, kind: ToastKind = 'ok'): void {
  toast.message = message
  toast.kind = kind
  if (timer) window.clearTimeout(timer)
  timer = window.setTimeout(() => {
    toast.message = ''
  }, 3200)
}
