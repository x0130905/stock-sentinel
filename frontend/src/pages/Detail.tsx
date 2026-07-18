import { Badge, Change, EmptyState, ScoreGauge, SectionTitle } from '../components/Common'
import { IndicatorChart, PriceChart } from '../components/Charts'
import type { Criterion, StockAnalysis } from '../types'

function CriteriaList({ title, score, criteria, tone }: { title: string; score: number; criteria: Criterion[]; tone: 'buy' | 'sell' }) {
  return <div className={`criteria-card ${tone}`}><div className="criteria-head"><div><span>{title}</span><strong>{score}/100</strong></div><div className="meter"><i style={{ width: `${score}%` }} /></div></div><div className="criteria-list">{criteria.map((item) => <div className={item.triggered ? 'criterion hit' : 'criterion'} key={item.key}><span>{item.triggered ? '✓' : '–'}</span><div><strong>{item.label}</strong><small>{item.detail}</small></div><b>{item.score}/{item.max_score}</b></div>)}</div></div>
}

export function Detail({ stock }: { stock?: StockAnalysis }) {
  if (!stock) return <EmptyState title="请选择一只股票" text="从总览或自选股列表进入详情。" />
  return <div className="page-stack">
    <section className="detail-hero panel"><div><div className="stock-title"><div className="symbol-mark large">{stock.symbol.slice(0, 2)}</div><div><h2>{stock.symbol} <span>{stock.name}</span></h2><p>{stock.market} 市场 · {stock.provider}</p></div></div><div className="detail-price"><strong>${stock.price.toFixed(2)}</strong><Change value={stock.change_percent} /></div></div><div className="detail-scores"><ScoreGauge score={stock.buy_score} label="买入评分" tone="buy" /><ScoreGauge score={stock.sell_score} label="卖出评分" tone="sell" /><div className="signal-summary"><Badge tone={stock.risk_level === '高' ? 'danger' : stock.risk_level === '中' ? 'warning' : 'success'}>{stock.signal_label}</Badge><p>风险 {stock.risk_level} · 可信度 {stock.confidence}</p><small>所有结论均需人工确认</small></div></div></section>
    <section className="level-grid"><div><span>支撑位</span><strong>${stock.support.toFixed(2)}</strong></div><div><span>关注区间</span><strong>${stock.attention_range[0].toFixed(2)} – ${stock.attention_range[1].toFixed(2)}</strong></div><div><span>压力位</span><strong>${stock.resistance.toFixed(2)}</strong></div><div><span>止损参考</span><strong>${stock.stop_loss_reference.toFixed(2)}</strong></div></section>
    <section className="panel"><SectionTitle eyebrow="PRICE ACTION" title="价格与技术指标" action={<Badge tone="warning">{stock.delayed ? '可能延迟' : '数据源标记实时'}</Badge>} /><PriceChart points={stock.price_history} /><div className="indicator-grid"><IndicatorChart points={stock.price_history} kind="macd" /><IndicatorChart points={stock.price_history} kind="rsi" /></div></section>
    <section><SectionTitle eyebrow="SCORE EXPLAINER" title="评分依据" /><div className="criteria-grid"><CriteriaList title="买入条件" score={stock.buy_score} criteria={stock.buy_criteria} tone="buy" /><CriteriaList title="卖出条件" score={stock.sell_score} criteria={stock.sell_criteria} tone="sell" /></div></section>
    <section className="metric-panel panel"><SectionTitle eyebrow="METRICS" title="关键指标快照" /><div className="metrics-grid">{Object.entries(stock.metrics).map(([key, value]) => <div key={key}><span>{key.replaceAll('_', ' ').toUpperCase()}</span><strong>{value ?? '—'}</strong></div>)}</div></section>
    <section className="delay-box"><strong>数据新鲜度说明</strong><p>{stock.delay_note}</p></section>
  </div>
}
