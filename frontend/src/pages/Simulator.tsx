import { useMemo, useState } from 'react'
import { EquityChart } from '../components/Charts'
import { Badge, EmptyState, SectionTitle, StatCard } from '../components/Common'
import type { Backtests, StockAnalysis } from '../types'
import { formatMoney, formatPercent } from '../utils'

type Transaction = {
  id: string
  symbol: string
  type: 'buy' | 'sell'
  quantity: number
  price: number
  createdAt: string
}

type Position = { quantity: number; cost: number }

function restoreTransactions(): Transaction[] {
  try { return JSON.parse(localStorage.getItem('stock-sentinel-trades') || '[]') as Transaction[] } catch { return [] }
}

function calculatePortfolio(transactions: Transaction[], initialCash: number, stocks: StockAnalysis[]) {
  let cash = initialCash
  let realized = 0
  const positions = new Map<string, Position>()
  const lastPrices = new Map(stocks.map((stock) => [stock.symbol, stock.price]))
  const snapshots = [initialCash]
  for (const tx of transactions) {
    const position = positions.get(tx.symbol) || { quantity: 0, cost: 0 }
    lastPrices.set(tx.symbol, tx.price)
    if (tx.type === 'buy') {
      cash -= tx.quantity * tx.price
      position.quantity += tx.quantity
      position.cost += tx.quantity * tx.price
    } else if (position.quantity >= tx.quantity) {
      const averageCost = position.quantity ? position.cost / position.quantity : 0
      cash += tx.quantity * tx.price
      realized += (tx.price - averageCost) * tx.quantity
      position.quantity -= tx.quantity
      position.cost -= averageCost * tx.quantity
    }
    positions.set(tx.symbol, position)
    const equity = cash + [...positions].reduce((sum, [symbol, value]) => sum + value.quantity * (lastPrices.get(symbol) || 0), 0)
    snapshots.push(equity)
  }
  stocks.forEach((stock) => lastPrices.set(stock.symbol, stock.price))
  const marketValue = [...positions].reduce((sum, [symbol, value]) => sum + value.quantity * (lastPrices.get(symbol) || 0), 0)
  const remainingCost = [...positions.values()].reduce((sum, value) => sum + value.cost, 0)
  const equity = cash + marketValue
  snapshots.push(equity)
  let peak = snapshots[0]
  let maxDrawdown = 0
  snapshots.forEach((value) => { peak = Math.max(peak, value); maxDrawdown = Math.min(maxDrawdown, value / peak - 1) })
  return { cash, positions, marketValue, remainingCost, realized, unrealized: marketValue - remainingCost, equity, returnPercent: (equity / initialCash - 1) * 100, maxDrawdown: maxDrawdown * 100 }
}

export function Simulator({ stocks, backtests }: { stocks: StockAnalysis[]; backtests: Backtests }) {
  const [transactions, setTransactions] = useState<Transaction[]>(restoreTransactions)
  const [initialCash, setInitialCash] = useState(() => Number(localStorage.getItem('stock-sentinel-cash') || 100000))
  const [symbol, setSymbol] = useState(stocks[0]?.symbol || '')
  const [type, setType] = useState<'buy' | 'sell'>('buy')
  const selected = stocks.find((stock) => stock.symbol === symbol)
  const [quantity, setQuantity] = useState(1)
  const [price, setPrice] = useState(selected?.price || 0)
  const [message, setMessage] = useState('')
  const portfolio = useMemo(() => calculatePortfolio(transactions, initialCash, stocks), [transactions, initialCash, stocks])
  const activeBacktest = backtests.results[symbol]

  const changeCash = (value: number) => {
    const safe = Math.max(100, value || 100000)
    setInitialCash(safe)
    localStorage.setItem('stock-sentinel-cash', String(safe))
  }
  const changeSymbol = (value: string) => { setSymbol(value); setPrice(stocks.find((stock) => stock.symbol === value)?.price || 0) }
  const addTransaction = () => {
    setMessage('')
    if (!selected || quantity <= 0 || price <= 0) return setMessage('请输入有效的数量和价格。')
    if (type === 'buy' && quantity * price > portfolio.cash) return setMessage('模拟现金不足。')
    const holding = portfolio.positions.get(symbol)?.quantity || 0
    if (type === 'sell' && quantity > holding) return setMessage(`最多可模拟卖出 ${holding.toFixed(4)} 股。`)
    const next = [{ id: crypto.randomUUID(), symbol, type, quantity, price, createdAt: new Date().toISOString() }, ...transactions]
    setTransactions(next)
    localStorage.setItem('stock-sentinel-trades', JSON.stringify(next))
  }
  const clear = () => { if (window.confirm('确定清空本机的全部模拟交易记录？')) { setTransactions([]); localStorage.removeItem('stock-sentinel-trades') } }

  if (!stocks.length) return <EmptyState title="没有可模拟的股票" text="先运行一次监测生成行情数据。" />
  return <div className="page-stack">
    <SectionTitle eyebrow="PAPER TRADING" title="模拟交易" action={<Badge tone="warning">不连接证券账户</Badge>} />
    <section className="stats-grid simulator-stats"><StatCard label="模拟总资产" value={formatMoney(portfolio.equity)} hint={`现金 ${formatMoney(portfolio.cash)}`} accent="#5ca8ff" /><StatCard label="浮动盈亏" value={<span className={portfolio.unrealized >= 0 ? 'positive' : 'negative'}>{formatMoney(portfolio.unrealized)}</span>} hint={`已实现 ${formatMoney(portfolio.realized)}`} accent="#36d6b7" /><StatCard label="累计收益" value={<span className={portfolio.returnPercent >= 0 ? 'positive' : 'negative'}>{formatPercent(portfolio.returnPercent)}</span>} hint={`初始资金 ${formatMoney(initialCash)}`} accent="#ffcc66" /><StatCard label="模拟最大回撤" value={formatPercent(portfolio.maxDrawdown)} hint="按本机交易快照估算" accent="#ff7085" /></section>
    <div className="simulator-layout"><section className="panel trade-ticket"><SectionTitle title="新建模拟委托" /><label>初始模拟资金<input type="number" min="100" value={initialCash} onChange={(event) => changeCash(Number(event.target.value))} /></label><div className="segmented"><button className={type === 'buy' ? 'active buy' : ''} onClick={() => setType('buy')}>模拟买入</button><button className={type === 'sell' ? 'active sell' : ''} onClick={() => setType('sell')}>模拟卖出</button></div><label>股票<select value={symbol} onChange={(event) => changeSymbol(event.target.value)}>{stocks.map((stock) => <option key={stock.symbol} value={stock.symbol}>{stock.symbol} · {stock.name}</option>)}</select></label><div className="form-pair"><label>数量<input type="number" min="0.0001" step="0.1" value={quantity} onChange={(event) => setQuantity(Number(event.target.value))} /></label><label>模拟成交价<input type="number" min="0.01" step="0.01" value={price} onChange={(event) => setPrice(Number(event.target.value))} /></label></div><div className="ticket-summary"><span>预计金额</span><strong>{formatMoney(quantity * price)}</strong></div>{message && <p className="form-error">{message}</p>}<button className={`primary-button ${type}`} onClick={addTransaction}>确认{type === 'buy' ? '买入' : '卖出'}（仅模拟）</button><small className="muted">记录只保存在当前浏览器，清除浏览器数据后无法恢复。</small></section>
      <section className="panel positions"><SectionTitle title="模拟持仓" />{[...portfolio.positions].filter(([, value]) => value.quantity > 0).length === 0 ? <EmptyState title="暂无持仓" text="创建一笔模拟买入后会在这里计算成本与盈亏。" /> : [...portfolio.positions].filter(([, value]) => value.quantity > 0).map(([positionSymbol, value]) => { const live = stocks.find((stock) => stock.symbol === positionSymbol)?.price || 0; const avg = value.cost / value.quantity; const pnl = (live - avg) * value.quantity; return <div className="position-row" key={positionSymbol}><div><strong>{positionSymbol}</strong><span>{value.quantity.toFixed(4)} 股</span></div><div><span>成本</span><strong>${avg.toFixed(2)}</strong></div><div><span>市值</span><strong>{formatMoney(live * value.quantity)}</strong></div><div><span>盈亏</span><strong className={pnl >= 0 ? 'positive' : 'negative'}>{formatMoney(pnl)}</strong></div></div>})}</section>
    </div>
    <section className="panel"><SectionTitle eyebrow="BACKTEST" title={`${symbol} 历史回测`} action={<Badge tone={activeBacktest?.status === 'completed' ? 'success' : 'danger'}>{activeBacktest?.status === 'completed' ? '已完成' : '未完成'}</Badge>} />{activeBacktest?.status === 'completed' ? <><div className="backtest-metrics">{[['总收益', 'total_return_percent'], ['年化收益', 'annualized_return_percent'], ['最大回撤', 'max_drawdown_percent'], ['胜率', 'win_rate_percent'], ['盈亏比', 'profit_factor'], ['交易次数', 'trade_count'], ['买入持有', 'buy_hold_return_percent']].map(([label, key]) => <div key={key}><span>{label}</span><strong>{activeBacktest.metrics[key] ?? '—'}{key.includes('percent') ? '%' : ''}</strong></div>)}</div><EquityChart result={activeBacktest} /><p className="muted">{activeBacktest.assumptions.execution_rule as string}；手续费和滑点均已计入。</p></> : <EmptyState title="回测尚未完成" text="后台会先完成回测，再允许产生模拟提醒。" />}</section>
    <section className="panel"><SectionTitle title="模拟交易记录" action={transactions.length ? <button className="text-button danger" onClick={clear}>清空记录</button> : undefined} />{transactions.length ? <div className="transactions">{transactions.map((tx) => <div key={tx.id}><Badge tone={tx.type === 'buy' ? 'success' : 'danger'}>{tx.type === 'buy' ? '买入' : '卖出'}</Badge><strong>{tx.symbol}</strong><span>{tx.quantity} 股 × ${tx.price.toFixed(2)}</span><small>{new Date(tx.createdAt).toLocaleString('zh-CN')}</small></div>)}</div> : <EmptyState title="暂无交易" text="所有操作都是本地模拟，不会发往券商。" />}</section>
  </div>
}
