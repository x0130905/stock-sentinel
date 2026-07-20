import { Badge, EmptyState, SectionTitle } from '../components/Common'
import type { AlertRecord, IntradaySnapshot, StockAnalysis } from '../types'
import { formatPercent, formatTime } from '../utils'

type AlertsProps = {
  alerts: AlertRecord[]
  stocks: StockAnalysis[]
  intraday: IntradaySnapshot
  unreadCount: number
  onMarkAllRead: () => void
}

export function Alerts({ alerts, stocks, intraday, unreadCount, onMarkAllRead }: AlertsProps) {
  const lookup = new Map(stocks.map((stock) => [stock.symbol, stock]))
  const intradayLookup = new Map(intraday.quotes.map((quote) => [quote.symbol, quote]))
  return <div className="page-stack">
    <SectionTitle eyebrow="HISTORY" title="历史提醒" action={<div className="alerts-actions"><Badge>{unreadCount > 0 ? `${unreadCount} 条未读` : '全部已读'}</Badge><button className="text-button" onClick={onMarkAllRead}>全部标为已读</button></div>} />
    {!alerts.length ? <EmptyState title="暂无提醒" text="评分首次越过阈值，或止盈、止损、异常涨跌触发后，会显示在这里。" /> : <div className="timeline panel">{alerts.map((alert) => {
      const stock = lookup.get(alert.symbol)
      const current = intradayLookup.get(alert.symbol)?.price ?? stock?.price
      const currency = stock?.market === 'CN' ? '¥' : '$'
      const followUp = current ? (current / alert.price - 1) * 100 : null
      return <article className="timeline-item" key={alert.id}><div className={`timeline-dot ${alert.alert_type}`} /><div className="timeline-time">{formatTime(alert.created_at)}</div><div className="timeline-body"><div><h3>{alert.label}</h3><span>{alert.name} · {alert.symbol}</span></div><div className="alert-tags"><Badge tone={alert.simulated ? 'warning' : 'success'}>{alert.simulated ? '模拟信号' : '已启用提醒'}</Badge>{alert.sent && <Badge tone="success">邮件已发</Badge>}</div><p>{alert.reason}</p><div className="alert-values"><span>当时价格 <b>{currency}{alert.price.toFixed(3)}</b></span><span>评分 <b>{alert.score ?? '—'}</b></span><span>后续变化 <b className={followUp !== null && followUp >= 0 ? 'positive' : 'negative'}>{followUp === null ? '—' : formatPercent(followUp)}</b></span></div></div></article>
    })}</div>}
  </div>
}
