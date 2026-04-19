import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { strategyApi } from '../services/api'
import { Plus, Edit, Copy, Trash2, Play } from 'lucide-react'

export default function Strategies() {
  const queryClient = useQueryClient()

  const { data: strategies, isLoading } = useQuery({
    queryKey: ['strategies'],
    queryFn: () => strategyApi.list(),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => strategyApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategies'] })
    },
  })

  const duplicateMutation = useMutation({
    mutationFn: (id: string) => strategyApi.duplicate(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategies'] })
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  const strategyList = strategies?.data || []

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold">Your Strategies</h2>
        <Link
          to="/strategies/new"
          className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
        >
          <Plus className="h-4 w-4" />
          New Strategy
        </Link>
      </div>

      {strategyList.length === 0 ? (
        <div className="bg-card border border-border rounded-lg p-12 text-center">
          <p className="text-muted-foreground mb-4">No strategies yet</p>
          <Link
            to="/strategies/new"
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            <Plus className="h-4 w-4" />
            Create your first strategy
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {strategyList.map((strategy: { id: string; name: string; description: string; symbols: string[]; aggregation_strategy: string; is_active: boolean; is_live: boolean; updated_at: string }) => (
            <div
              key={strategy.id}
              className="bg-card border border-border rounded-lg p-6"
            >
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="font-semibold">{strategy.name}</h3>
                  <p className="text-sm text-muted-foreground">
                    {strategy.description || 'No description'}
                  </p>
                </div>
                <span
                  className={`px-2 py-1 text-xs rounded-full ${
                    strategy.is_live
                      ? 'bg-profit/20 text-profit'
                      : strategy.is_active
                      ? 'bg-blue-500/20 text-blue-500'
                      : 'bg-muted text-muted-foreground'
                  }`}
                >
                  {strategy.is_live ? 'Live' : strategy.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>

              <div className="space-y-2 text-sm text-muted-foreground mb-4">
                <p>Symbols: {strategy.symbols?.join(', ') || 'None'}</p>
                <p>Aggregation: {strategy.aggregation_strategy}</p>
                <p>
                  Updated: {new Date(strategy.updated_at).toLocaleDateString()}
                </p>
              </div>

              <div className="flex gap-2">
                <Link
                  to={`/strategies/${strategy.id}`}
                  className="flex-1 flex items-center justify-center gap-1 px-3 py-2 bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/80 text-sm"
                >
                  <Edit className="h-4 w-4" />
                  Edit
                </Link>
                <button
                  onClick={() => duplicateMutation.mutate(strategy.id)}
                  className="px-3 py-2 bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/80"
                  title="Duplicate"
                >
                  <Copy className="h-4 w-4" />
                </button>
                <Link
                  to={`/backtest?strategy=${strategy.id}`}
                  className="px-3 py-2 bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/80"
                  title="Run Backtest"
                >
                  <Play className="h-4 w-4" />
                </Link>
                <button
                  onClick={() => {
                    if (confirm('Delete this strategy?')) {
                      deleteMutation.mutate(strategy.id)
                    }
                  }}
                  className="px-3 py-2 bg-destructive/10 text-destructive rounded-md hover:bg-destructive/20"
                  title="Delete"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
