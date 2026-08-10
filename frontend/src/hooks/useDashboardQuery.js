import { useCallback, useEffect, useState } from 'react'

/** Loads a single dataset endpoint with graceful demo-data fallback. */
export function useDashboardQuery(query, deps = []) {
  const [state, setState] = useState({ loading: true, live: true, data: null })

  const load = useCallback(async () => {
    setState((s) => ({ ...s, loading: true }))
    const res = await query()
    setState({ loading: false, live: res.live, data: res.data })
  }, deps) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    load()
  }, [load])

  return { ...state, refresh: load }
}
