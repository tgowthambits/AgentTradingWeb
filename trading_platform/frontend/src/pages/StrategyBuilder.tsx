import { useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { strategyApi, indicatorApi } from '../services/api'
import { Save, ArrowLeft } from 'lucide-react'

const initialNodes: Node[] = [
  {
    id: 'start',
    type: 'input',
    data: { label: 'Market Data' },
    position: { x: 250, y: 0 },
  },
  {
    id: 'signal',
    type: 'default',
    data: { label: 'Signal Aggregator' },
    position: { x: 250, y: 200 },
  },
  {
    id: 'end',
    type: 'output',
    data: { label: 'Trade Decision' },
    position: { x: 250, y: 400 },
  },
]

const initialEdges: Edge[] = [
  { id: 'e1', source: 'start', target: 'signal' },
  { id: 'e2', source: 'signal', target: 'end' },
]

export default function StrategyBuilder() {
  const { id } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const isNew = !id || id === 'new'

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)
  
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [symbols, setSymbols] = useState<string[]>([])
  const [aggregationStrategy, setAggregationStrategy] = useState('weighted')

  const { data: indicatorsData } = useQuery({
    queryKey: ['indicators'],
    queryFn: () => indicatorApi.list(),
  })

  const { isLoading } = useQuery({
    queryKey: ['strategy', id],
    queryFn: () => strategyApi.get(id!),
    enabled: !isNew,
    onSuccess: (data) => {
      setName(data.data.name)
      setDescription(data.data.description || '')
      setSymbols(data.data.symbols || [])
      setAggregationStrategy(data.data.aggregation_strategy)
      if (data.data.flow_config?.nodes) {
        setNodes(data.data.flow_config.nodes)
      }
      if (data.data.flow_config?.edges) {
        setEdges(data.data.flow_config.edges)
      }
    },
  })

  const saveMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) =>
      isNew ? strategyApi.create(data) : strategyApi.update(id!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategies'] })
      navigate('/strategies')
    },
  })

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  )

  const handleSave = () => {
    saveMutation.mutate({
      name,
      description,
      symbols,
      aggregation_strategy: aggregationStrategy,
      flow_config: { nodes, edges },
    })
  }

  const indicators = indicatorsData?.data || []

  if (!isNew && isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/strategies')}
            className="p-2 rounded-md hover:bg-accent"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Strategy Name"
            className="text-xl font-semibold bg-transparent border-b border-transparent hover:border-border focus:border-primary focus:outline-none px-2 py-1"
          />
        </div>
        <button
          onClick={handleSave}
          disabled={saveMutation.isPending || !name}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50"
        >
          <Save className="h-4 w-4" />
          Save Strategy
        </button>
      </div>

      <div className="flex-1 flex gap-4">
        {/* Left Panel - Configuration */}
        <div className="w-80 bg-card border border-border rounded-lg p-4 overflow-y-auto">
          <h3 className="font-semibold mb-4">Configuration</h3>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Description</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Strategy description..."
                className="w-full px-3 py-2 bg-background border border-input rounded-md focus:outline-none focus:ring-2 focus:ring-ring text-sm"
                rows={3}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Symbols</label>
              <input
                type="text"
                value={symbols.join(', ')}
                onChange={(e) =>
                  setSymbols(
                    e.target.value.split(',').map((s) => s.trim().toUpperCase())
                  )
                }
                placeholder="NIFTY, BANKNIFTY"
                className="w-full px-3 py-2 bg-background border border-input rounded-md focus:outline-none focus:ring-2 focus:ring-ring text-sm"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">
                Aggregation Strategy
              </label>
              <select
                value={aggregationStrategy}
                onChange={(e) => setAggregationStrategy(e.target.value)}
                className="w-full px-3 py-2 bg-background border border-input rounded-md focus:outline-none focus:ring-2 focus:ring-ring text-sm"
              >
                <option value="weighted">Weighted</option>
                <option value="majority">Majority</option>
                <option value="unanimous">Unanimous</option>
                <option value="conservative">Conservative</option>
                <option value="threshold">Threshold</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">
                Available Indicators
              </label>
              <div className="space-y-2">
                {indicators.map((ind: { id: string; display_name: string; indicator_type: string }) => (
                  <div
                    key={ind.id}
                    className="p-2 bg-background border border-border rounded text-sm cursor-pointer hover:border-primary"
                    draggable
                    onDragStart={(e) => {
                      e.dataTransfer.setData('indicator', JSON.stringify(ind))
                    }}
                  >
                    <p className="font-medium">{ind.display_name}</p>
                    <p className="text-xs text-muted-foreground">
                      {ind.indicator_type}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Flow Canvas */}
        <div className="flex-1 bg-card border border-border rounded-lg overflow-hidden">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            fitView
          >
            <Controls />
            <Background />
          </ReactFlow>
        </div>
      </div>
    </div>
  )
}
