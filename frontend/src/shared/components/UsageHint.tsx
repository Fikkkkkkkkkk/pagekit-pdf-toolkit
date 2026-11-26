import { Icon } from './Icon'
import './usage-hint.css'

type Step = { title: string; detail: string }

export function UsageHint({ icon, title, steps }: { icon: string; title: string; steps: readonly Step[] }) {
  return <aside className="usage-card" aria-label={`${title} instructions`}>
    <span className="usage-card__icon"><Icon name={icon} /></span>
    <h2>{title}</h2>
    <ol>{steps.map(step => <li key={step.title}><strong>{step.title}</strong><span>{step.detail}</span></li>)}</ol>
  </aside>
}
