import axios from 'axios'
import { useAuthStore } from '../store/authStore'

const API_BASE_URL = '/api'

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const { accessToken } = useAuthStore.getState()
    if (accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      const { refreshToken, setAuth, logout } = useAuthStore.getState()

      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          })

          const { access_token, refresh_token } = response.data
          const userResponse = await axios.get(`${API_BASE_URL}/auth/me`, {
            headers: { Authorization: `Bearer ${access_token}` },
          })

          setAuth(userResponse.data, access_token, refresh_token)
          originalRequest.headers.Authorization = `Bearer ${access_token}`

          return api(originalRequest)
        } catch {
          logout()
        }
      }
    }

    return Promise.reject(error)
  }
)

// Auth API
export const authApi = {
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),

  register: (email: string, username: string, password: string) =>
    api.post('/auth/register', { email, username, password }),

  getMe: () => api.get('/auth/me'),

  updateMe: (data: Record<string, unknown>) => api.patch('/auth/me', data),
}

// Strategy API
export const strategyApi = {
  list: () => api.get('/strategies'),

  get: (id: string) => api.get(`/strategies/${id}`),

  create: (data: Record<string, unknown>) => api.post('/strategies', data),

  update: (id: string, data: Record<string, unknown>) =>
    api.patch(`/strategies/${id}`, data),

  delete: (id: string) => api.delete(`/strategies/${id}`),

  duplicate: (id: string) => api.post(`/strategies/${id}/duplicate`),
}

// Backtest API
export const backtestApi = {
  list: () => api.get('/backtests'),

  get: (id: string) => api.get(`/backtests/${id}`),

  create: (data: Record<string, unknown>) => api.post('/backtests', data),

  getResult: (id: string) => api.get(`/backtests/${id}/result`),

  getTrades: (id: string) => api.get(`/backtests/${id}/trades`),

  cancel: (id: string) => api.post(`/backtests/${id}/cancel`),

  delete: (id: string) => api.delete(`/backtests/${id}`),
}

// Trading Session API
export const sessionApi = {
  list: () => api.get('/sessions'),

  create: (data: Record<string, unknown>) => api.post('/sessions', data),

  start: (id: string) => api.post(`/sessions/${id}/start`),

  stop: (id: string) => api.post(`/sessions/${id}/stop`),

  getPositions: (id: string) => api.get(`/sessions/${id}/positions`),

  getOrders: (id: string) => api.get(`/sessions/${id}/orders`),

  getTrades: (id: string) => api.get(`/sessions/${id}/trades`),
}

// Indicator API
export const indicatorApi = {
  list: () => api.get('/indicators'),

  get: (id: string) => api.get(`/indicators/${id}`),
}

// Symbol API
export const symbolApi = {
  list: () => api.get('/symbols'),

  get: (symbol: string) => api.get(`/symbols/${symbol}`),
}

// Market Data API
export const marketDataApi = {
  getCandles: (
    symbol: string,
    timeframe: string = '5m',
    startDate?: string,
    endDate?: string,
    limit: number = 500
  ) =>
    api.post('/market-data/candles', {
      symbol,
      timeframe,
      start_date: startDate,
      end_date: endDate,
      limit,
    }),
}

// Dashboard API
export const dashboardApi = {
  getSummary: () => api.get('/dashboard/summary'),
}
