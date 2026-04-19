import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useAuthStore } from '../store/authStore'
import { authApi } from '../services/api'
import { Save } from 'lucide-react'

export default function Settings() {
  const { user, updateUser } = useAuthStore()

  const [username, setUsername] = useState(user?.username || '')
  const [defaultCapital, setDefaultCapital] = useState(user?.default_capital?.toString() || '100000')
  const [timezone, setTimezone] = useState(user?.timezone || 'Asia/Kolkata')
  const [brokerType, setBrokerType] = useState(user?.broker_type || 'paper')

  const updateMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => authApi.updateMe(data),
    onSuccess: (response) => {
      updateUser(response.data)
    },
  })

  const handleSave = () => {
    updateMutation.mutate({
      username,
      default_capital: parseFloat(defaultCapital),
      timezone,
      broker_type: brokerType,
    })
  }

  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="text-xl font-semibold">Settings</h1>

      <div className="bg-card border border-border rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4">Profile Settings</h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Email</label>
            <input
              type="email"
              value={user?.email || ''}
              disabled
              className="w-full px-3 py-2 bg-muted border border-input rounded-md text-muted-foreground"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-3 py-2 bg-background border border-input rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Default Capital</label>
            <input
              type="number"
              value={defaultCapital}
              onChange={(e) => setDefaultCapital(e.target.value)}
              className="w-full px-3 py-2 bg-background border border-input rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Timezone</label>
            <select
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
              className="w-full px-3 py-2 bg-background border border-input rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="Asia/Kolkata">Asia/Kolkata (IST)</option>
              <option value="UTC">UTC</option>
              <option value="America/New_York">America/New_York (EST)</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Broker Type</label>
            <select
              value={brokerType}
              onChange={(e) => setBrokerType(e.target.value)}
              className="w-full px-3 py-2 bg-background border border-input rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="paper">Paper Trading</option>
              <option value="zerodha">Zerodha</option>
              <option value="flattrade">FlatTrade</option>
            </select>
          </div>
        </div>

        <button
          onClick={handleSave}
          disabled={updateMutation.isPending}
          className="mt-6 flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50"
        >
          <Save className="h-4 w-4" />
          {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
        </button>

        {updateMutation.isSuccess && (
          <p className="mt-2 text-sm text-profit">Settings saved successfully!</p>
        )}
      </div>
    </div>
  )
}
