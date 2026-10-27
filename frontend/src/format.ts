export const number = (v: number | null | undefined, digits = 0) => v == null ? '—' : new Intl.NumberFormat('en-IN', { maximumFractionDigits: digits }).format(v);
export const money = (v: number | null | undefined) => v == null ? 'Not configured' : `₹${number(v, 2)}`;
export const percent = (v: number | null | undefined) => v == null ? 'No baseline' : `${v > 0 ? '+' : ''}${v.toFixed(2)}%`;
export function dateLabel(value: string) { return new Date(value).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' }); }
