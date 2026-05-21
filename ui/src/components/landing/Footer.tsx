export function Footer() {
  const year = new Date().getFullYear()
  return (
    <footer className="border-t border-slate-200 bg-white py-12">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-6 px-6">
        <div className="flex items-center gap-2">
          <div className="grid h-7 w-7 place-items-center rounded-md bg-brand-600 text-xs font-bold text-white">
            B
          </div>
          <span className="text-sm font-semibold text-slate-900">BioVoyager</span>
          <span className="text-xs text-slate-400">— protein signals to research artifacts</span>
        </div>

        <nav className="flex flex-wrap items-center gap-6 text-sm text-slate-500">
          <a href="#how" className="hover:text-slate-900">How it works</a>
          <a href="#preview" className="hover:text-slate-900">Demo</a>
          <a href="#team" className="hover:text-slate-900">Team</a>
          <a
            href="https://github.com/JOY-SWang/BioVoyager"
            target="_blank"
            rel="noreferrer"
            className="hover:text-slate-900"
          >
            GitHub
          </a>
          <a href="mailto:hello@biovoyager.example.com" className="hover:text-slate-900">
            Contact
          </a>
        </nav>

        <p className="text-xs text-slate-400">© {year} BioVoyager team. MIT-licensed code.</p>
      </div>
    </footer>
  )
}
