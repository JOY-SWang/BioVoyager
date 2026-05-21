import { useState } from 'react'
import { useDiseases } from './hooks/useDiseases'
import { Header } from './components/Header'
import { Sidebar } from './components/Sidebar'
import { DiseaseView } from './components/DiseaseView'
import { ReportView } from './components/ReportView'
import { LoadingState } from './components/LoadingState'
import { ErrorState } from './components/ErrorState'
import { EmptyMainPanel } from './components/EmptyMainPanel'

export default function App() {
  const state = useDiseases()
  const [activeIdx, setActiveIdx] = useState(0)
  const [showReport, setShowReport] = useState(false)

  if (state.status === 'loading') return <LoadingState label="Loading diseases…" />
  if (state.status === 'error') return <ErrorState error={state.error} />

  const { diseases } = state
  const active = diseases[activeIdx] ?? null

  return (
    <div className="flex h-full flex-col">
      <Header />
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
    </div>
  )
}
