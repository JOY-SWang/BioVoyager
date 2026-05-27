import { Link } from 'react-router-dom'
import { SectionHeader } from './HowItWorks'

/**
 * InterfacePreview — show what the demo actually looks like, with a
 * "macOS-window"-styled frame around a screenshot or live iframe.
 */
export function InterfacePreview() {
  return (
    <section className="py-24" id="preview">
      <div className="mx-auto max-w-7xl px-6">
        <SectionHeader
          eyebrow="The Demo"
          title="Browse ten ready-made disease reports"
          description="Pre-computed dashboards for Alzheimer's, Parkinson's, Type 2 Diabetes, and seven more — each with a Cytoscape network and a fully cited mechanism report."
        />

        <div className="relative mx-auto mt-14 max-w-5xl">
          {/* Decorative gradient halo */}
          <div className="absolute -inset-4 -z-10 rounded-3xl bg-gradient-to-r from-brand-200/40 via-cyan-200/40 to-emerald-200/40 blur-2xl" />

          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xl">
            <WindowChrome />
            <MockUI />
          </div>

          <div className="mt-8 flex justify-center">
            <Link
              to="/demo"
              className="inline-flex items-center gap-2 rounded-full bg-brand-600 px-6 py-3 text-sm font-semibold text-white shadow-md transition hover:bg-brand-700 hover:shadow-lg"
            >
              Open the live demo
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                <path d="M5 12h14M13 5l7 7-7 7" />
              </svg>
            </Link>
          </div>
        </div>
      </div>
    </section>
  )
}

function WindowChrome() {
  return (
    <div className="flex items-center gap-1.5 border-b border-slate-200 bg-slate-50 px-4 py-2.5">
      <span className="h-3 w-3 rounded-full bg-rose-400" />
      <span className="h-3 w-3 rounded-full bg-amber-400" />
      <span className="h-3 w-3 rounded-full bg-emerald-400" />
      <span className="ml-3 text-[11px] text-slate-400">bioinsight.papersearch.org/demo</span>
    </div>
  )
}

function MockUI() {
  return (
    <div className="flex h-[460px] bg-white">
      {/* sidebar */}
      <div className="w-56 flex-shrink-0 bg-slate-900 p-3 text-[11px]">
        <div className="px-2 py-1.5 text-[9px] font-bold uppercase tracking-widest text-slate-500">
          Nervous System
        </div>
        <div className="mt-1 flex items-center gap-2 rounded-md border-l-2 border-brand-500 bg-brand-500/15 px-3 py-1.5 text-white">
          <span className="h-1.5 w-1.5 rounded-full bg-brand-300" />
          Alzheimer Disease
          <span className="ml-auto text-[10px] text-brand-200">10</span>
        </div>
        <div className="mt-1 flex items-center gap-2 px-3 py-1.5 text-slate-400">
          <span className="h-1.5 w-1.5 rounded-full bg-slate-600" />
          Parkinson's Disease
          <span className="ml-auto text-[10px] text-slate-600">11</span>
        </div>
        <div className="mt-4 px-2 py-1.5 text-[9px] font-bold uppercase tracking-widest text-slate-500">
          Circulatory
        </div>
        {['Heart Failure', 'Hypertension', 'Stroke'].map((d, i) => (
          <div key={i} className="mt-1 flex items-center gap-2 px-3 py-1.5 text-slate-400">
            <span className="h-1.5 w-1.5 rounded-full bg-slate-600" />
            {d}
          </div>
        ))}
      </div>

      {/* main */}
      <div className="flex-1 overflow-hidden bg-slate-50 p-5">
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <div className="flex items-center gap-2">
            <h3 className="text-base font-semibold text-slate-900">Alzheimer Disease</h3>
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600">
              Nervous System
            </span>
            <span className="rounded-full bg-brand-50 px-2 py-0.5 text-[10px] font-medium text-brand-700">
              10 proteins
            </span>
          </div>
        </div>
        <div className="mt-3 flex items-center gap-2 text-[11px]">
          <span className="font-semibold text-slate-700">Input Protein Table</span>
          <span className="rounded bg-slate-100 px-1.5 py-0.5 text-slate-600">10 shown</span>
          <button className="ml-auto rounded-md bg-brand-600 px-3 py-1 text-[10px] font-semibold text-white">
            View Full Report →
          </button>
        </div>
        <div className="mt-2 overflow-hidden rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-[10px]">
            <thead>
              <tr className="bg-slate-50 text-left text-[9px] uppercase tracking-wider text-slate-500">
                <th className="px-3 py-2">Protein</th>
                <th className="px-3 py-2">Definition</th>
                <th className="px-3 py-2">HR</th>
                <th className="px-3 py-2">P</th>
              </tr>
            </thead>
            <tbody>
              {[
                ['APOE', 'Apolipoprotein E', '1.93', '4.2e-12'],
                ['GFAP', 'Glial fibrillary acidic protein', '1.41', '8.7e-09'],
                ['NEFL', 'Neurofilament light chain', '1.55', '2.1e-08'],
                ['VGF', 'VGF nerve growth factor', '0.74', '5.6e-07'],
                ['SNAP25', 'Synaptosomal-associated protein 25', '1.28', '1.9e-06'],
              ].map(([p, d, hr, pv], i) => (
                <tr key={i} className="border-t border-slate-100">
                  <td className="px-3 py-1.5 font-mono font-semibold text-brand-700">{p}</td>
                  <td className="px-3 py-1.5 text-slate-700">{d}</td>
                  <td className="px-3 py-1.5 tabular-nums text-slate-700">{hr}</td>
                  <td className="px-3 py-1.5 tabular-nums text-slate-500">{pv}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
