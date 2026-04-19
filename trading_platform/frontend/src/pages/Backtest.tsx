import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { backtestApi, strategyApi } from '../services/api'
import { Play, Clock, CheckCircle, XCircle, AlertCircle } from 'lucide-react'

export default function Backtest() {
  const [searchParams] = useSearchParams()
  const queryClient = useQueryClient()

  const [selectedStrategy, setSelectedStrategy] = useState(searchParams.get('strategy') || '')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [initialCapital, setInitialCapital] = useState('100000')

  const { data: strategies } = useQuery({
    queryKey: ['strategies'],
    queryFn: () => strategyApi.list(),
  })

  const { data: backtests, isLoading } = useQuery({
    queryKey: ['backtests'],
    queryFn: () => backtestApi.list(),
    refetchInterval: 5000,
  })

  const createMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => backtestApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['backtests'] })
    },
  })

  const handleRunBacktest = () => {
    if (!selectedStrategy || !startDate || !endDate) return

    createMutation.mutate({
      strategy_id: selectedStrategy,
      start_date: startDate,
      end_date: endDate,
      initial_capital: parseFloat(initialCapital),
    })
  }

  const strategyList = strategies?.data || []
  const backtestList = backtests?.data || []

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-profit" />
      case 'running':
        return <Clock className="h-5 w-5 text-blue-500 animate-pulse" />
      case 'failed':
        return <XCircle className="h-5 w-5 text-loss" />
      default:
        return <AlertCircle className="h-5 w-5 text-muted-foreground" />
    }
  }

  return (
    <div className="space-y-6">
      {/* Run Backtest Form */}
      <div className="bg-card border border-border rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4">Run Backtest</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Strategy</label>
            <select
              value={selectedStrategy}
              onChange={(e) => setSelectedStrategy(e.target.value)}
              className="w-full px-3 py-2 bg-background border border-input rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="">Select a strategy</option>
              {strategyList.map((s: { id: string; name: string }) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Start Date</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full px-3 py-2 bg-background border border-input rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">End Date</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full px-3 py-2 bg-background border border-input rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Initial Capital</label>
            <input
              type="number"
              value={initialCapital}
              onChange={(e) => setInitialCapital(e.target.value)}
              className="w-full px-3 py-2 bg-background border border-input rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>

          <div className="flex items-end">
            <button
              onClick={handleRunBacktest}
              disabled={!selectedStrategy || !startDate || !endDate || createMutation.isPending}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50"
            >
              <Play className="h-4 w-4" />
              Run Backtest
            </button>
          </div>
        </div>
      </div>

      {/* Backtest History */}
      <div className="bg-card border border-border rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4">Backtest History</h2>

        {isLoading ? (
          <div className="flex items-center justify-center h-32">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        ) : backtestList.length === 0 ? (
          <p className="text-center py-8 text-muted-foreground">
            No backtests yet. Run your first backtest above.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Status</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Strategy</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Period</th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">Progress</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Created</th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">Actions</th>
                </tr>
              </thead>
              <tbody>
                {backtestList.map((bt: { id: string; status: string; strategy_name: string; start_date: string; end_date: string; progress: number; created_at: string }) => (
                  <tr key={bt.id} className="border-b border-border">
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        {getStatusIcon(bt.status)}
                        <span className="capitalize">{bt.status}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4">{bt.strategy_name}</td>
                    <td className="py-3 px-4 text-sm">
                      {bt.start_date} - {bt.end_date}
                    </td>
                    <td className="py-3 px-4 text-right">
                      {bt.status === 'running' ? (
                        <div className="flex items-center justify-end gap-2">
                          <div className="w-24 h-2 bg-muted rounded-full overflow-hidden">
                            <div
                              className="h-full bg-primary transition-all"
                              style={{ width: `${bt.progress}%` }}
                            />
                          </div>
                          <span className="text-sm">{bt.progress}%</span>
                        </div>
                      ) : (
                        '-'
                      )}
                    </td>
                    <td className="py-3 px-4 text-sm text-muted-foreground">
                      {new Date(bt.created_at).toLocaleString()}
                    </td>
                    <td className="py-3 px-4 text-right">
                      {bt.status === 'completed' && (
                        <Link
                          to={`/backtest/${bt.id}`}
                          className="text-primary hover:underline text-sm"
                        >
                          View Results
                        </Link>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
