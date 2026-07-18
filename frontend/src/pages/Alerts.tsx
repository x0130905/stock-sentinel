import { Badge, EmptyState, SectionTitle } from '../components/Common'
import type { AlertRecord, StockAnalysis } from '../types'
import { formatPercent, formatTime } from '../utils'

export function Alerts({ alerts, stocks }: { alerts: AlertRecord[]; stocks: StockAnalysis[] }) {
  const lookup = new Map(stocks.map((stock) => [stock.symbol, stock]))
  return <div className="page-stack"><SectionTitle eyebrow="HISTORY" title="历史提醒" action={<Badge>{alerts.length} 条</Badge>} />
    {!alerts.length ? <EmptyState title="暂无提醒" text="评分首次越过阈值，或止盈、止损、异常涨跌触发后，会显示在这里。" /> : <div className="timeline panel">{alerts.map((alert) => {
      const current = lookup.get(alert.symbol)?.price
      const followUp = current ? (current / alert.price - 1) * 100 : null
      return <article className="timeline-item" key={alert.id}><div className={`timeline-dot ${alert.alert_type}`} /><div className="timeline-time">{formatTime(alert.created_at)}</div><div className="timeline-body"><div><h3>{alert.label}</h3><span>{alert.name} · {alert.symbol}</span></div><div className="alert-tags"><Badge tone={alert.simulated ? 'warning' : 'success'}>{alert.simulated ? '模拟信号' : '已启用提醒'}</Badge>{alert.sent && <Badge tone="success">邮件已发</Badge>}</div><p>{alert.reason}</p><div className="alert-values"><span>当时价格 <b>${alert.price.toFixed(2)}</b></span><span>评分 <b>{alert.score ?? '—'}</b></span><span>后续变化 <b className={followUp !== null && followUp >= 0 ? 'positive' : 'negative'}>{followUp === null ? '—' : formatPercent(followUp)}</b></span></div></div></article>
    })}</div>}
  </div>
}
