import { Change, Badge, ScoreGauge, SectionTitle, StatCard } from '../components/Common'
import type { Dashboard, StockAnalysis } from '../types'
import { formatTime } from '../utils'

export function Overview({ dashboard, onSelect }: { dashboard: Dashboard; onSelect: (stock: StockAnalysis) => void }) {
  const lead = dashboard.stocks[0]
  return (
    <div className="page-stack">
      <section className="hero-panel">
        <div className="hero-copy">
          <div className="eyebrow"><span className="live-dot" /> 市场监测台</div>
          <h1>用清晰的规则，<br /><span>看懂每一次信号。</span></h1>
          <p>多指标评分、历史回测与风险约束集中在一个手机端界面。每条结论都能追溯到触发依据。</p>
          <div className="hero-tags"><Badge tone={dashboard.mode === 'sample' ? 'warning' : 'success'}>{dashboard.mode === 'sample' ? '演示数据' : '真实数据源'}</Badge><Badge>{dashboard.provider}</Badge><Badge tone="warning">行情可能延迟</Badge></div>
        </div>
        {lead && <button className="lead-quote" onClick={() => onSelect(lead)}>
          <div><span>{lead.symbol}</span><small>{lead.name}</small></div>
          <strong>${lead.price.toFixed(2)}</strong>
          <Change value={lead.change_percent} />
          <div className="mini-score"><span>买 {lead.buy_score}</span><span>卖 {lead.sell_score}</span></div>
        </button>}
      </section>

      <section className="stats-grid">
        <StatCard label="监测股票" value={dashboard.summary.monitored_count} hint={`成功分析 ${dashboard.summary.successful_count} 只`} accent="#5ca8ff" />
        <StatCard label="今日信号" value={dashboard.summary.today_signal_count} hint={`本轮新增 ${dashboard.summary.new_signal_count} 条`} accent="#36d6b7" />
        <StatCard label="高风险" value={dashboard.summary.high_risk_count} hint="需要优先人工核对" accent="#ff7085" />
        <StatCard label="数据源" value={dashboard.provider_status} hint={`更新于 ${formatTime(dashboard.generated_at)}`} accent="#ffcc66" />
      </section>

      <section className="panel">
        <SectionTitle eyebrow="WATCHLIST" title="重点观察" action={<span className="muted">点击查看完整依据</span>} />
        <div className="spotlight-grid">
          {dashboard.stocks.map((stock) => <button className="spotlight-card" key={stock.symbol} onClick={() => onSelect(stock)}>
            <div className="stock-title"><div className="symbol-mark">{stock.symbol.slice(0, 2)}</div><div><strong>{stock.symbol}</strong><span>{stock.name}</span></div><Badge tone={stock.risk_level === '高' ? 'danger' : stock.risk_level === '中' ? 'warning' : 'success'}>{stock.risk_level}风险</Badge></div>
            <div className="quote-line"><strong>${stock.price.toFixed(2)}</strong><Change value={stock.change_percent} /></div>
            <div className="dual-score"><ScoreGauge score={stock.buy_score} label="买入评分" tone="buy" /><ScoreGauge score={stock.sell_score} label="卖出评分" tone="sell" /></div>
            <div className="card-footer"><span>{stock.signal_label}</span><span>可信度 {stock.confidence} →</span></div>
          </button>)}
        </div>
      </section>

      <section className="notice-strip"><div>i</div><p><strong>真实频率说明</strong>{dashboard.schedule_note}</p></section>
    </div>
  )
}
