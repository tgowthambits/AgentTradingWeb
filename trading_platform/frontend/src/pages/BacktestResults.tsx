import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { backtestApi } from '../services/api'
import { ArrowLeft, TrendingUp, TrendingDown, Target, AlertTriangle } from 'lucide-react'

export default function BacktestResults() {
  const { id } = useParams()

  const { data: session } = useQuery({
    queryKey: ['backtest', id],
    queryFn: () => backtestApi.get(id!),
  })

  const { data: result, isLoading } = useQuery({
    queryKey: ['backtest-result', id],
    queryFn: () => backtestApi.getResult(id!),
    enabled: session?.data?.status === 'completed',
  })

  const { data: trades } = useQuery({
    queryKey: ['backtest-trades', id],
    queryFn: () => backtestApi.getTrades(id!),
    enabled: session?.data?.status === 'completed',
  })

  if (isLoading || !result) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  const r = result.data
  const tradeList = trades?.data || []

  const stats = [
    { name: 'Total P&L', value: `₹${r.total_pnl.toLocaleString()}`, positive: r.total_pnl >= 0, icon: r.total_pnl >= 0 ? TrendingUp : TrendingDown },
    { name: 'Return', value: `${r.total_return_pct.toFixed(2)}%`, positive: r.total_return_pct >= 0 },
    { name: 'Win Rate', value: `${r.win_rate.toFixed(1)}%`, icon: Target },
    { name: 'Profit Factor', value: r.profit_factor.toFixed(2) },
    { name: 'Sharpe Ratio', value: r.sharpe_ratio.toFixed(2) },
    { name: 'Max Drawdown', value: `${r.max_drawdown_pct.toFixed(2)}%`, icon: AlertTriangle },
    { name: 'Total Trades', value: r.total_trades },
    { name: 'Winners', value: r.winning_trades },
    { name: 'Losers', value: r.losing_trades },
    { name: 'Avg Win', value: `₹${r.avg_win.toLocaleString()}` },
    { name: 'Avg Loss', value: `₹${Math.abs(r.avg_loss).toLocaleString()}` },
    { name: 'Max Consecutive Losses', value: r.max_consecutive_losses },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link to="/backtest" className="p-2 rounded-md hover:bg-accent">
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div>
          <h1 className="text-xl font-semibold">Backtest Results</h1>
          <p className="text-sm text-muted-foreground">
            {session?.data?.strategy_name} | {session?.data?.start_date} - {session?.data?.end_date}
          </p>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {stats.map((stat) => (
          <div key={stat.name} className="bg-card border border-border rounded-lg p-4">
            <p className="text-sm text-muted-foreground">{stat.name}</p>
            <p className={`text-lg font-semibold mt-1 ${
              stat.positive !== undefined
                ? stat.positive ? 'text-profit' : 'text-loss'
                : ''
            }`}>
              {stat.value}
            </p>
          </div>
        ))}
      </div>

      {/* Equity Curve */}
      <div className="bg-card border border-border rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4">Equity Curve</h2>
        <div className="h-64 flex items-center justify-center text-muted-foreground">
          <p>Equity curve chart placeholder</p>
        </div>
      </div>

      {/* Trades Table */}
      <div className="bg-card border border-border rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4">Trade History</h2>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">#</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Symbol</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Type</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">Entry</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">Exit</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">P&L</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Exit Reason</th>
              </tr>
            </thead>
            <tbody>
              {tradeList.slice(0, 50).map((trade: { trade_number: number; symbol: string; trade_type: string; entry_price: number; exit_price: number; net_pnl: number; exit_reason: string }) => (
                <tr key={trade.trade_number} className="border-b border-border">
                  <td className="py-3 px-4">{trade.trade_number}</td>
                  <td className="py-3 px-4">{trade.symbol}</td>
                  <td className="py-3 px-4">
                    <span className={trade.trade_type === 'LONG' ? 'text-profit' : 'text-loss'}>
                      {trade.trade_type}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right">{trade.entry_price.toFixed(2)}</td>
                  <td className="py-3 px-4 text-right">{trade.exit_price.toFixed(2)}</td>
                  <td className={`py-3 px-4 text-right ${trade.net_pnl >= 0 ? 'text-profit' : 'text-loss'}`}>
                    ₹{trade.net_pnl.toLocaleString()}
                  </td>
                  <td className="py-3 px-4 capitalize">{trade.exit_reason.replace('_', ' ')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
