import type { ReactNode } from 'react'
import { clamp, formatPercent } from '../utils'

export function ScoreGauge({ score, label, tone }: { score: number; label: string; tone: 'buy' | 'sell' }) {
  const value = clamp(score, 0, 100)
  return (
    <div className="score-block">
      <div
        className={`score-ring ${tone}`}
        style={{ '--score': `${value * 3.6}deg` } as React.CSSProperties}
        aria-label={`${label} ${score} 分`}
      >
        <div><strong>{score}</strong><span>/100</span></div>
      </div>
      <span>{label}</span>
    </div>
  )
}

export function Change({ value }: { value: number }) {
  return <span className={value >= 0 ? 'positive' : 'negative'}>{formatPercent(value)}</span>
}

export function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: string }) {
  return <span className={`badge ${tone}`}>{children}</span>
}

export function StatCard({ label, value, hint, accent }: { label: string; value: ReactNode; hint: string; accent: string }) {
  return (
    <article className="stat-card" style={{ '--accent': accent } as React.CSSProperties}>
      <div className="stat-icon" aria-hidden="true" />
      <p>{label}</p>
      <strong>{value}</strong>
      <small>{hint}</small>
    </article>
  )
}

export function SectionTitle({ eyebrow, title, action }: { eyebrow?: string; title: string; action?: ReactNode }) {
  return (
    <div className="section-title">
      <div>{eyebrow && <span>{eyebrow}</span>}<h2>{title}</h2></div>
      {action}
    </div>
  )
}

export function EmptyState({ title, text }: { title: string; text: string }) {
  return <div className="empty-state"><div>◎</div><h3>{title}</h3><p>{text}</p></div>
}
