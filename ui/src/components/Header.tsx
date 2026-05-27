import { Link, NavLink } from 'react-router-dom'

/**
 * Compact header for the /demo and /chat pages. /landing has its own Navbar.
 */
export function Header() {
  return (
    <header className="z-10 flex h-14 flex-shrink-0 items-center gap-6 border-b border-slate-200 bg-white px-6 shadow-sm">
      <Link to="/" className="flex items-center gap-2">
        <div className="grid h-7 w-7 place-items-center rounded-md bg-brand-600 text-sm font-bold text-white">
          B
        </div>
        <span className="text-base font-semibold tracking-tight text-slate-900">BioInsight</span>
      </Link>

      <nav className="hidden items-center gap-1 md:flex">
        <NavTab to="/demo">Demo</NavTab>
        <NavTab to="/chat">Chat</NavTab>
      </nav>

      <span className="hidden text-xs text-slate-500 lg:inline">
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

function NavTab({ to, children }: { to: string; children: React.ReactNode }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        'rounded-md px-3 py-1.5 text-sm font-medium transition ' +
        (isActive
          ? 'bg-slate-100 text-slate-900'
          : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900')
      }
    >
      {children}
    </NavLink>
  )
}
