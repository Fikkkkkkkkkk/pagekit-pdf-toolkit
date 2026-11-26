import { useEffect, useRef, useState } from 'react'
import { categories, tools } from '../features/tool-catalog/catalog'

const availableGroups = categories.map(category => ({
  ...category,
  available: tools.filter(tool => tool.available && tool.category === category.id),
})).filter(category => category.available.length > 0)

export function SiteHeader() {
  const [menuOpen, setMenuOpen] = useState(false)
  const menuButton = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!menuOpen) return
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setMenuOpen(false)
        menuButton.current?.focus()
      }
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [menuOpen])

  return <header className="site-header">
    <div className="container header-inner">
      <a className="brand" href="#catalog" aria-label="PageKit: browse available tools" onClick={() => setMenuOpen(false)}><span className="brand-mark" aria-hidden="true"><span /></span><span>pagekit<span className="brand-dot">.</span></span></a>
      <button ref={menuButton} className="header-menu-button" type="button" aria-label={menuOpen ? 'Close navigation menu' : 'Open navigation menu'} aria-expanded={menuOpen} aria-controls="site-main-nav" onClick={() => setMenuOpen(open => !open)}><span className="header-menu-icon" aria-hidden="true"><span /><span /><span /></span></button>
      <nav id="site-main-nav" className={menuOpen ? 'header-nav-open' : ''} aria-label="Main navigation"><a className="header-nav-primary" href="#catalog" onClick={() => setMenuOpen(false)}>Browse tools</a><a className="header-nav-secondary" href="#about" onClick={() => setMenuOpen(false)}>About PageKit</a></nav>
    </div>
  </header>
}

export function AboutGuide() {
  return <section className="about-section" id="about" aria-labelledby="about-title"><div className="container about-guide">
    <div className="about-guide__intro"><div><span className="eyebrow">ABOUT PAGEKIT</span><h2 id="about-title">Less PDF busywork.<br /><em>More time to study.</em></h2></div><p>PageKit helps students organize, convert, edit, and secure documents. Choose a tool, review its options and preview, then download a new result. No account is needed.</p></div>
    <div className="about-guide__details">
      <div><span className="about-guide__label">FILE HANDLING</span><h3>Processed for your request</h3><p>Most tools send selected files to PageKit’s Flask backend. PDF to JPG renders pages in your browser, then sends JPGs for ZIP packaging. Temporary request folders are removed when processing ends; abandoned folders are cleared at startup or on later requests once 15 minutes old.</p></div>
      <div><span className="about-guide__label">CHECK YOUR RESULT</span><h3>Know the limits</h3><p>PDF to Word layout can change, and OCR is not available. Crop PDF hides content without securely erasing it. Sign PDF adds a visual mark, not a cryptographic signature. Compression can make a file larger or soften images.</p></div>
    </div>
  </div></section>
}

export function SiteFooter() {
  return <footer className="site-footer"><div className="container footer-inner">
    <div className="footer-top"><div className="footer-brand"><a className="brand" href="#catalog" aria-label="PageKit: browse available tools"><span className="brand-mark" aria-hidden="true"><span /></span><span>pagekit<span className="brand-dot">.</span></span></a><p>Practical PDF tools for study and submission.</p></div><nav className="footer-primary" aria-label="Footer navigation"><a href="#catalog">Full tool catalog</a><a href="#about">About PageKit</a></nav></div>
    <nav className="footer-tool-groups" aria-label="Available tools by category">{availableGroups.map(group => <div className="footer-tool-group" key={group.id}><h2>{group.label}</h2><ul>{group.available.map(tool => <li key={tool.name}><a href={`#${tool.name.toLowerCase().replace(/ /g, '-')}`}>{tool.name}</a></li>)}</ul></div>)}</nav>
    <nav className="footer-mobile-groups" aria-label="Available tools by category">{availableGroups.map(group => <details key={group.id}><summary><span>{group.label}</span><span className="footer-mobile-groups__count">{group.available.length} tools</span><span className="footer-mobile-groups__chevron" aria-hidden="true" /></summary><ul>{group.available.map(tool => <li key={tool.name}><a href={`#${tool.name.toLowerCase().replace(/ /g, '-')}`}>{tool.name}</a></li>)}</ul></details>)}</nav>
    <p className="footer-files">Temporary request files are removed after processing. Abandoned folders are cleared at startup or on a later request once they are 15 minutes old.</p>
  </div></footer>
}
