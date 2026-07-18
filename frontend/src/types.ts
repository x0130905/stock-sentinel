export type Criterion = {
  key: string
  label: string
  triggered: boolean
  score: number
  max_score: number
  detail: string
}

export type PricePoint = {
  date: string
  open: number | null
  high: number | null
  low: number | null
  close: number | null
  volume: number | null
  sma_5: number | null
  sma_20: number | null
  sma_60: number | null
  macd: number | null
  macd_signal: number | null
  macd_hist: number | null
  rsi_14: number | null
  bollinger_upper: number | null
  bollinger_middle: number | null
  bollinger_lower: number | null
}

export type StockAnalysis = {
  symbol: string
  name: string
  market: string
  price: number
  previous_close: number
  change_percent: number
  updated_at: string
  provider: string
  delayed: boolean
  delay_minutes: number | null
  delay_note: string
  mode: string
  buy_score: number
  sell_score: number
  signal_label: string
  risk_level: '低' | '中' | '高'
  confidence: string
  human_confirmation_required: boolean
  support: number
  resistance: number
  attention_range: [number, number]
  stop_loss_reference: number
  metrics: Record<string, number | null>
  buy_criteria: Criterion[]
  sell_criteria: Criterion[]
  position: Record<string, number>
  price_history: PricePoint[]
}

export type Dashboard = {
  schema_version: number
  generated_at: string
  generated_at_local: string
  provider: string
  mode: string
  provider_status: string
  schedule_note: string
  summary: {
    monitored_count: number
    successful_count: number
    today_signal_count: number
    high_risk_count: number
    latest_run: string
    new_signal_count: number
  }
  stocks: StockAnalysis[]
  errors: { symbol: string; message: string; count: string }[]
  disclaimer: string
}

export type AlertRecord = {
  id: string
  symbol: string
  name: string
  alert_type: string
  label: string
  reason: string
  price: number
  score: number | null
  created_at: string
  sent: boolean
  simulated: boolean
}

export type BacktestResult = {
  status: string
  symbol: string
  start_date: string
  end_date: string
  assumptions: Record<string, string | number | boolean>
  metrics: Record<string, number | null>
  trades: unknown[]
  equity_curve: { date: string; equity: number }[]
  disclaimer: string
}

export type Backtests = {
  generated_at: string
  results: Record<string, BacktestResult>
  disclaimer: string
}

export type AppData = {
  dashboard: Dashboard
  alerts: AlertRecord[]
  backtests: Backtests
  cached: boolean
}
