import { useMemo, useState } from 'react'
import { Icon } from '../../shared/components/Icon'
import { categories, tools, type CategoryId, type Tool } from './catalog'

type Filter = 'all' | 'first' | CategoryId

function ToolCard({ tool }: { tool: Tool }) {
  const available = !!tool.available
  return (
    <article className={`tool-card ${available ? 'tool-card--available' : ''}`} aria-label={`${tool.name}, ${available ? 'available' : tool.release ? 'first release, planned' : 'future release, planned'}`}>
      <span className={`tool-icon tool-icon--${tool.category}`}><Icon name={tool.icon} /></span>
      <div className="tool-card__content">
        <div className="tool-card__heading"><h3>{tool.name}</h3><span className={`tool-badge ${available ? 'tool-badge--live' : tool.release ? 'tool-badge--first' : ''}`}>{available ? 'Available' : tool.release ? 'First release' : 'Later'}</span></div>
        <p>{tool.description}</p>
      </div>
      {available ? <a className="tool-card__link" href={`#${tool.name.toLowerCase().replace(/ /g, '-')}`}>Open {tool.name} <span aria-hidden="true">→</span></a> : <span className="tool-card__availability">Planned · unavailable</span>}
    </article>
  )
}

export function ToolCatalog() {
  const activeReleaseCount = tools.filter(tool => tool.release).length
  const [filter, setFilter] = useState<Filter>('all')
  const [query, setQuery] = useState('')
  const normalizedQuery = query.trim().toLowerCase()
  const visibleGroups = useMemo(() => categories.map(category => ({
    ...category,
    tools: tools.filter(tool => tool.category === category.id && (filter === 'all' || filter === category.id || (filter === 'first' && tool.release)) && `${tool.name} ${tool.description}`.toLowerCase().includes(normalizedQuery)),
  })).filter(group => group.tools.length > 0), [filter, normalizedQuery])
  const resultCount = visibleGroups.reduce((sum, group) => sum + group.tools.length, 0)

  const selectFilter = (next: Filter) => {
    setFilter(next)
    document.getElementById('catalog-title')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  return (
    <section className="catalog-section" id="catalog" aria-labelledby="catalog-title">
      <div className="catalog-heading">
        <div><span className="eyebrow">THE TOOL LIBRARY</span><h2 id="catalog-title">Find your next PDF tool<span className="accent-dot">.</span></h2><p>Merge PDF, Split PDF, Organize pages, Rotate PDF, Add page numbers, Crop PDF, Compress PDF, PDF to Word, Protect PDF, and Watermark PDF are ready to use. Explore the rest of the toolkit planned for PageKit.</p></div>
        <span className="catalog-count">{tools.length} tools in the library</span>
      </div>

      <div className="catalog-controls">
        <label className="search-field"><Icon name="scan" /><span className="sr-only">Search planned tools</span><input value={query} onChange={event => setQuery(event.target.value)} type="search" placeholder="Search tools, like ‘merge’ or ‘image’" /></label>
        <div className="filter-list" role="group" aria-label="Filter tools">
          <button className={filter === 'all' ? 'filter-pill active' : 'filter-pill'} onClick={() => selectFilter('all')} aria-pressed={filter === 'all'}>All tools</button>
          <button className={filter === 'first' ? 'filter-pill active' : 'filter-pill'} onClick={() => selectFilter('first')} aria-pressed={filter === 'first'}>Active release <span>{activeReleaseCount}</span></button>
          {categories.map(category => <button key={category.id} className={filter === category.id ? 'filter-pill active' : 'filter-pill'} onClick={() => selectFilter(category.id)} aria-pressed={filter === category.id}>{category.label}</button>)}
        </div>
      </div>

      <p className="result-count" role="status">Showing {resultCount} {resultCount === 1 ? 'tool' : 'tools'}</p>
      {visibleGroups.length ? visibleGroups.map(group => <div className="tool-group" key={group.id}>
        <div className="tool-group__heading"><div><span className={`group-mark group-mark--${group.id}`} aria-hidden="true" /><h3>{group.label}</h3><span className="group-count">{group.tools.length}</span></div><p>{group.description}</p></div>
        <div className="tool-grid">{group.tools.map(tool => <ToolCard tool={tool} key={tool.name} />)}</div>
      </div>) : <div className="empty-state"><Icon name="scan" /><h3>No tools found</h3><p>Try a different search or choose another category.</p><button onClick={() => { setQuery(''); setFilter('all') }}>Clear filters</button></div>}
    </section>
  )
}
