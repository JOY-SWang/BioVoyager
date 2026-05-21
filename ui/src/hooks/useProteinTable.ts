import { useMemo, useState } from 'react'
import type { Protein, SortDir, SortKey } from '../types'

const NUMERIC_KEYS: ReadonlySet<SortKey> = new Set(['p_value', 'nb_case', 'nb_individual'])

export function useProteinTable(proteins: Protein[]) {
  const [search, setSearch] = useState('')
  const [sortKey, setSortKey] = useState<SortKey | null>(null)
  const [sortDir, setSortDir] = useState<SortDir>('asc')

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  function reset() {
    setSearch('')
    setSortKey(null)
    setSortDir('asc')
  }

  const rows = useMemo(() => {
    let out = proteins
    if (search.trim()) {
      const q = search.toLowerCase()
      out = out.filter(
        (r) =>
          r.protein.toLowerCase().includes(q) ||
          r.definition.toLowerCase().includes(q),
      )
    }
    if (sortKey) {
      const numeric = NUMERIC_KEYS.has(sortKey)
      out = [...out].sort((a, b) => {
        const av = numeric ? parseFloat(a[sortKey]) || 0 : a[sortKey].toLowerCase()
        const bv = numeric ? parseFloat(b[sortKey]) || 0 : b[sortKey].toLowerCase()
        const cmp = av < bv ? -1 : av > bv ? 1 : 0
        return sortDir === 'asc' ? cmp : -cmp
      })
    }
    return out
  }, [proteins, search, sortKey, sortDir])

  return { rows, search, setSearch, sortKey, sortDir, toggleSort, reset }
}
