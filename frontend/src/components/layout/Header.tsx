import { useQuery } from '@tanstack/react-query'
import { healthApi } from '@/api/health'
import { Badge } from '@/components/ui/Badge'
import { RefreshCw } from 'lucide-react'

interface HeaderProps {
  title: string
  onRefresh?: () => void
}

export function Header({ title, onRefresh }: HeaderProps) {
  const { data: health, isLoading } = useQuery({
    queryKey: ['health'],
    queryFn: healthApi.get,
    refetchInterval: 30000,
    retry: false,
  })

  return (
    <header className="sticky top-0 z-30 bg-bg-primary/80 backdrop-blur-xl border-b border-border-subtle px-6 py-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-text-primary">{title}</h1>
        <div className="flex items-center gap-4">
          {isLoading ? (
            <Badge variant="default">Checking...</Badge>
          ) : health?.status === 'healthy' ? (
            <Badge variant="success" dot>API Connected</Badge>
          ) : (
            <Badge variant="danger" dot>API Disconnected</Badge>
          )}
          {onRefresh && (
            <button
              onClick={onRefresh}
              className="p-2 rounded-lg hover:bg-white/5 text-text-muted hover:text-text-primary transition-all"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </header>
  )
}
