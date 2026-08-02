/**
 * Reservation window helpers (FR-010).
 * `datetime-local` inputs produce local wall-clock strings; the API expects
 * ISO 8601 datetimes with timezone, so values are converted at the boundary.
 */

/** Format a Date for a `datetime-local` input value (local time, no TZ). */
export function toLocalInputValue(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    `T${pad(date.getHours())}:${pad(date.getMinutes())}`
  )
}

/** Convert a `datetime-local` value to an ISO 8601 string with timezone. */
export function toIsoDateTime(localValue: string): string {
  return new Date(localValue).toISOString()
}

/**
 * Validate a reservation window before submit (UX-only; the backend remains
 * the authority and also rejects overlapping active reservations with 409).
 * Returns a user-safe message, or null when the window is valid.
 */
export function validateReservationWindow(
  start: string,
  end: string,
  now: Date = new Date(),
): string | null {
  if (!start) return 'Choose when the reservation starts.'
  if (!end) return 'Choose when the reservation ends.'
  const startMs = new Date(start).getTime()
  const endMs = new Date(end).getTime()
  if (Number.isNaN(startMs) || Number.isNaN(endMs)) return 'Enter valid start and end times.'
  if (endMs <= startMs) return 'The end must be after the start.'
  if (endMs <= now.getTime()) return 'The reservation window must end in the future.'
  return null
}
