import { SectionHeader } from './HowItWorks'

type Member = {
  name: string
  role: string
  affiliation: string
  initials: string
}

// Placeholder until real team info is provided.
const TEAM: Member[] = [
  { name: 'TBD', role: 'Principal Investigator', affiliation: 'University of Pennsylvania', initials: 'PI' },
  { name: 'Joy Wang', role: 'Lead Developer', affiliation: 'Peking University', initials: 'JW' },
  { name: 'Jiayi', role: 'Method Design', affiliation: 'Collaborator', initials: 'JY' },
  { name: 'Jason Jiang', role: 'Infrastructure', affiliation: 'Collaborator', initials: 'JJ' },
]

export function Team() {
  return (
    <section className="py-24" id="team">
      <div className="mx-auto max-w-7xl px-6">
        <SectionHeader
          eyebrow="Who we are"
          title="The team behind BioVoyager"
          description="A multi-institutional collaboration combining bioinformatics, LLM systems, and clinical proteomics."
        />
        <div className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {TEAM.map((m) => (
            <MemberCard key={m.name} member={m} />
          ))}
        </div>
      </div>
    </section>
  )
}

function MemberCard({ member }: { member: Member }) {
  return (
    <div className="group rounded-2xl border border-slate-200 bg-white p-6 text-center transition hover:-translate-y-0.5 hover:border-brand-300 hover:shadow-lg">
      <div className="mx-auto grid h-20 w-20 place-items-center rounded-full bg-gradient-to-br from-brand-100 to-cyan-100 text-xl font-bold text-brand-700 ring-4 ring-white">
        {member.initials}
      </div>
      <h3 className="mt-4 text-base font-semibold text-slate-900">{member.name}</h3>
      <p className="mt-0.5 text-sm text-brand-600">{member.role}</p>
      <p className="mt-2 text-xs text-slate-500">{member.affiliation}</p>
    </div>
  )
}
