import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'

interface DonutChartProps {
  data: { name: string; value: number }[]
  title?: string
}

const colors = ['#ef4444', '#22c55e', '#f59e0b']

export function DonutChart({ data, title }: DonutChartProps) {
  if (!data.length || data.every((d) => d.value === 0)) return null

  return (
    <div className="space-y-4">
      {title && <h3 className="text-sm font-medium text-text-secondary">{title}</h3>}
      <ResponsiveContainer width="100%" height={250}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={90}
            paddingAngle={5}
            dataKey="value"
          >
            {data.map((_, index) => (
              <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: 'rgba(18,18,26,0.95)',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '8px',
              color: '#f5f5f5',
            }}
          />
          <Legend
            formatter={(value: string) => <span className="text-text-secondary text-sm">{value}</span>}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
