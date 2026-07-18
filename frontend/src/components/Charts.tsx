import type { BacktestResult, PricePoint } from '../types'

const WIDTH = 900

function numeric(values: (number | null)[]): number[] {
  return values.filter((value): value is number => value !== null && Number.isFinite(value))
}

function linePath<T>(
  data: T[],
  getter: (item: T) => number | null,
  x: (index: number) => number,
  y: (value: number) => number,
): string {
  let started = false
  return data.reduce((path, item, index) => {
    const value = getter(item)
    if (value === null || !Number.isFinite(value)) return path
    const command = started ? 'L' : 'M'
    started = true
    return `${path}${command}${x(index).toFixed(1)},${y(value).toFixed(1)} `
  }, '')
}

export function PriceChart({ points }: { points: PricePoint[] }) {
  const data = points.slice(-64).filter((point) => point.close !== null)
  if (!data.length) return <div className="chart-empty">暂无图表数据</div>
  const priceValues = numeric(data.flatMap((point) => [point.low, point.high, point.bollinger_lower, point.bollinger_upper]))
  const min = Math.min(...priceValues)
  const max = Math.max(...priceValues)
  const range = max - min || 1
  const chartTop = 24
  const chartBottom = 350
  const x = (index: number) => 52 + (index / Math.max(data.length - 1, 1)) * (WIDTH - 86)
  const y = (value: number) => chartTop + ((max - value) / range) * (chartBottom - chartTop)
  const candleWidth = Math.max(2, Math.min(8, (WIDTH - 100) / data.length - 2))
  const volumeMax = Math.max(...numeric(data.map((point) => point.volume)), 1)

  return (
    <div className="chart-shell">
      <div className="chart-legend"><span className="legend-candle">K 线</span><span className="legend-sma5">SMA5</span><span className="legend-sma20">SMA20</span><span className="legend-boll">布林带</span></div>
      <svg viewBox={`0 0 ${WIDTH} 470`} role="img" aria-label="K 线、成交量、均线与布林带图">
        {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
          const value = max - range * ratio
          const yy = y(value)
          return <g key={ratio}><line x1="48" x2={WIDTH - 24} y1={yy} y2={yy} className="grid-line" /><text x="2" y={yy + 4} className="axis-label">{value.toFixed(1)}</text></g>
        })}
        <path d={linePath(data, (point) => point.bollinger_upper, x, y)} className="line boll" />
        <path d={linePath(data, (point) => point.bollinger_lower, x, y)} className="line boll" />
        {data.map((point, index) => {
          if ([point.open, point.high, point.low, point.close].some((value) => value === null)) return null
          const open = point.open as number
          const close = point.close as number
          const high = point.high as number
          const low = point.low as number
          const up = close >= open
          const top = y(Math.max(open, close))
          const height = Math.max(1.5, Math.abs(y(open) - y(close)))
          return <g key={point.date} className={up ? 'candle up' : 'candle down'}><line x1={x(index)} x2={x(index)} y1={y(high)} y2={y(low)} /><rect x={x(index) - candleWidth / 2} y={top} width={candleWidth} height={height} /></g>
        })}
        <path d={linePath(data, (point) => point.sma_5, x, y)} className="line sma5" />
        <path d={linePath(data, (point) => point.sma_20, x, y)} className="line sma20" />
        {data.map((point, index) => {
          const volume = point.volume || 0
          const height = (volume / volumeMax) * 66
          return <rect key={`v-${point.date}`} x={x(index) - candleWidth / 2} y={445 - height} width={candleWidth} height={height} className={(point.close || 0) >= (point.open || 0) ? 'volume up' : 'volume down'} />
        })}
        <text x="4" y="414" className="axis-label">成交量</text>
        <text x="52" y="465" className="axis-label">{data[0]?.date.slice(5)}</text>
        <text x={WIDTH - 78} y="465" className="axis-label">{data[data.length - 1]?.date.slice(5)}</text>
      </svg>
    </div>
  )
}

export function IndicatorChart({ points, kind }: { points: PricePoint[]; kind: 'macd' | 'rsi' }) {
  const data = points.slice(-64)
  const height = 180
  const x = (index: number) => 42 + (index / Math.max(data.length - 1, 1)) * (WIDTH - 66)
  const values = kind === 'macd'
    ? numeric(data.flatMap((point) => [point.macd, point.macd_signal, point.macd_hist]))
    : [0, 30, 50, 70, 100]
  const min = kind === 'rsi' ? 0 : Math.min(...values, -1)
  const max = kind === 'rsi' ? 100 : Math.max(...values, 1)
  const y = (value: number) => 14 + ((max - value) / (max - min || 1)) * (height - 34)
  return (
    <div className="mini-chart">
      <div className="chart-legend"><strong>{kind === 'macd' ? 'MACD' : 'RSI 14'}</strong>{kind === 'macd' ? <><span className="legend-sma5">MACD</span><span className="legend-sma20">信号线</span></> : <span>30 / 70 阈值参考</span>}</div>
      <svg viewBox={`0 0 ${WIDTH} ${height}`} role="img" aria-label={kind === 'macd' ? 'MACD 图' : 'RSI 图'}>
        {(kind === 'rsi' ? [30, 50, 70] : [0]).map((value) => <line key={value} x1="42" x2={WIDTH - 20} y1={y(value)} y2={y(value)} className="grid-line" />)}
        {kind === 'macd' && data.map((point, index) => {
          const value = point.macd_hist || 0
          const yy = y(Math.max(value, 0))
          return <rect key={point.date} x={x(index) - 3} y={yy} width="5" height={Math.max(1, Math.abs(y(value) - y(0)))} className={value >= 0 ? 'hist up' : 'hist down'} />
        })}
        <path d={linePath(data, (point) => kind === 'macd' ? point.macd : point.rsi_14, x, y)} className="line sma5" />
        {kind === 'macd' && <path d={linePath(data, (point) => point.macd_signal, x, y)} className="line sma20" />}
      </svg>
    </div>
  )
}

export function EquityChart({ result }: { result?: BacktestResult }) {
  const data = result?.equity_curve || []
  if (!data.length) return <div className="chart-empty">暂无回测资金曲线</div>
  const values = data.map((point) => point.equity)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const x = (index: number) => 28 + (index / Math.max(data.length - 1, 1)) * (WIDTH - 50)
  const y = (value: number) => 20 + ((max - value) / (max - min || 1)) * 180
  return <div className="equity-chart"><svg viewBox={`0 0 ${WIDTH} 225`} role="img" aria-label="历史回测资金曲线"><defs><linearGradient id="equity-fill" x1="0" y1="0" x2="0" y2="1"><stop stopColor="#36d6b7" stopOpacity=".35" /><stop offset="1" stopColor="#36d6b7" stopOpacity="0" /></linearGradient></defs><path d={`${linePath(data, (point) => point.equity, x, y)}L${x(data.length - 1)},215 L${x(0)},215 Z`} fill="url(#equity-fill)" /><path d={linePath(data, (point) => point.equity, x, y)} className="line equity" /></svg></div>
}
