import type { IconName } from '~/utils/icons'

/** Semantic treatments per layout.md §5.3 — never color alone: icon + text + badge. */
export type Treatment = 'success' | 'info' | 'warning' | 'danger' | 'neutral'

export interface TreatmentStyle {
  treatment: Treatment
  icon: IconName
  badgeClass: string
}

const TREATMENT_CLASSES: Record<Treatment, string> = {
  success: 'bg-success/10 text-success border-success/40',
  info: 'bg-info/10 text-info border-info/40',
  warning: 'bg-warning/10 text-warning border-warning/40',
  danger: 'bg-danger/10 text-danger border-danger/40',
  neutral: 'bg-hover text-muted border-border-strong',
}

const TREATMENT_ICONS: Record<Treatment, IconName> = {
  success: 'success',
  info: 'info',
  warning: 'warning',
  danger: 'error',
  neutral: 'neutral',
}

const VALID_TREATMENTS = new Set<Treatment>(['success', 'info', 'warning', 'danger', 'neutral'])

/** Keyword → treatment mapping used when the backend supplies only a status code. */
const CODE_KEYWORDS: Array<[RegExp, Treatment]> = [
  [/^(available|in_stock|in_service|assigned|in_use|completed|verified|active|returned)/, 'success'],
  [/^(reserved|in_transit|pending|requested|checked_out|on_order)/, 'info'],
  [/^(maintenance|due|expiring|overdue|repair)/, 'warning'],
  [/^(missing|lost|stolen|failed|blocked|damaged)/, 'danger'],
  [/^(draft|retired|disposed|archived|inactive|cancelled)/, 'neutral'],
]

export function normalizeTreatment(value?: string | null): Treatment | null {
  if (!value) return null
  const v = value.toLowerCase().replace(/\s+/g, '_') as Treatment
  return VALID_TREATMENTS.has(v) ? v : null
}

function styleFor(treatment: Treatment): TreatmentStyle {
  return {
    treatment,
    icon: TREATMENT_ICONS[treatment],
    badgeClass: TREATMENT_CLASSES[treatment],
  }
}

export function treatmentForStatus(code?: string | null, semanticHint?: string | null): TreatmentStyle {
  const hinted = normalizeTreatment(semanticHint)
  let treatment: Treatment | null = hinted
  if (!treatment && code) {
    const normalized = code.toLowerCase().replace(/[\s-]+/g, '_')
    for (const [re, t] of CODE_KEYWORDS) {
      if (re.test(normalized)) {
        treatment = t
        break
      }
    }
  }
  return styleFor(treatment ?? 'neutral')
}

const OUTCOME_MAP: Record<string, Treatment> = {
  found: 'success',
  verified: 'success',
  moved: 'info',
  duplicate: 'warning',
  unexpected: 'warning',
  condition_mismatch: 'warning',
  not_found: 'danger',
  missing: 'danger',
}

/** Stocktake observation outcome → treatment (layout §15.2: distinguish scan results). */
export function outcomeStyle(outcome?: string | null): TreatmentStyle {
  const key = (outcome ?? '').toLowerCase().replace(/[\s-]+/g, '_')
  return styleFor(OUTCOME_MAP[key] ?? 'neutral')
}

/** Human-readable label for machine codes (found → Found, condition_mismatch → Condition mismatch). */
export function codeToLabel(code?: string | null): string {
  if (!code) return 'Unknown'
  return code
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}
