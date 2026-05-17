import { Sidebar } from './Sidebar'
import { Header } from './Header'

interface PageLayoutProps {
  title: string
  children: React.ReactNode
  onRefresh?: () => void
}

export function PageLayout({ title, children, onRefresh }: PageLayoutProps) {
  return (
    <div className="min-h-screen bg-bg-primary">
      <Sidebar />
      <div className="ml-64">
        <Header title={title} onRefresh={onRefresh} />
        <main className="p-6">{children}</main>
      </div>
    </div>
  )
}
