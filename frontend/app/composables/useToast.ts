import type { IconName } from '~/utils/icons'

export type ToastTone = 'success' | 'error' | 'info' | 'warning'

export interface ToastItem {
  id: number
  title: string
  description?: string
  tone: ToastTone
}

const TONE_ICONS: Record<ToastTone, IconName> = {
  success: 'success',
  error: 'error',
  info: 'info',
  warning: 'warning',
}

let nextId = 1

/** Lightweight toasts for non-critical confirmations (layout.md §20.1). */
export function useToast() {
  const toasts = useState<ToastItem[]>('app:toasts', () => [])

  function dismiss(id: number): void {
    toasts.value = toasts.value.filter((t) => t.id !== id)
  }

  function push(toast: Omit<ToastItem, 'id'>, timeoutMs = 5000): number {
    const id = nextId++
    toasts.value = [...toasts.value, { ...toast, id }]
    if (import.meta.client && timeoutMs > 0) {
      setTimeout(() => dismiss(id), timeoutMs)
    }
    return id
  }

  return {
    toasts,
    dismiss,
    push,
    success: (title: string, description?: string) => push({ title, description, tone: 'success' }),
    error: (title: string, description?: string) => push({ title, description, tone: 'error' }, 8000),
    info: (title: string, description?: string) => push({ title, description, tone: 'info' }),
    toneIcon: (tone: ToastTone) => TONE_ICONS[tone],
  }
}
