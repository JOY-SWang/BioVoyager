import { reportUrl } from '../lib/api'

type Props = {
  report: string
  diseaseName: string
  onBack: () => void
}

export function ReportView({ report, diseaseName, onBack }: Props) {
  const src = reportUrl(report)
  return (
    <div className="flex h-full flex-col">
      <ReportToolbar diseaseName={diseaseName} src={src} onBack={onBack} />
      <iframe
        src={src}
        title={diseaseName}
        className="flex-1 border-0 bg-white"
      />
    </div>
  )
}

function ReportToolbar({
  diseaseName,
  src,
  onBack,
}: {
  diseaseName: string
  src: string
  onBack: () => void
}) {
  return (
    <div className="flex items-center gap-3 border-b border-slate-200 bg-white px-6 py-2.5">
      <button
        onClick={onBack}
        className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-slate-600 transition hover:bg-slate-100"
      >
        <ArrowLeft />
        Back to {diseaseName}
      </button>
      <span className="text-xs text-slate-400">·</span>
      <span className="text-xs text-slate-600">Interactive v3 report</span>
      <a
        href={src}
        target="_blank"
        rel="noreferrer"
        className="ml-auto text-xs text-brand-600 hover:underline"
      >
        Open in new tab ↗
      </a>
    </div>
  )
}

function ArrowLeft() {
  return (
    <svg className="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden>
      <path d="M19 12H5M12 19l-7-7 7-7" />
    </svg>
  )
}
