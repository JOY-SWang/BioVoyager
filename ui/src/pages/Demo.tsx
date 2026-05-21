import { useState } from 'react'
import { useDiseases } from '../hooks/useDiseases'
import { Sidebar } from '../components/Sidebar'
import { DiseaseView } from '../components/DiseaseView'
import { ReportView } from '../components/ReportView'
import { LoadingState } from '../components/LoadingState'
import { ErrorState } from '../components/ErrorState'
import { EmptyMainPanel } from '../components/EmptyMainPanel'

/**
 * /demo — the interactive disease browser.
 * Left: category-grouped sidebar of pre-generated reports.
 * Middle: the selected disease's input protein table.
 * Right (via toggle): the full Cytoscape report iframe.
 */
export default function Demo() {
  const state = useDiseases()
  const [activeIdx, setActiveIdx] = useState(0)
  const [showReport, setShowReport] = useState(false)

  if (state.status === 'loading') return <LoadingState label="Loading diseases…" />
  if (state.status === 'error') return <ErrorState error={state.error} />

  const { diseases } = state
  const active = diseases[activeIdx] ?? null

  return (
    <div className="flex min-h-0 flex-1">
      <Sidebar
        diseases={diseases}
        activeIdx={activeIdx}
        onSelect={(i) => {
          setActiveIdx(i)
          setShowReport(false)
        }}
      />
      <main className="flex min-h-0 flex-1 flex-col overflow-hidden bg-slate-50">
        {!active ? (
          <EmptyMainPanel />
        ) : showReport && active.report ? (
          <ReportView
            report={active.report}
            diseaseName={active.name}
            onBack={() => setShowReport(false)}
          />
        ) : (
          <DiseaseView disease={active} onOpenReport={() => setShowReport(true)} />
        )}
      </main>
    </div>
  )
}
