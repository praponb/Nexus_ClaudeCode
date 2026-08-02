/**
 * Parse a scanned/decoded value into an asset tag.
 * Accepts raw tags (e.g. AST-000123) and app deep links
 * (e.g. https://host/scan?tag=AST-000123 or /scan?tag=AST-000123).
 */
export function parseScannedTag(input: string): string | null {
  const raw = input.trim()
  if (!raw) return null

  // Deep-link forms containing a tag query parameter.
  const tagParamMatch = /[?&]tag=([^&#]+)/.exec(raw)
  if (tagParamMatch?.[1]) {
    const decoded = decodeURIComponent(tagParamMatch[1]).trim()
    return isPlausibleTag(decoded) ? decoded : null
  }

  // Absolute/relative URLs without a tag parameter are not asset codes.
  if (/^https?:\/\//i.test(raw) || raw.startsWith('/')) return null

  return isPlausibleTag(raw) ? raw : null
}

function isPlausibleTag(value: string): boolean {
  return /^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/.test(value)
}
