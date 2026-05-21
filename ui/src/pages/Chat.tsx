import { useState } from 'react'
import { Link } from 'react-router-dom'

/**
 * /chat — placeholder. Pitches the future conversational interface
 * and collects an email for "notify me when this is ready".
 */
export default function Chat() {
  const [email, setEmail] = useState('')
  const [submitted, setSubmitted] = useState(false)

  function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    // TODO: wire to a real /api/notify endpoint
    setSubmitted(true)
  }

  return (
    <div className="flex min-h-full flex-col items-center justify-center bg-gradient-to-b from-white via-brand-50/30 to-white px-6 py-24">
      <span className="mb-6 inline-flex items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-medium text-amber-800">
        <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
        Coming soon
      </span>

      <h1 className="max-w-2xl text-center text-4xl font-semibold tracking-tight text-slate-900 sm:text-5xl">
        Talk to your report.
      </h1>
      <p className="mt-5 max-w-xl text-center text-base leading-relaxed text-slate-600">
        Ask follow-ups about any pathway, swap a protein, ground a claim in a
        different journal — a conversational interface to iterate on the
        mechanism dashboard, without leaving the page.
      </p>

      <div className="mt-10 w-full max-w-md">
        {submitted ? (
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-center text-sm text-emerald-900">
            Thanks. We'll email you when /chat ships.
          </div>
        ) : (
          <form onSubmit={onSubmit} className="flex items-center gap-2 rounded-full border border-slate-300 bg-white p-1.5 shadow-sm focus-within:border-brand-500 focus-within:ring-1 focus-within:ring-brand-500">
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Notify me when ready — your email"
              className="flex-1 bg-transparent px-3 py-1.5 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none"
            />
            <button
              type="submit"
              className="rounded-full bg-slate-900 px-4 py-1.5 text-xs font-semibold text-white transition hover:bg-slate-800"
            >
              Notify me
            </button>
          </form>
        )}
      </div>

      <div className="mt-12 flex items-center gap-4 text-sm">
        <Link to="/" className="text-slate-500 hover:text-slate-900">
          ← Back to home
        </Link>
        <span className="text-slate-300">·</span>
        <Link to="/demo" className="font-medium text-brand-600 hover:text-brand-700">
          Try the demo instead →
        </Link>
      </div>
    </div>
  )
}
