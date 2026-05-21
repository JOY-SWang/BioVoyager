export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex h-full items-center justify-center bg-slate-50 text-slate-500">
      <div className="flex items-center gap-3">
        <Spinner />
        {label}
      </div>
    </div>
  )
}

function Spinner() {
  return (
    <div
      role="status"
      aria-label="Loading"
      className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-slate-700"
    />
  )
}
