import { useCallback, useEffect, useMemo, useState } from 'react'
import { loadAppData, readCachedAppData } from './api'
import { Badge } from './components/Common'
import { Alerts } from './pages/Alerts'
import { Detail } from './pages/Detail'
import { Overview } from './pages/Overview'
import { Settings } from './pages/Settings'
import { Simulator } from './pages/Simulator'
import { Watchlist } from './pages/Watchlist'
import type { AppData, StockAnalysis } from './types'
import { formatTime } from './utils'

type Tab = 'overview' | 'watchlist' | 'detail' | 'alerts' | 'simulator' | 'settings'
type RefreshState = 'idle' | 'loading' | 'success' | 'error'

const navigation: { id: Tab; label: string; icon: string }[] = [
  { id: 'overview', label: '总览', icon: '⌂' },
  { id: 'watchlist', label: '自选', icon: '◎' },
  { id: 'detail', label: '分析', icon: '⌁' },
  { id: 'alerts', label: '提醒', icon: '●' },
  { id: 'simulator', label: '模拟', icon: '◇' },
  { id: 'settings', label: '设置', icon: '⚙' },
]

const ALERTS_READ_KEY = 'stock-sentinel-alerts-read-at-v1'

export default function App() {
  const initialCache = useMemo(() => readCachedAppData(), [])
  const [data, setData] = useState<AppData | null>(initialCache)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(!initialCache)
  const [refreshState, setRefreshState] = useState<RefreshState>('idle')
  const [refreshMessage, setRefreshMessage] = useState('')
  const [tab, setTab] = useState<Tab>('overview')
  const [selectedSymbol, setSelectedSymbol] = useState('')
  const [online, setOnline] = useState(navigator.onLine)
  const [installPrompt, setInstallPrompt] = useState<Event | null>(null)
  const [alertsReadAt, setAlertsReadAt] = useState(() => Number(localStorage.getItem(ALERTS_READ_KEY) || 0))

  const refresh = useCallback((showFeedback = true) => {
    setLoading(true)
    setError('')
    if (showFeedback) {
      setRefreshState('loading')
      setRefreshMessage('正在刷新最新数据…')
    }
    loadAppData()
      .then((result) => {
        setData(result)
        setSelectedSymbol((current) => current || result.dashboard.stocks[0]?.symbol || '')
        if (showFeedback) {
          setRefreshState('success')
          setRefreshMessage(result.cached ? '网络较慢，已显示本地缓存' : '刷新成功，已获取最新数据')
        }
      })
      .catch((reason: unknown) => {
        const message = reason instanceof Error ? reason.message : '无法读取分析数据'
        setError(message)
        if (showFeedback) {
          setRefreshState('error')
          setRefreshMessage('刷新失败，继续显示原有数据')
        }
      })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { refresh(false) }, [refresh])
  useEffect(() => {
    if (refreshState === 'idle' || refreshState === 'loading') return
    const timer = window.setTimeout(() => { setRefreshState('idle'); setRefreshMessage('') }, 2600)
    return () => window.clearTimeout(timer)
  }, [refreshState])
  useEffect(() => {
    const onOnline = () => setOnline(true)
    const onOffline = () => setOnline(false)
    const onInstall = (event: Event) => { event.preventDefault(); setInstallPrompt(event) }
    window.addEventListener('online', onOnline)
    window.addEventListener('offline', onOffline)
    window.addEventListener('beforeinstallprompt', onInstall)
    if ('serviceWorker' in navigator && import.meta.env.PROD) navigator.serviceWorker.register('./service-worker.js').catch(() => undefined)
    return () => {
      window.removeEventListener('online', onOnline)
      window.removeEventListener('offline', onOffline)
      window.removeEventListener('beforeinstallprompt', onInstall)
    }
  }, [])

  const markAlertsRead = useCallback(() => {
    const latestAlert = Math.max(0, ...((data?.alerts ?? []).map((alert) => Date.parse(alert.created_at)).filter(Number.isFinite)))
    const readAt = Math.max(Date.now(), latestAlert)
    localStorage.setItem(ALERTS_READ_KEY, String(readAt))
    setAlertsReadAt(readAt)
  }, [data?.alerts])

  const openTab = (nextTab: Tab) => {
    setTab(nextTab)
    if (nextTab === 'alerts') markAlertsRead()
  }
  const selectStock = (stock: StockAnalysis) => {
    setSelectedSymbol(stock.symbol); setTab('detail'); window.scrollTo({ top: 0, behavior: 'smooth' })
  }
  const install = async () => {
    if (!installPrompt) return
    await (installPrompt as Event & { prompt: () => Promise<void> }).prompt()
    setInstallPrompt(null)
  }

  if (loading && !data) return <div className="app-state"><div className="loader"><span /><span /><span /></div><h1>Stock Sentinel</h1><p>正在载入分析结果…</p></div>
  if (error && !data) return <div className="app-state error-state"><div>!</div><h1>暂时无法载入数据</h1><p>{error}</p><button className="primary-button compact" onClick={() => refresh(true)}>重新加载</button></div>
  if (!data) return null

  const selected = data.dashboard.stocks.find((stock) => stock.symbol === selectedSymbol)
  const today = new Date().toDateString()
  const unreadAlerts = data.alerts.filter((alert) => {
    const created = Date.parse(alert.created_at)
    return Number.isFinite(created) && created > alertsReadAt && new Date(created).toDateString() === today
  }).length

  const navButtons = (mobile = false) => navigation.map((item) => <button key={item.id} className={tab === item.id ? 'active' : ''} onClick={() => { openTab(item.id); if (mobile) window.scrollTo({ top: 0 }) }}><span>{item.icon}</span>{item.label}{item.id === 'alerts' && unreadAlerts > 0 && <i>{unreadAlerts}</i>}</button>)

  return <div className="app-shell">
    <header className="topbar">
      <button className="brand" onClick={() => openTab('overview')}><span className="brand-mark"><i /><i /><i /></span><span><strong>Stock Sentinel</strong><small>股票行情监测</small></span></button>
      <nav className="desktop-nav">{navButtons()}</nav>
      <div className="top-actions"><Badge tone={online ? 'success' : 'warning'}>{online ? '在线' : '离线缓存'}</Badge>{installPrompt && <button className="install-button" onClick={install}>安装到手机</button>}<button className={`refresh-button ${loading ? 'is-loading' : ''}`} onClick={() => refresh(true)} disabled={loading} aria-label={loading ? '正在刷新数据' : '刷新数据'} title={loading ? '正在刷新…' : '刷新最新数据'}>↻</button></div>
    </header>
    <main className="main-content">
      {refreshMessage && <div className={`refresh-toast ${refreshState}`} role="status" aria-live="polite">{refreshState === 'loading' && <span />}{refreshMessage}</div>}
      {(data.cached || !online) && <div className="offline-banner">当前先显示本地缓存，最后生成于 {formatTime(data.dashboard.generated_at)}；后台正在检查更新。</div>}
      {error && <div className="offline-banner warning">刷新失败，继续显示上次数据：{error}</div>}
      {tab === 'overview' && <Overview dashboard={data.dashboard} intraday={data.intraday} onSelect={selectStock} />}
      {tab === 'watchlist' && <Watchlist stocks={data.dashboard.stocks} onSelect={selectStock} />}
      {tab === 'detail' && <Detail stock={selected} />}
      {tab === 'alerts' && <Alerts alerts={data.alerts} stocks={data.dashboard.stocks} intraday={data.intraday} unreadCount={unreadAlerts} onMarkAllRead={markAlertsRead} />}
      {tab === 'simulator' && <Simulator stocks={data.dashboard.stocks} backtests={data.backtests} />}
      {tab === 'settings' && <Settings dashboard={data.dashboard} />}
    </main>
    <footer className="app-footer"><strong>风险声明</strong><p>{data.dashboard.disclaimer} 本系统不连接银行卡或证券账户，也不会自动下单。</p><span>最后更新：{formatTime(data.dashboard.generated_at)} · {data.dashboard.mode === 'sample' ? '演示模式' : data.dashboard.provider}</span></footer>
    <nav className="mobile-nav">{navButtons(true)}</nav>
  </div>
}
