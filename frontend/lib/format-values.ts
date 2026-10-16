const inr = new Intl.NumberFormat('en-IN', {
  style: 'currency', currency: 'INR', minimumFractionDigits: 2, maximumFractionDigits: 2,
})
const counts = new Intl.NumberFormat('en-IN', {maximumFractionDigits: 0})
export const UNAVAILABLE = 'Unavailable'

function decimal(value: unknown): string | null {
  if (typeof value === 'number' && (!Number.isFinite(value) || Math.abs(value) > Number.MAX_SAFE_INTEGER)) return null
  if (!['string', 'number', 'bigint'].includes(typeof value)) return null
  const text = String(value).trim()
  return /^[+-]?\d+(?:\.\d+)?$/.test(text) ? text : null
}

export function formatINR(value: unknown): string {
  const text = decimal(value)
  if (text === null) return UNAVAILABLE
  // Modern Intl accepts exact decimal strings; avoid a lossy Number conversion.
  // TypeScript's Intl declaration still exposes only number/bigint inputs.
  return (inr.format as unknown as (value: string) => string)(text)
}

export function formatCount(value: unknown): string {
  const text = decimal(value)
  if (text === null || !/^\+?\d+(?:\.0+)?$/.test(text)) return UNAVAILABLE
  return counts.format(BigInt(text.split('.')[0]))
}
