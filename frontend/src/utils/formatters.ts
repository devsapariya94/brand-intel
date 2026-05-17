export function formatDateTime(dtStr: string): string {
  if (!dtStr) return 'N/A'
  try {
    const dt = new Date(dtStr)
    return dt.toLocaleString('en-US', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    })
  } catch {
    return dtStr
  }
}

export function formatRelativeTime(dtStr: string): string {
  if (!dtStr) return 'Never'
  try {
    const dt = new Date(dtStr)
    const now = new Date()
    const diff = Math.floor((now.getTime() - dt.getTime()) / 1000)

    if (diff < 60) return `${diff}s ago`
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
    return `${Math.floor(diff / 86400)}d ago`
  } catch {
    return dtStr
  }
}

export function formatNumber(num: number): string {
  if (num == null) return '0'
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`
  if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`
  return String(num)
}

export function formatPercentage(value: number): string {
  return `${(value * 100).toFixed(1)}%`
}
