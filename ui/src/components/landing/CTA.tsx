import { Link } from 'react-router-dom'

export function CTA() {
  return (
    <section className="bg-slate-950 py-24" id="cta">
      <div className="mx-auto max-w-4xl px-6 text-center">
        <h2 className="text-4xl font-semibold tracking-tight text-white sm:text-5xl">
          Ready to explore?
        </h2>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-slate-300">
          Browse the ten pre-generated disease reports, or read the paper to see
          how a flat protein table becomes a fully cited research artifact.
        </p>
        <div className="mt-10 flex flex-wrap justify-center gap-3">
          <Link
            to="/demo"
            className="inline-flex items-center gap-2 rounded-full bg-white px-6 py-3 text-sm font-semibold text-slate-900 shadow-md transition hover:bg-slate-100"
          >
            Open the demo
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
              <path d="M5 12h14M13 5l7 7-7 7" />
            </svg>
          </Link>
          <a
            href="mailto:hello@bioinsight.papersearch.org"
            className="inline-flex items-center gap-2 rounded-full border border-slate-700 px-6 py-3 text-sm font-semibold text-slate-200 transition hover:border-slate-500 hover:bg-white/5"
          >
            Contact the team
          </a>
        </div>
      </div>
    </section>
  )
}
