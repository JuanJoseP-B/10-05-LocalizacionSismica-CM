export function formatNumber(value, fixedDigits = 4) {
  if (value == null || Number.isNaN(value)) return '—';
  if (value === 0) return '0';
  const abs = Math.abs(value);
  if (abs < 1e-3 || abs >= 1e6) return value.toExponential(3);
  return value.toFixed(fixedDigits);
}

export function formatPercent(value) {
  return `${Math.max(0, value).toFixed(1)}%`;
}
