import { useEffect, useState } from 'react'
import { fetchDiseases } from '../lib/api'
import type { Disease } from '../types'

type State =
  | { status: 'loading' }
  | { status: 'ready'; diseases: Disease[] }
  | { status: 'error'; error: string }

export function useDiseases(): State {
  const [state, setState] = useState<State>({ status: 'loading' })

  useEffect(() => {
    const ctl = new AbortController()
    fetchDiseases(ctl.signal)
      .then((diseases) => setState({ status: 'ready', diseases }))
      .catch((e: unknown) => {
        if (e instanceof DOMException && e.name === 'AbortError') return
        setState({ status: 'error', error: e instanceof Error ? e.message : String(e) })
      })
    return () => ctl.abort()
  }, [])

  return state
}
