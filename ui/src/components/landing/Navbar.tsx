import { useEffect, useState } from 'react'
import { Link, NavLink } from 'react-router-dom'

/**
 * Global navbar — transparent over the hero, becomes solid w/ shadow on scroll.
 * Used by /landing only; the demo page uses its own compact header.
 */
export function Navbar() {
  const [scrolled, setScrolled] = useState(false)
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <header
      className={
        'fixed inset-x-0 top-0 z-50 transition ' +
        (scrolled
          ? 'border-b border-slate-200/80 bg-white/85 backdrop-blur-md shadow-sm'
          : 'border-b border-transparent bg-transparent')
      }
    >
      <nav className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
        <Link to="/" className="flex items-center gap-2">
          <div className="grid h-8 w-8 place-items-center rounded-lg bg-brand-600 font-bold text-white shadow-sm">
            B
          </div>
          <span className="text-base font-semibold tracking-tight text-slate-900">BioVoyager</span>
        </Link>

        <div className="hidden items-center gap-8 md:flex">
          <a href="#how" className="text-sm font-medium text-slate-600 transition hover:text-slate-900">
            How it works
          </a>
          <a href="#metrics" className="text-sm font-medium text-slate-600 transition hover:text-slate-900">
            Metrics
          </a>
          <a href="#preview" className="text-sm font-medium text-slate-600 transition hover:text-slate-900">
            Demo
          </a>
        </div>

        <div className="flex items-center gap-2">
          <NavLink
            to="/chat"
            className={({ isActive }) =>
              'hidden rounded-full px-3 py-1.5 text-sm font-medium transition sm:inline-flex ' +
              (isActive
                ? 'bg-slate-100 text-slate-900'
                : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900')
            }
          >
            Chat
          </NavLink>
          <Link
            to="/demo"
            className="inline-flex items-center gap-1.5 rounded-full bg-slate-900 px-4 py-1.5 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800"
          >
            Launch app
            <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" aria-hidden>
              <path d="M5 12h14M13 5l7 7-7 7" />
            </svg>
          </Link>
        </div>
      </nav>
    </header>
  )
}
