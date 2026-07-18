import { useCallback, useEffect, useState } from 'react'
import { loadAppData } from './api'
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

const navigation: { id: Tab; label: string; icon: string }[] = [
  { id: 'overview', label: '总览', icon: '⌂' },
  { id: 'watchlist', label: '自选', icon: '◇' },
  { id: 'detail', label: '分析', icon: '⌁' },
  { id: 'alerts', label: '提醒', icon: '◴' },
  { id: 'simulator', label: '模拟', icon: '◎' },
  { id: 'settings', label: '设置', icon: '⚙' },
]

export default function App() {
  const [data, setData] = useState<AppData | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<Tab>('overview')
  const [selectedSymbol, setSelectedSymbol] = useState('')
  const [online, setOnline] = useState(navigator.onLine)
  const [installPrompt, setInstallPrompt] = useState<Event | null>(null)

  const refresh = useCallback(() => {
    setLoading(true); setError('')
    loadAppData().then((result) => { setData(result); setSelectedSymbol((current) => current || result.dashboard.stocks[0]?.symbol || '') }).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : '无法读取分析数据')).finally(() => setLoading(false))
  }, [])

  useEffect(() => { refresh() }, [refresh])
  useEffect(() => {
    const onOnline = () => setOnline(true)
    const onOffline = () => setOnline(false)
    const onInstall = (event: Event) => { event.preventDefault(); setInstallPrompt(event) }
    window.addEventListener('online', onOnline); window.addEventListener('offline', onOffline); window.addEventListener('beforeinstallprompt', onInstall)
    if ('serviceWorker' in navigator && import.meta.env.PROD) navigator.serviceWorker.register('./service-worker.js').catch(() => undefined)
    return () => { window.removeEventListener('online', onOnline); window.removeEventListener('offline', onOffline); window.removeEventListener('beforeinstallprompt', onInstall) }
  }, [])

  const selectStock = (stock: StockAnalysis) => { setSelectedSymbol(stock.symbol); setTab('detail'); window.scrollTo({ top: 0, behavior: 'smooth' }) }
  const install = async () => {
    if (!installPrompt) return
    const promptEvent = installPrompt as Event & { prompt: () => Promise<void> }
    await promptEvent.prompt(); setInstallPrompt(null)
  }

  if (loading && !data) return <div className="app-state"><div className="loader"><span /><span /><span /></div><h1>Stock Sentinel</h1><p>正在载入分析结果…</p></div>
  if (error && !data) return <div className="app-state error-state"><div>!</div><h1>暂时无法载入数据</h1><p>{error}</p><button className="primary-button compact" onClick={refresh}>重新加载</button><small>首次使用请先在项目根目录运行 <code>python -m stock_sentinel demo</code></small></div>
  if (!data) return null
  const selected = data.dashboard.stocks.find((stock) => stock.symbol === selectedSymbol)

  return <div className="app-shell">
    <header className="topbar"><button className="brand" onClick={() => setTab('overview')}><span className="brand-mark"><i /><i /><i /></span><span><strong>Stock Sentinel</strong><small>股票行情监测</small></span></button><nav className="desktop-nav">{navigation.map((item) => <button key={item.id} className={tab === item.id ? 'active' : ''} onClick={() => setTab(item.id)}><span>{item.icon}</span>{item.label}{item.id === 'alerts' && data.dashboard.summary.today_signal_count > 0 && <i>{data.dashboard.summary.today_signal_count}</i>}</button>)}</nav><div className="top-actions"><Badge tone={online ? 'success' : 'warning'}>{online ? '在线' : '离线缓存'}</Badge>{installPrompt && <button className="install-button" onClick={install}>安装到手机</button>}<button className="refresh-button" onClick={refresh} aria-label="刷新数据">↻</button></div></header>
    <main className="main-content">
      {(data.cached || !online) && <div className="offline-banner">当前显示离线缓存，最后生成于 {formatTime(data.dashboard.generated_at)}。</div>}
      {error && <div className="offline-banner warning">刷新失败，继续显示上次数据：{error}</div>}
      {tab === 'overview' && <Overview dashboard={data.dashboard} onSelect={selectStock} />}
      {tab === 'watchlist' && <Watchlist stocks={data.dashboard.stocks} onSelect={selectStock} />}
      {tab === 'detail' && <Detail stock={selected} />}
      {tab === 'alerts' && <Alerts alerts={data.alerts} stocks={data.dashboard.stocks} />}
      {tab === 'simulator' && <Simulator stocks={data.dashboard.stocks} backtests={data.backtests} />}
      {tab === 'settings' && <Settings dashboard={data.dashboard} />}
    </main>
    <footer className="app-footer"><strong>风险声明</strong><p>{data.dashboard.disclaimer} 本系统不连接银行卡或证券账户，也不会自动下单。</p><span>最后更新：{formatTime(data.dashboard.generated_at)} · {data.dashboard.mode === 'sample' ? '演示模式' : data.dashboard.provider}</span></footer>
    <nav className="mobile-nav">{navigation.map((item) => <button key={item.id} className={tab === item.id ? 'active' : ''} onClick={() => { setTab(item.id); window.scrollTo({ top: 0 }) }}><span>{item.icon}</span>{item.label}{item.id === 'alerts' && data.dashboard.summary.today_signal_count > 0 && <i>{data.dashboard.summary.today_signal_count}</i>}</button>)}</nav>
  </div>
}
