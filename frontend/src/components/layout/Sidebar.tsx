import { NavLink } from 'react-router-dom'
import { cn } from '@/utils/cn'
import {
  LayoutDashboard,
  Building2,
  Satellite,
  AlertTriangle,
  Brain,
  Settings,
  Shield,
} from 'lucide-react'

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/brands', label: 'Brands', icon: Building2 },
  { to: '/monitors', label: 'Monitors', icon: Satellite },
  { to: '/alerts', label: 'Alerts', icon: AlertTriangle },
  { to: '/enrichment', label: 'Enrichment', icon: Brain },
  { to: '/admin', label: 'Admin', icon: Settings },
]

export function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 h-full w-64 bg-bg-secondary border-r border-border-subtle flex flex-col z-40">
      <div className="p-6 border-b border-border-subtle">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-cyan-neon/10 flex items-center justify-center">
            <Shield className="w-5 h-5 text-cyan-neon" />
          </div>
          <div>
            <h1 className="font-bold text-text-primary text-lg">Brand Intel</h1>
            <p className="text-xs text-text-muted">Threat Monitoring</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 p-4 space-y-1">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200',
                isActive
                  ? 'bg-cyan-neon/10 text-cyan-neon'
                  : 'text-text-secondary hover:text-text-primary hover:bg-white/5'
              )
            }
          >
            <Icon className="w-4 h-4" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="p-4 border-t border-border-subtle">
        <div className="flex items-center gap-2 text-xs text-text-muted">
          <div className="w-2 h-2 rounded-full bg-green-neon animate-pulse" />
          System Online
        </div>
      </div>
    </aside>
  )
}
