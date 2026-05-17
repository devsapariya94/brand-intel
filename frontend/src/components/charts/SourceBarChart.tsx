import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

interface SourceBarChartProps {
  data: Record<string, number>
  title?: string
}

const colors = ['#06b6d4', '#22c55e', '#f59e0b', '#a855f7', '#ef4444', '#ec4899']

export function SourceBarChart({ data, title }: SourceBarChartProps) {
  if (!Object.keys(data).length) return null

  const chartData = Object.entries(data).map(([name, value], i) => ({
    name,
    value,
    fill: colors[i % colors.length],
  }))

  return (
    <div className="space-y-4">
      {title && <h3 className="text-sm font-medium text-text-secondary">{title}</h3>}
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
          <XAxis
            dataKey="name"
            stroke="rgba(255,255,255,0.3)"
            tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 12 }}
          />
          <YAxis
            stroke="rgba(255,255,255,0.3)"
            tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 12 }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'rgba(18,18,26,0.95)',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '8px',
              color: '#f5f5f5',
            }}
          />
          <Bar dataKey="value" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
