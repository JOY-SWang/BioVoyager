export function Header() {
  return (
    <header className="z-10 flex h-14 flex-shrink-0 items-center gap-4 border-b border-slate-200 bg-white px-6 shadow-sm">
      <Logo />
      <span className="text-xs text-slate-500">
        Plasma proteomics → pathway analysis → mechanism reports
      </span>
      <div className="ml-auto flex items-center gap-2">
        <a
          href="https://github.com/JOY-SWang/BioVoyager"
          target="_blank"
          rel="noreferrer"
          className="rounded-md border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:border-slate-300 hover:bg-slate-50"
        >
          GitHub ↗
        </a>
        <button
          disabled
          className="cursor-not-allowed rounded-md bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-400"
          title="Coming soon"
        >
          + Bring your own CSV
        </button>
      </div>
    </header>
  )
}

function Logo() {
  return (
    <div className="flex items-center gap-2">
      <div className="grid h-7 w-7 place-items-center rounded-md bg-brand-600 font-bold text-white">
        B
      </div>
      <span className="text-base font-semibold tracking-tight text-slate-900">BioVoyager</span>
    </div>
  )
}
