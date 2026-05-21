export function ErrorState({ error }: { error: string }) {
  return (
    <div className="flex h-full flex-col items-center justify-center bg-slate-50 p-8">
      <div className="max-w-md rounded-xl border border-rose-200 bg-rose-50 p-6 text-rose-900">
        <h2 className="text-lg font-semibold">Failed to load diseases</h2>
        <p className="mt-2 text-sm">{error}</p>
        <p className="mt-3 text-sm text-rose-700">
          Is the FastAPI backend running on <code>localhost:5000</code>?
        </p>
      </div>
    </div>
  )
}
