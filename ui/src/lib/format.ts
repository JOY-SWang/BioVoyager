/** Render a p-value: scientific notation when very small, fixed precision otherwise. */
export function formatPValue(raw: string): string {
  const n = parseFloat(raw)
  if (!isFinite(n)) return raw
  if (Math.abs(n) < 0.001) return n.toExponential(2)
  return n.toPrecision(3)
}
