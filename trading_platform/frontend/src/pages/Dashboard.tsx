import { useQuery } from '@tanstack/react-query'
import { dashboardApi } from '../services/api'
import { TrendingUp, TrendingDown, DollarSign, Activity, Target, BarChart2 } from 'lucide-react'

export default function Dashboard() {
  const { data: summary, isLoading } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: () => dashboardApi.getSummary(),
    refetchInterval: 5000,
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  const data = summary?.data || {
    total_capital: 100000,
    total_pnl: 0,
    total_pnl_pct: 0,
    open_positions: 0,
    total_trades_today: 0,
    winning_trades_today: 0,
    win_rate_today: 0,
  }

  const stats = [
    {
      name: 'Total Capital',
      value: `₹${data.total_capital.toLocaleString()}`,
      icon: DollarSign,
      change: null,
    },
    {
      name: 'Total P&L',
      value: `₹${data.total_pnl.toLocaleString()}`,
      icon: data.total_pnl >= 0 ? TrendingUp : TrendingDown,
      change: `${data.total_pnl_pct >= 0 ? '+' : ''}${data.total_pnl_pct.toFixed(2)}%`,
      positive: data.total_pnl >= 0,
    },
    {
      name: 'Open Positions',
      value: data.open_positions,
      icon: Activity,
      change: null,
    },
    {
      name: 'Trades Today',
      value: data.total_trades_today,
      icon: BarChart2,
      change: null,
    },
    {
      name: 'Winners Today',
      value: data.winning_trades_today,
      icon: Target,
      change: null,
    },
    {
      name: 'Win Rate',
      value: `${data.win_rate_today.toFixed(1)}%`,
      icon: TrendingUp,
      change: null,
    },
  ]

  return (
    <div className="space-y-6">
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {stats.map((stat) => (
          <div
            key={stat.name}
            className="bg-card border border-border rounded-lg p-6"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">{stat.name}</p>
                <p className="text-2xl font-semibold mt-1">{stat.value}</p>
                {stat.change && (
                  <p
                    className={`text-sm mt-1 ${
                      stat.positive ? 'text-profit' : 'text-loss'
                    }`}
                  >
                    {stat.change}
                  </p>
                )}
              </div>
              <stat.icon
                className={`h-8 w-8 ${
                  stat.positive !== undefined
                    ? stat.positive
                      ? 'text-profit'
                      : 'text-loss'
                    : 'text-muted-foreground'
                }`}
              />
            </div>
          </div>
        ))}
      </div>

      {/* Chart Placeholder */}
      <div className="bg-card border border-border rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4">Equity Curve</h2>
        <div className="h-96 flex items-center justify-center text-muted-foreground">
          <p>Chart will be displayed here when trading data is available</p>
        </div>
      </div>

      {/* Positions Table */}
      <div className="bg-card border border-border rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4">Open Positions</h2>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Symbol</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Type</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">Qty</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">Entry</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">Current</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">P&L</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td colSpan={6} className="text-center py-8 text-muted-foreground">
                  No open positions
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
