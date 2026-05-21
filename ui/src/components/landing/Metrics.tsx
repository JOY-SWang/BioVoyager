type Stat = { value: string; label: string; sublabel?: string }

const STATS: Stat[] = [
  { value: '10', label: 'Disease reports', sublabel: 'pre-generated' },
  { value: '29', label: 'Avg. enriched pathways', sublabel: 'per disease' },
  { value: '4', label: 'LLM agents', sublabel: 'Planning · Reasoning · Query · Writing' },
  { value: '3', label: 'Knowledge sources', sublabel: 'PubMed · STRING · DGIdb' },
]

/**
 * Metrics — quick numeric proof points across the bottom of the "how it works" section.
 */
export function Metrics() {
  return (
    <section className="bg-slate-900 py-20" id="metrics">
      <div className="mx-auto max-w-7xl px-6">
        <div className="grid grid-cols-2 gap-x-8 gap-y-12 lg:grid-cols-4">
          {STATS.map((s) => (
            <StatCard key={s.label} stat={s} />
          ))}
        </div>
      </div>
    </section>
  )
}

function StatCard({ stat }: { stat: Stat }) {
  return (
    <div className="text-center">
      <p className="bg-gradient-to-b from-white to-slate-300 bg-clip-text text-5xl font-bold text-transparent sm:text-6xl">
        {stat.value}
      </p>
      <p className="mt-3 text-sm font-medium text-slate-200">{stat.label}</p>
      {stat.sublabel && (
        <p className="mt-1 text-xs text-slate-500">{stat.sublabel}</p>
      )}
    </div>
  )
}
