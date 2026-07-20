import type { AlertRecord, AppData, Backtests, Dashboard, IntradaySnapshot } from './types'

const CACHE_KEY = 'stock-sentinel-data-v1'

export function readCachedAppData(): AppData | null {
  try {
    const cached = localStorage.getItem(CACHE_KEY)
    return cached ? { ...(JSON.parse(cached) as AppData), cached: true } : null
  } catch {
    localStorage.removeItem(CACHE_KEY)
    return null
  }
}

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { cache: 'no-store', signal: AbortSignal.timeout(10_000) })
  if (!response.ok) throw new Error(`${path} 返回 HTTP ${response.status}`)
  return response.json() as Promise<T>
}

export async function loadAppData(): Promise<AppData> {
  try {
    const [dashboard, alertPayload, backtests, intraday] = await Promise.all([
      fetchJson<Dashboard>('./data/dashboard.json'),
      fetchJson<{ alerts: AlertRecord[] }>('./data/alerts.json'),
      fetchJson<Backtests>('./data/backtests.json'),
      fetchJson<IntradaySnapshot>('./data/intraday.json'),
    ])
    const data: AppData = {
      dashboard,
      alerts: alertPayload.alerts,
      backtests,
      intraday,
      cached: false,
    }
    localStorage.setItem(CACHE_KEY, JSON.stringify(data))
    return data
  } catch (error) {
    const cached = readCachedAppData()
    if (cached) return cached
    throw error
  }
}
