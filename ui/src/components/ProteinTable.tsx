import type { Protein, SortDir, SortKey } from '../types'
import { formatPValue } from '../lib/format'

type Column = { key: SortKey; label: string }

const COLUMNS: Column[] = [
  { key: 'protein', label: 'Protein' },
  { key: 'definition', label: 'Definition' },
  { key: 'nb_case', label: 'Cases' },
  { key: 'hr', label: 'HR [95% CI]' },
  { key: 'p_value', label: 'P-value' },
]

type Props = {
  rows: Protein[]
  sortKey: SortKey | null
  sortDir: SortDir
  onToggleSort: (key: SortKey) => void
}

export function ProteinTable({ rows, sortKey, sortDir, onToggleSort }: Props) {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="max-h-[calc(100vh-300px)] overflow-y-auto">
        <table className="w-full text-xs">
          <thead className="sticky top-0 z-10 bg-slate-50">
            <tr>
              {COLUMNS.map((col) => (
                <ColumnHeader
                  key={col.key}
                  column={col}
                  active={sortKey === col.key}
                  dir={sortDir}
                  onClick={() => onToggleSort(col.key)}
                />
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <EmptyRow />
            ) : (
              rows.map((r) => <ProteinRow key={r.protein} protein={r} />)
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function ColumnHeader({
  column,
  active,
  dir,
  onClick,
}: {
  column: Column
  active: boolean
  dir: SortDir
  onClick: () => void
}) {
  return (
    <th
      onClick={onClick}
      className="cursor-pointer select-none whitespace-nowrap border-b border-slate-200 px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500 transition hover:text-brand-600"
    >
      {column.label}
      <span className={'ml-1 ' + (active ? 'text-brand-600' : 'text-slate-300')}>
        {active ? (dir === 'asc' ? '↑' : '↓') : '↕'}
      </span>
    </th>
  )
}

function ProteinRow({ protein }: { protein: Protein }) {
  return (
    <tr className="border-b border-slate-100 transition last:border-0 hover:bg-brand-50/30">
      <td className="px-4 py-2.5 font-mono font-semibold text-brand-700">{protein.protein}</td>
      <td className="max-w-md px-4 py-2.5 text-slate-700">{protein.definition}</td>
      <td className="whitespace-nowrap px-4 py-2.5 tabular-nums text-slate-700">{protein.nb_case}</td>
      <td className="whitespace-nowrap px-4 py-2.5 tabular-nums text-slate-700">{protein.hr}</td>
      <td className="whitespace-nowrap px-4 py-2.5 tabular-nums text-slate-500">
        {formatPValue(protein.p_value)}
      </td>
    </tr>
  )
}

function EmptyRow() {
  return (
    <tr>
      <td colSpan={COLUMNS.length} className="px-4 py-8 text-center text-slate-400">
        No proteins match your search.
      </td>
    </tr>
  )
}
