type Step = {
  num: string
  title: string
  body: string
  tag: string
}

const STEPS: Step[] = [
  {
    num: '01',
    tag: 'Input',
    title: 'A disease + a protein table',
    body: 'You supply a cohort-derived list of disease-associated proteins (hazard ratios, p-values). No model retraining required.',
  },
  {
    num: '02',
    tag: 'Planning',
    title: 'Pathway enrichment & ranking',
    body: 'The Planning Agent runs g:Profiler, filters fundamentals, and ranks pathways by literature relevance using PubMed, Semantic Scholar, and BioBERT embeddings.',
  },
  {
    num: '03',
    tag: 'Reasoning',
    title: 'Mechanism synthesis',
    body: 'The Reasoning Agent retrieves STRING-DB protein interactions, clusters them, and writes per-pathway mechanism descriptions with PubMed citations.',
  },
  {
    num: '04',
    tag: 'Output',
    title: 'An interactive Cytoscape dashboard',
    body: 'A single self-contained HTML report: pathway-protein-drug network on the left, narrative report on the right, every claim hyperlinked to its source.',
  },
]

/**
 * HowItWorks — 4-step pipeline overview. Stepper layout with a left rail.
 */
export function HowItWorks() {
  return (
    <section className="border-y border-slate-200/60 bg-slate-50/60 py-24" id="how">
      <div className="mx-auto max-w-7xl px-6">
        <SectionHeader
          eyebrow="Pipeline"
          title="From CSV to dashboard, in one pass"
          description="Four collaborating LLM agents — each with a focused role — turn a flat protein table into a fully cited research artifact."
        />
        <div className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((s) => (
            <StepCard key={s.num} step={s} />
          ))}
        </div>
      </div>
    </section>
  )
}

function StepCard({ step }: { step: Step }) {
  return (
    <div className="group relative rounded-2xl border border-slate-200 bg-white p-6 transition hover:-translate-y-0.5 hover:border-brand-300 hover:shadow-lg">
      <div className="flex items-baseline justify-between">
        <span className="font-mono text-3xl font-bold text-slate-200 transition group-hover:text-brand-200">
          {step.num}
        </span>
        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
          {step.tag}
        </span>
      </div>
      <h3 className="mt-4 text-base font-semibold text-slate-900">{step.title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-slate-600">{step.body}</p>
    </div>
  )
}

export function SectionHeader(props: {
  eyebrow?: string
  title: string
  description?: string
  center?: boolean
}) {
  const align = props.center === false ? '' : 'text-center mx-auto'
  return (
    <div className={`max-w-2xl ${align}`}>
      {props.eyebrow && (
        <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-brand-600">
          {props.eyebrow}
        </p>
      )}
      <h2 className="text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
        {props.title}
      </h2>
      {props.description && (
        <p className="mt-4 text-base leading-relaxed text-slate-600">{props.description}</p>
      )}
    </div>
  )
}
