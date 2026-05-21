import { Link } from 'react-router-dom'

/**
 * Hero — the first thing visitors see.
 * Big claim, supporting line, two CTAs, decorative network graph SVG on the right.
 */
export function Hero() {
  return (
    <section className="relative overflow-hidden">
      {/* Background: subtle gradient + faint grid */}
      <div className="absolute inset-0 -z-10 bg-gradient-to-b from-white via-brand-50/40 to-white" />
      <div
        className="absolute inset-0 -z-10 opacity-[0.04]"
        style={{
          backgroundImage:
            "linear-gradient(to right, #0f172a 1px, transparent 1px), linear-gradient(to bottom, #0f172a 1px, transparent 1px)",
          backgroundSize: '48px 48px',
        }}
      />

      <div className="mx-auto grid max-w-7xl items-center gap-12 px-6 pt-24 pb-24 lg:grid-cols-12 lg:pt-32 lg:pb-32">
        <div className="lg:col-span-7">
          <p className="mb-5 inline-flex items-center gap-2 rounded-full border border-brand-200 bg-brand-50/60 px-3 py-1 text-xs font-medium text-brand-700">
            <span className="h-1.5 w-1.5 rounded-full bg-brand-500" />
            Multi-agent biomedical research
          </p>
          <h1 className="text-5xl font-semibold leading-[1.05] tracking-tight text-slate-900 sm:text-6xl lg:text-7xl">
            From protein signals to
            <br />
            <span className="bg-gradient-to-r from-brand-600 via-brand-500 to-cyan-500 bg-clip-text text-transparent">
              mechanism reports
            </span>
            .
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-relaxed text-slate-600">
            BioVoyager turns disease-associated proteomics into an interactive,
            evidence-grounded research dashboard — pathway enrichment, literature
            ranking, drug context, and a citable narrative, generated end-to-end
            by a team of LLM agents.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              to="/demo"
              className="inline-flex items-center gap-2 rounded-full bg-slate-900 px-6 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800 hover:shadow-md"
            >
              Try the demo
              <ArrowRight />
            </Link>
            <a
              href="https://github.com/JOY-SWang/BioVoyager"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 rounded-full border border-slate-300 bg-white px-6 py-3 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-50"
            >
              <GitHubIcon />
              View on GitHub
            </a>
          </div>

          <div className="mt-12 flex flex-wrap items-center gap-6 text-xs text-slate-500">
            <Bullet>10 disease reports pre-generated</Bullet>
            <Bullet>4 collaborating LLM agents</Bullet>
            <Bullet>PubMed · STRING-DB · DGIdb</Bullet>
          </div>
        </div>

        <div className="lg:col-span-5">
          <HeroVisual />
        </div>
      </div>
    </section>
  )
}

function Bullet({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <svg className="h-3.5 w-3.5 text-emerald-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden>
        <path d="M20 6L9 17l-5-5" />
      </svg>
      {children}
    </span>
  )
}

function ArrowRight() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path d="M5 12h14M13 5l7 7-7 7" />
    </svg>
  )
}

function GitHubIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.91.57.1.78-.25.78-.55 0-.27-.01-1.16-.02-2.1-3.2.7-3.87-1.36-3.87-1.36-.52-1.32-1.28-1.67-1.28-1.67-1.04-.71.08-.7.08-.7 1.16.08 1.77 1.19 1.77 1.19 1.02 1.76 2.69 1.25 3.34.96.1-.75.4-1.25.73-1.54-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.28 1.19-3.09-.12-.29-.52-1.47.11-3.07 0 0 .97-.31 3.18 1.18a11.05 11.05 0 0 1 5.79 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.6.23 2.78.12 3.07.74.81 1.18 1.83 1.18 3.09 0 4.42-2.69 5.39-5.25 5.68.41.36.78 1.06.78 2.13 0 1.54-.02 2.78-.02 3.16 0 .31.21.66.79.55A11.51 11.51 0 0 0 23.5 12C23.5 5.65 18.35.5 12 .5z" />
    </svg>
  )
}

function HeroVisual() {
  // Decorative SVG: nodes connected by arcs, evoking a pathway/PPI network.
  // Animated subtly so the hero doesn't feel static.
  return (
    <div className="relative aspect-square w-full">
      <div className="absolute inset-0 rounded-3xl bg-gradient-to-br from-brand-50 via-white to-cyan-50 shadow-[0_30px_80px_-30px_rgba(37,99,235,0.25)] ring-1 ring-slate-200/60" />
      <svg
        viewBox="0 0 400 400"
        className="absolute inset-0 h-full w-full p-8"
        aria-hidden
      >
        <defs>
          <radialGradient id="node-pathway" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#2563eb" stopOpacity="0.95" />
            <stop offset="100%" stopColor="#1d4ed8" stopOpacity="1" />
          </radialGradient>
          <radialGradient id="node-protein" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#94a3b8" stopOpacity="0.95" />
            <stop offset="100%" stopColor="#475569" stopOpacity="1" />
          </radialGradient>
          <radialGradient id="node-drug" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#34d399" stopOpacity="0.95" />
            <stop offset="100%" stopColor="#059669" stopOpacity="1" />
          </radialGradient>
        </defs>

        {/* Edges */}
        <g stroke="#cbd5e1" strokeWidth="1.2" fill="none">
          <line x1="200" y1="200" x2="100" y2="120" />
          <line x1="200" y1="200" x2="320" y2="100" />
          <line x1="200" y1="200" x2="340" y2="240" />
          <line x1="200" y1="200" x2="280" y2="330" />
          <line x1="200" y1="200" x2="120" y2="310" />
          <line x1="200" y1="200" x2="70" y2="220" />
          <line x1="100" y1="120" x2="70" y2="220" />
          <line x1="320" y1="100" x2="340" y2="240" />
          <line x1="280" y1="330" x2="340" y2="240" />
          <line x1="120" y1="310" x2="70" y2="220" />
        </g>

        {/* Pathway hex (center) */}
        <polygon
          points="200,160 240,180 240,220 200,240 160,220 160,180"
          fill="url(#node-pathway)"
          stroke="#1e3a8a"
          strokeWidth="1.5"
        />
        <text x="200" y="205" textAnchor="middle" fontSize="11" fill="white" fontWeight="600">
          Pathway
        </text>

        {/* Protein nodes */}
        {[
          [100, 120],
          [320, 100],
          [340, 240],
          [70, 220],
        ].map(([cx, cy], i) => (
          <g key={`p-${i}`} className="animate-[pulse_4s_ease-in-out_infinite]" style={{ animationDelay: `${i * 0.4}s` }}>
            <circle cx={cx} cy={cy} r="18" fill="url(#node-protein)" />
          </g>
        ))}

        {/* Drug rectangles */}
        {[
          [280, 330],
          [120, 310],
        ].map(([cx, cy], i) => (
          <rect
            key={`d-${i}`}
            x={cx - 22}
            y={cy - 12}
            width="44"
            height="24"
            rx="4"
            fill="url(#node-drug)"
            stroke="#065f46"
            strokeWidth="1.2"
          />
        ))}
      </svg>

      {/* Floating labels */}
      <div className="absolute right-6 top-6 rounded-lg border border-slate-200 bg-white/90 px-2.5 py-1.5 text-[11px] font-medium text-slate-600 shadow-sm backdrop-blur">
        <span className="mr-1.5 inline-block h-2 w-2 rounded-sm bg-emerald-500 align-middle" />
        Drug context
      </div>
      <div className="absolute bottom-6 left-6 rounded-lg border border-slate-200 bg-white/90 px-2.5 py-1.5 text-[11px] font-medium text-slate-600 shadow-sm backdrop-blur">
        <span className="mr-1.5 inline-block h-2 w-2 rounded-full bg-slate-500 align-middle" />
        Protein evidence
      </div>
    </div>
  )
}
