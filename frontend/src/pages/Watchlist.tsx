import { Badge, Change, EmptyState, ScoreGauge, SectionTitle } from '../components/Common'
import type { StockAnalysis } from '../types'
import { formatTime } from '../utils'

export function Watchlist({ stocks, onSelect }: { stocks: StockAnalysis[]; onSelect: (stock: StockAnalysis) => void }) {
  return <div className="page-stack"><SectionTitle eyebrow="WATCHLIST" title="自选股" action={<Badge>{stocks.length} 只</Badge>} />
    {!stocks.length ? <EmptyState title="还没有自选股" text="在设置页添加股票并导出后台配置。" /> : <div className="watch-table panel">
      <div className="watch-head"><span>股票</span><span>价格 / 涨跌</span><span>买入评分</span><span>卖出评分</span><span>状态</span></div>
      {stocks.map((stock) => <button className="watch-row" key={stock.symbol} onClick={() => onSelect(stock)}>
        <span className="stock-title"><span className="symbol-mark">{stock.symbol.slice(0, 2)}</span><span><strong>{stock.symbol}</strong><small>{stock.name} · {stock.market}</small></span></span>
        <span className="watch-price"><strong>${stock.price.toFixed(2)}</strong><Change value={stock.change_percent} /></span>
        <ScoreGauge score={stock.buy_score} label="买" tone="buy" />
        <ScoreGauge score={stock.sell_score} label="卖" tone="sell" />
        <span className="watch-status"><Badge tone={stock.risk_level === '高' ? 'danger' : stock.risk_level === '中' ? 'warning' : 'success'}>{stock.signal_label}</Badge><small>{formatTime(stock.updated_at)} · 查看 →</small></span>
      </button>)}
    </div>}
  </div>
}
