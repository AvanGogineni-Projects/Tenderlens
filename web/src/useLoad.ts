import { useEffect, useState } from 'react'

/** Load data for a page; refetches when `deps` change and ignores answers for stale deps. */
export function useLoad<T>(load: () => Promise<T>, deps: unknown[]): { data?: T; error?: string } {
  const [state, setState] = useState<{ data?: T; error?: string }>({})
  useEffect(() => {
    let live = true
    setState({})
    load().then((data) => live && setState({ data }), (e: Error) => live && setState({ error: e.message }))
    return () => { live = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  return state
}
