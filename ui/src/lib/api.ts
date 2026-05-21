import type { Disease } from '../types'

export async function fetchDiseases(signal?: AbortSignal): Promise<Disease[]> {
  const r = await fetch('/api/diseases', { signal })
  if (!r.ok) throw new Error(`GET /api/diseases failed: HTTP ${r.status}`)
  return r.json()
}

export function reportUrl(report: string): string {
  return `/raw?file=${encodeURIComponent(report)}`
}
