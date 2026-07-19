import { Change, Badge, ScoreGauge, SectionTitle, StatCard } from '../components/Common'
import type { Dashboard, IntradaySnapshot, StockAnalysis } from '../types'
import { formatTime } from '../utils'

export function Overview({ dashboard, intraday, onSelect }: { dashboard: Dashboard; intraday: IntradaySnapshot; onSelect: (stock: StockAnalysis) => void }) {
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

      <section className="panel intraday-panel">
        <SectionTitle
          eyebrow="INTRADAY RISK"
          title="15分钟盘中风险观察"
          action={<Badge tone={intraday.status === '正常' ? 'success' : 'warning'}>{intraday.status}</Badge>}
        />
        {intraday.quotes.length ? <div className="intraday-grid">
          {intraday.quotes.map((quote) => <article className="intraday-card" key={quote.symbol}>
            <div><strong>{quote.symbol}</strong><small>{quote.name}</small></div>
            <span><b>¥{quote.price.toFixed(3)}</b><Change value={quote.change_percent} /></span>
            <p>今高 ¥{quote.high.toFixed(3)} · 今低 ¥{quote.low.toFixed(3)}</p>
          </article>)}
        </div> : <p className="intraday-empty">等待交易时段首次检查；工作日 9:30–11:30、13:00–15:00 运行。</p>}
        <div className="intraday-foot">
          <span>最近检查：{intraday.generated_at ? formatTime(intraday.generated_at) : '尚未运行'}</span>
          <span>本轮新增风险：{intraday.new_risk_count}</span>
        </div>
        <p className="intraday-warning">实验性免费行情：{intraday.delay_note} 必须执行的止损请使用券商条件单。</p>
      </section>

      <section className="notice-strip"><div>i</div><p><strong>真实频率说明</strong>{dashboard.schedule_note}</p></section>
    </div>
  )
}
