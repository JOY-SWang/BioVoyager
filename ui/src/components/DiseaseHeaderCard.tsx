import type { Disease } from '../types'

export function DiseaseHeaderCard({ disease }: { disease: Disease }) {
  return (
    <div className="mb-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start gap-3">
        <h1 className="flex-1 text-xl font-semibold tracking-tight text-slate-900">
          {disease.name}
        </h1>
        <div className="flex flex-wrap items-center gap-1.5">
          <Pill tone="neutral">{disease.category}</Pill>
          <Pill tone="brand">{disease.n_proteins} input proteins</Pill>
          {!disease.report && <Pill tone="warning">Report pending</Pill>}
        </div>
      </div>
    </div>
  )
}

type Tone = 'neutral' | 'brand' | 'warning'
function Pill({ tone, children }: { tone: Tone; children: React.ReactNode }) {
  const styles: Record<Tone, string> = {
    neutral: 'bg-slate-100 text-slate-600',
    brand: 'bg-brand-50 text-brand-700',
    warning: 'bg-amber-50 text-amber-800',
  }
  return (
    <span className={`rounded-full px-2.5 py-1 text-[11px] font-medium ${styles[tone]}`}>
      {children}
    </span>
  )
}
