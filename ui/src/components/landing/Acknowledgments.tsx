import { SectionHeader } from './HowItWorks'

export function Acknowledgments() {
  return (
    <section className="border-t border-slate-200/60 bg-slate-50/60 py-20" id="acknowledgments">
      <div className="mx-auto max-w-4xl px-6">
        <SectionHeader
          eyebrow="Acknowledgments"
          title="Built on shared scientific infrastructure"
          description="BioVoyager would not be possible without the open biomedical data ecosystem."
        />

        <div className="mt-12 grid gap-4 sm:grid-cols-2">
          {[
            ['UK Biobank', 'Plasma proteomics cohort'],
            ['g:Profiler', 'Pathway enrichment'],
            ['PubMed / NCBI', 'Literature evidence'],
            ['Semantic Scholar', 'Snippet & ranking'],
            ['STRING-DB', 'Protein interaction networks'],
            ['DGIdb', 'Drug-gene interactions'],
            ['BioBERT (dmis-lab)', 'Biomedical embeddings'],
            ['OpenAI', 'GPT family of agents'],
          ].map(([name, desc]) => (
            <div
              key={name}
              className="flex items-center justify-between rounded-lg border border-slate-200 bg-white px-4 py-3"
            >
              <span className="text-sm font-medium text-slate-900">{name}</span>
              <span className="text-xs text-slate-500">{desc}</span>
            </div>
          ))}
        </div>

        <p className="mt-12 text-center text-xs text-slate-500">
          Funding: TBD — research grant acknowledgments will be added when the paper is finalized.
        </p>
      </div>
    </section>
  )
}
