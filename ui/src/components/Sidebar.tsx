import { useMemo } from 'react'
import type { Disease } from '../types'

type Props = {
  diseases: Disease[]
  activeIdx: number | null
  onSelect: (idx: number) => void
}

export function Sidebar({ diseases, activeIdx, onSelect }: Props) {
  const grouped = useMemo(() => groupByCategory(diseases), [diseases])

  return (
    <aside className="w-72 flex-shrink-0 overflow-y-auto border-r border-slate-200 bg-brand-950 py-3">
      {Object.entries(grouped).map(([category, items]) => (
        <CategoryGroup
          key={category}
          category={category}
          items={items}
          activeIdx={activeIdx}
          onSelect={onSelect}
        />
      ))}
    </aside>
  )
}

type Indexed = Disease & { _idx: number }

function groupByCategory(diseases: Disease[]): Record<string, Indexed[]> {
  return diseases.reduce<Record<string, Indexed[]>>((acc, d, i) => {
    ;(acc[d.category] ||= []).push({ ...d, _idx: i })
    return acc
  }, {})
}

function CategoryGroup(props: {
  category: string
  items: Indexed[]
  activeIdx: number | null
  onSelect: (idx: number) => void
}) {
  return (
    <div className="mb-3">
      <div className="px-4 py-2 text-[10px] font-bold uppercase tracking-widest text-slate-400">
        {props.category}
      </div>
      {props.items.map((d) => (
        <DiseaseItem
          key={d.csv}
          disease={d}
          active={d._idx === props.activeIdx}
          onClick={() => props.onSelect(d._idx)}
        />
      ))}
    </div>
  )
}

function DiseaseItem(props: {
  disease: Indexed
  active: boolean
  onClick: () => void
}) {
  const { disease: d, active, onClick } = props
  const statusColor = active
    ? 'bg-brand-200'
    : d.report
      ? 'bg-slate-500'
      : 'bg-amber-500'

  return (
    <button
      onClick={onClick}
      className={
        'flex w-full items-center gap-2.5 border-l-2 px-4 py-2 text-left transition ' +
        (active
          ? 'border-brand-500 bg-brand-500/15 text-white'
          : 'border-transparent text-slate-300 hover:bg-white/5 hover:text-white')
      }
    >
      <span className={`h-1.5 w-1.5 flex-shrink-0 rounded-full ${statusColor}`} />
      <span className="flex-1 text-[13px] leading-tight">{d.name}</span>
      <span
        className={
          'text-[11px] tabular-nums ' + (active ? 'text-brand-200' : 'text-slate-500')
        }
      >
        {d.n_proteins}
      </span>
    </button>
  )
}
