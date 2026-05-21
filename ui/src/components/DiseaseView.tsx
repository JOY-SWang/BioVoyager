import type { Disease } from '../types'
import { useProteinTable } from '../hooks/useProteinTable'
import { DiseaseHeaderCard } from './DiseaseHeaderCard'
import { ProteinTable } from './ProteinTable'
import { SearchInput } from './SearchInput'
import { Button } from './Button'

type Props = {
  disease: Disease
  onOpenReport: () => void
}

export function DiseaseView({ disease, onOpenReport }: Props) {
  const table = useProteinTable(disease.proteins)

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto p-6">
      <DiseaseHeaderCard disease={disease} />
      <ActionBar
        total={disease.n_proteins}
        visible={table.rows.length}
        hasReport={Boolean(disease.report)}
        search={table.search}
        onSearchChange={table.setSearch}
        onOpenReport={onOpenReport}
      />
      <ProteinTable
        rows={table.rows}
        sortKey={table.sortKey}
        sortDir={table.sortDir}
        onToggleSort={table.toggleSort}
      />
    </div>
  )
}

function ActionBar(props: {
  total: number
  visible: number
  hasReport: boolean
  search: string
  onSearchChange: (v: string) => void
  onOpenReport: () => void
}) {
  return (
    <div className="mb-3 flex flex-wrap items-center gap-3">
      <h2 className="text-sm font-semibold text-slate-700">Input Protein Table</h2>
      <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
        {props.visible} of {props.total} shown
      </span>
      <div className="ml-auto flex items-center gap-3">
        <SearchInput
          value={props.search}
          onChange={props.onSearchChange}
          placeholder="Search protein…"
        />
        {props.hasReport ? (
          <Button onClick={props.onOpenReport} className="px-4 py-1.5 font-semibold">
            View Full Report
            <ArrowRight />
          </Button>
        ) : (
          <span className="inline-flex items-center gap-1.5 rounded-md bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-800">
            No report yet
          </span>
        )}
      </div>
    </div>
  )
}

function ArrowRight() {
  return (
    <svg className="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden>
      <path d="M5 12h14M13 5l7 7-7 7" />
    </svg>
  )
}
