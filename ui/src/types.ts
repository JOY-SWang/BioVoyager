export type Protein = {
  protein: string
  definition: string
  nb_individual: string
  nb_case: string
  hr: string
  p_value: string
}

export type Disease = {
  name: string
  csv: string
  report: string | null
  category: string
  proteins: Protein[]
  n_proteins: number
}

export type SortKey = keyof Protein
export type SortDir = 'asc' | 'desc'
