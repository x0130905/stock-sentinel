import { useState } from 'react'
import { Badge, SectionTitle } from '../components/Common'
import type { Dashboard } from '../types'

const CURRENT_SCHEMA_VERSION = 3

type EditableStock = {
  symbol: string
  name: string
  market: string
  cost_basis: number
  quantity: number
  target_return_percent: number
  max_loss_percent: number
  take_profit_price: number | null
  stop_loss_price: number | null
  email_enabled: boolean
  buy_alert_enabled: boolean
  sell_alert_enabled: boolean
  daily_summary_enabled: boolean
}

type LocalConfig = {
  schema_version: number
  provider: string
  history_period: string
  analysis_frequency_minutes: number
  timezone: string
  stocks: EditableStock[]
  scoring: {
    buy_alert_threshold: number
    sell_alert_threshold: number
    rsi_oversold: number
    rsi_overbought: number
    near_level_atr_multiple: number
    abnormal_daily_change_percent: number
    high_volatility_annualized: number
    high_drawdown_percent: number
  }
  alerts: {
    cooldown_hours: number
    score_confirmation_runs: number
    consecutive_failure_threshold: number
    simulation_mode: boolean
    live_alerts_enabled: boolean
    backtest_required: boolean
  }
  intraday: {
    enabled: boolean
    provider: string
    interval_minutes: number
    abnormal_drop_percent: number
    pullback_from_high_percent: number
    support_break_percent: number
    cooldown_minutes: number
  }
  backtest: {
    initial_cash: number
    fee_rate: number
    slippage_rate: number
    start_date: null
    end_date: null
  }
}

function defaultConfig(dashboard: Dashboard): LocalConfig {
  return {
    schema_version: CURRENT_SCHEMA_VERSION,
    provider: 'alpha_vantage',
    history_period: '6mo',
    analysis_frequency_minutes: 1440,
    timezone: 'Asia/Shanghai',
    stocks: dashboard.stocks.map((stock) => ({
      symbol: stock.symbol,
      name: stock.name,
      market: stock.market,
      cost_basis: stock.position.cost_basis || 0,
      quantity: stock.position.quantity || 0,
      target_return_percent: 10,
      max_loss_percent: 8,
      take_profit_price: null,
      stop_loss_price: null,
      email_enabled: false,
      buy_alert_enabled: true,
      sell_alert_enabled: true,
      daily_summary_enabled: true,
    })),
    scoring: {
      buy_alert_threshold: 70,
      sell_alert_threshold: 70,
      rsi_oversold: 30,
      rsi_overbought: 70,
      near_level_atr_multiple: 1,
      abnormal_daily_change_percent: 7,
      high_volatility_annualized: 0.45,
      high_drawdown_percent: 25,
    },
    alerts: {
      cooldown_hours: 24,
      score_confirmation_runs: 2,
      consecutive_failure_threshold: 3,
      simulation_mode: true,
      live_alerts_enabled: false,
      backtest_required: true,
    },
    intraday: {
      enabled: true,
      provider: 'akshare',
      interval_minutes: 15,
      abnormal_drop_percent: 3,
      pullback_from_high_percent: 2,
      support_break_percent: 0.5,
      cooldown_minutes: 60,
    },
    backtest: {
      initial_cash: 100000,
      fee_rate: 0.001,
      slippage_rate: 0.0005,
      start_date: null,
      end_date: null,
    },
  }
}

function restoreConfig(dashboard: Dashboard): LocalConfig {
  try {
    const parsed = JSON.parse(localStorage.getItem('stock-sentinel-settings') || '') as LocalConfig
    return parsed.schema_version === CURRENT_SCHEMA_VERSION ? parsed : defaultConfig(dashboard)
  } catch {
    return defaultConfig(dashboard)
  }
}

export function Settings({ dashboard }: { dashboard: Dashboard }) {
  const [config, setConfig] = useState<LocalConfig>(() => restoreConfig(dashboard))
  const [saved, setSaved] = useState(false)
  const [newStock, setNewStock] = useState({ symbol: '', name: '', market: 'CN' })

  const updateStock = (index: number, patch: Partial<EditableStock>) => {
    setConfig((current) => ({
      ...current,
      stocks: current.stocks.map((stock, itemIndex) =>
        itemIndex === index ? { ...stock, ...patch } : stock,
      ),
    }))
  }

  const save = () => {
    localStorage.setItem('stock-sentinel-settings', JSON.stringify(config))
    setSaved(true)
    window.setTimeout(() => setSaved(false), 1800)
  }

  const add = () => {
    const symbol = newStock.symbol.trim().toUpperCase()
    if (!symbol || config.stocks.some((stock) => stock.symbol === symbol)) return
    setConfig((current) => ({
      ...current,
      stocks: [
        ...current.stocks,
        {
          symbol,
          name: newStock.name.trim() || symbol,
          market: newStock.market,
          cost_basis: 0,
          quantity: 0,
          target_return_percent: 10,
          max_loss_percent: 8,
          take_profit_price: null,
          stop_loss_price: null,
          email_enabled: false,
          buy_alert_enabled: true,
          sell_alert_enabled: true,
          daily_summary_enabled: true,
        },
      ],
    }))
    setNewStock({ symbol: '', name: '', market: 'CN' })
  }

  const exportConfig = () => {
    const blob = new Blob([`${JSON.stringify(config, null, 2)}\n`], {
      type: 'application/json',
    })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = 'settings.json'
    link.click()
    URL.revokeObjectURL(link.href)
  }

  const importConfig = (file?: File) => {
    if (!file) return
    file
      .text()
      .then((text) => {
        const parsed = JSON.parse(text) as LocalConfig
        if (!Array.isArray(parsed.stocks)) throw new Error('缺少 stocks')
        setConfig({
          ...parsed,
          schema_version: CURRENT_SCHEMA_VERSION,
          alerts: {
            ...parsed.alerts,
            score_confirmation_runs: parsed.alerts.score_confirmation_runs || 2,
          },
        })
      })
      .catch(() => window.alert('配置文件格式不正确。'))
  }

  return (
    <div className="page-stack">
      <SectionTitle
        eyebrow="CONFIGURATION"
        title="设置"
        action={
          <button className="primary-button compact" onClick={save}>
            {saved ? '已保存在本机' : '保存本机设置'}
          </button>
        }
      />
      <section className="notice-strip warning">
        <div>!</div>
        <p>
          <strong>静态部署边界</strong>
          此页修改先保存在当前设备。要让 GitHub Actions 后台使用，请导出 settings.json
          并替换仓库的 config/settings.json。密钥只能放 GitHub Secrets。
        </p>
      </section>

      <section className="panel settings-section">
        <SectionTitle title="免费盘中风险观察" />
        <div className="settings-grid">
          <label>
            检查频率（分钟）
            <select
              value={config.intraday.interval_minutes}
              onChange={(event) => setConfig({
                ...config,
                intraday: { ...config.intraday, interval_minutes: Number(event.target.value) },
              })}
            >
              <option value="5">5 分钟</option>
              <option value="15">15 分钟</option>
              <option value="30">30 分钟</option>
              <option value="60">60 分钟</option>
            </select>
          </label>
          <label>
            异常下跌阈值（%）
            <input type="number" min="0" step="0.1" value={config.intraday.abnormal_drop_percent} onChange={(event) => setConfig({ ...config, intraday: { ...config.intraday, abnormal_drop_percent: Number(event.target.value) } })} />
          </label>
          <label>
            从盘中高点回落（%）
            <input type="number" min="0" step="0.1" value={config.intraday.pullback_from_high_percent} onChange={(event) => setConfig({ ...config, intraday: { ...config.intraday, pullback_from_high_percent: Number(event.target.value) } })} />
          </label>
          <label>
            跌破支撑缓冲（%）
            <input type="number" min="0" step="0.1" value={config.intraday.support_break_percent} onChange={(event) => setConfig({ ...config, intraday: { ...config.intraday, support_break_percent: Number(event.target.value) } })} />
          </label>
        </div>
        <div className="switch-row">
          <label><input type="checkbox" checked={config.intraday.enabled} onChange={(event) => setConfig({ ...config, intraday: { ...config.intraday, enabled: event.target.checked } })} /> 启用实验性盘中观察</label>
          <Badge tone="warning">AKShare 免费来源，不替代券商条件单</Badge>
        </div>
      </section>

      <section className="panel settings-section">
        <SectionTitle title="数据源与频率" />
        <div className="settings-grid">
          <label>
            行情数据源
            <select
              value={config.provider}
              onChange={(event) => setConfig({ ...config, provider: event.target.value })}
            >
              <option value="sample">sample（演示）</option>
              <option value="yfinance">yfinance</option>
              <option value="alpha_vantage">Alpha Vantage</option>
              <option value="twelve_data">Twelve Data</option>
            </select>
          </label>
          <label>
            分析频率（分钟）
            <input
              type="number"
              min="5"
              value={config.analysis_frequency_minutes}
              onChange={(event) =>
                setConfig({ ...config, analysis_frequency_minutes: Number(event.target.value) })
              }
            />
          </label>
          <label>
            历史区间
            <select
              value={config.history_period}
              onChange={(event) => setConfig({ ...config, history_period: event.target.value })}
            >
              <option value="6mo">6 个月</option>
              <option value="1y">1 年</option>
              <option value="2y">2 年</option>
              <option value="5y">5 年</option>
            </select>
          </label>
          <label>
            提醒冷却（小时）
            <input
              type="number"
              min="0"
              value={config.alerts.cooldown_hours}
              onChange={(event) =>
                setConfig({
                  ...config,
                  alerts: { ...config.alerts, cooldown_hours: Number(event.target.value) },
                })
              }
            />
          </label>
        </div>
        <p className="muted">
          当前按交易日北京时间 16:30 分析一次。Alpha Vantage 免费层是日线收盘数据，不是盘中实时行情。
        </p>
      </section>

      <section className="panel settings-section">
        <SectionTitle title="评分与风险阈值" />
        <div className="settings-grid">
          <label>
            买入提醒阈值
            <input
              type="number"
              min="0"
              max="100"
              value={config.scoring.buy_alert_threshold}
              onChange={(event) =>
                setConfig({
                  ...config,
                  scoring: {
                    ...config.scoring,
                    buy_alert_threshold: Number(event.target.value),
                  },
                })
              }
            />
          </label>
          <label>
            卖出提醒阈值
            <input
              type="number"
              min="0"
              max="100"
              value={config.scoring.sell_alert_threshold}
              onChange={(event) =>
                setConfig({
                  ...config,
                  scoring: {
                    ...config.scoring,
                    sell_alert_threshold: Number(event.target.value),
                  },
                })
              }
            />
          </label>
          <label>
            连续确认次数
            <input
              type="number"
              min="1"
              max="5"
              value={config.alerts.score_confirmation_runs}
              onChange={(event) =>
                setConfig({
                  ...config,
                  alerts: {
                    ...config.alerts,
                    score_confirmation_runs: Number(event.target.value),
                  },
                })
              }
            />
          </label>
          <label>
            最大回撤阈值（%）
            <input
              type="number"
              min="1"
              value={config.scoring.high_drawdown_percent}
              onChange={(event) =>
                setConfig({
                  ...config,
                  scoring: {
                    ...config.scoring,
                    high_drawdown_percent: Number(event.target.value),
                  },
                })
              }
            />
          </label>
          <label>
            异常单日涨跌（%）
            <input
              type="number"
              min="1"
              value={config.scoring.abnormal_daily_change_percent}
              onChange={(event) =>
                setConfig({
                  ...config,
                  scoring: {
                    ...config.scoring,
                    abnormal_daily_change_percent: Number(event.target.value),
                  },
                })
              }
            />
          </label>
        </div>
        <div className="switch-row">
          <label>
            <input
              type="checkbox"
              checked={config.alerts.simulation_mode}
              onChange={(event) =>
                setConfig({
                  ...config,
                  alerts: { ...config.alerts, simulation_mode: event.target.checked },
                })
              }
            />{' '}
            模拟提醒模式
          </label>
          <label>
            <input
              type="checkbox"
              checked={config.alerts.live_alerts_enabled}
              onChange={(event) =>
                setConfig({
                  ...config,
                  alerts: { ...config.alerts, live_alerts_enabled: event.target.checked },
                })
              }
            />{' '}
            真实数据提醒（仍不自动交易）
          </label>
          <Badge tone="warning">默认保持模拟提醒</Badge>
        </div>
      </section>

      <section className="panel settings-section">
        <SectionTitle title="产品管理" action={<Badge>{config.stocks.length} 只</Badge>} />
        <div className="stock-settings">
          {config.stocks.map((stock, index) => (
            <article key={stock.symbol}>
              <div className="stock-settings-head">
                <strong>
                  {stock.symbol} · {stock.name}
                </strong>
                <button
                  className="text-button danger"
                  onClick={() =>
                    setConfig({
                      ...config,
                      stocks: config.stocks.filter((_, itemIndex) => itemIndex !== index),
                    })
                  }
                >
                  删除
                </button>
              </div>
              <div className="settings-grid compact-grid">
                <label>
                  持仓成本
                  <input
                    type="number"
                    value={stock.cost_basis}
                    onChange={(event) =>
                      updateStock(index, { cost_basis: Number(event.target.value) })
                    }
                  />
                </label>
                <label>
                  持仓数量
                  <input
                    type="number"
                    value={stock.quantity}
                    onChange={(event) =>
                      updateStock(index, { quantity: Number(event.target.value) })
                    }
                  />
                </label>
                <label>
                  目标收益率 %
                  <input
                    type="number"
                    value={stock.target_return_percent}
                    onChange={(event) =>
                      updateStock(index, { target_return_percent: Number(event.target.value) })
                    }
                  />
                </label>
                <label>
                  最大亏损 %
                  <input
                    type="number"
                    value={stock.max_loss_percent}
                    onChange={(event) =>
                      updateStock(index, { max_loss_percent: Number(event.target.value) })
                    }
                  />
                </label>
                <label>
                  止盈价
                  <input
                    type="number"
                    value={stock.take_profit_price ?? ''}
                    onChange={(event) =>
                      updateStock(index, {
                        take_profit_price: event.target.value
                          ? Number(event.target.value)
                          : null,
                      })
                    }
                  />
                </label>
                <label>
                  止损价
                  <input
                    type="number"
                    value={stock.stop_loss_price ?? ''}
                    onChange={(event) =>
                      updateStock(index, {
                        stop_loss_price: event.target.value
                          ? Number(event.target.value)
                          : null,
                      })
                    }
                  />
                </label>
              </div>
              <div className="switch-row">
                <label>
                  <input
                    type="checkbox"
                    checked={stock.email_enabled}
                    onChange={(event) =>
                      updateStock(index, { email_enabled: event.target.checked })
                    }
                  />{' '}
                  邮件
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={stock.buy_alert_enabled}
                    onChange={(event) =>
                      updateStock(index, { buy_alert_enabled: event.target.checked })
                    }
                  />{' '}
                  买入提醒
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={stock.sell_alert_enabled}
                    onChange={(event) =>
                      updateStock(index, { sell_alert_enabled: event.target.checked })
                    }
                  />{' '}
                  卖出提醒
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={stock.daily_summary_enabled}
                    onChange={(event) =>
                      updateStock(index, { daily_summary_enabled: event.target.checked })
                    }
                  />{' '}
                  每日总结
                </label>
              </div>
            </article>
          ))}
        </div>
        <div className="add-stock">
          <input
            placeholder="代码，如 510300.SHH"
            value={newStock.symbol}
            onChange={(event) => setNewStock({ ...newStock, symbol: event.target.value })}
          />
          <input
            placeholder="名称"
            value={newStock.name}
            onChange={(event) => setNewStock({ ...newStock, name: event.target.value })}
          />
          <select
            value={newStock.market}
            onChange={(event) => setNewStock({ ...newStock, market: event.target.value })}
          >
            <option value="CN">国内产品 CN</option>
            <option value="HK">港股 HK</option>
            <option value="US">美股 US</option>
          </select>
          <button className="secondary-button" onClick={add}>
            添加产品
          </button>
        </div>
      </section>

      <section className="panel settings-section">
        <SectionTitle title="导入、导出与密钥" />
        <div className="action-row">
          <button className="secondary-button" onClick={exportConfig}>
            导出 settings.json
          </button>
          <label className="secondary-button file-button">
            导入 settings.json
            <input
              type="file"
              accept="application/json"
              onChange={(event) => importConfig(event.target.files?.[0])}
            />
          </label>
        </div>
        <div className="secret-note">
          <Badge tone="success">安全</Badge>
          <p>
            本页面不接收 API Key、邮箱密码或券商密码。请把{' '}
            <code>ALPHA_VANTAGE_API_KEY</code>、<code>TWELVE_DATA_API_KEY</code>、
            <code>RESEND_API_KEY</code> 或 SMTP 授权码放入 GitHub Secrets。
          </p>
        </div>
      </section>
    </div>
  )
}
