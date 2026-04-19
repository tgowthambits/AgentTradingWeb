import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import Layout from './components/Layout'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Strategies from './pages/Strategies'
import StrategyBuilder from './pages/StrategyBuilder'
import Backtest from './pages/Backtest'
import BacktestResults from './pages/BacktestResults'
import Settings from './pages/Settings'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore()
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />
}

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-background dark">
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route
            path="/"
            element={
              <PrivateRoute>
                <Layout />
              </PrivateRoute>
            }
          >
            <Route index element={<Dashboard />} />
            <Route path="strategies" element={<Strategies />} />
            <Route path="strategies/new" element={<StrategyBuilder />} />
            <Route path="strategies/:id" element={<StrategyBuilder />} />
            <Route path="backtest" element={<Backtest />} />
            <Route path="backtest/:id" element={<BacktestResults />} />
            <Route path="settings" element={<Settings />} />
          </Route>
        </Routes>
      </div>
    </Router>
  )
}

export default App
