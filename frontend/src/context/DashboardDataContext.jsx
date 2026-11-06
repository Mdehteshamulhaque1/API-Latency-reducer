import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { apiClient } from '../lib/apiClient'

const DashboardDataContext = createContext(null)

export function DashboardDataProvider({ hours = 24, children }) {
  const [state, setState] = useState({
    loading: true,
    live: true,
    summary: null,
    rules: [],
    health: null,
  })

  const load = useCallback(async () => {
    setState((s) => ({ ...s, loading: true }))
    const [summary, rules, health] = await Promise.all([
      apiClient.summary(hours),
      apiClient.rules(),
      apiClient.health(),
    ])
    setState({
      loading: false,
      live: summary.live && rules.live && health.live,
      summary: summary.data,
      rules: rules.data,
      health: health.data,
    })
  }, [hours])

  useEffect(() => {
    load()
  }, [load])

  const value = useMemo(() => ({ ...state, refresh: load }), [state, load])
  return <DashboardDataContext.Provider value={value}>{children}</DashboardDataContext.Provider>
}

export function useDashboardData() {
  const ctx = useContext(DashboardDataContext)
  if (!ctx) throw new Error('useDashboardData must be used within DashboardDataProvider')
  return ctx
}
