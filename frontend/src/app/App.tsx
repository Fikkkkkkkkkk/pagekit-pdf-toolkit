import { Icon } from '../shared/components/Icon'
import { ToolCatalog } from '../features/tool-catalog/ToolCatalog'

export function App() {
  return <div className="app-shell">
    <header className="site-header">
      <div className="container header-inner">
        <a className="brand" href="#top" aria-label="PageKit home"><span className="brand-mark" aria-hidden="true"><span /></span><span>pagekit<span className="brand-dot">.</span></span></a>
        <nav aria-label="Main navigation"><a href="#catalog">Explore tools</a><a href="#about">About PageKit</a></nav>
        <span className="header-status"><span className="status-spark" aria-hidden="true">✦</span> In the making</span>
      </div>
    </header>

    <main id="top">
      <section className="hero"><div className="container hero-inner">
        <div className="hero-copy"><span className="hero-kicker"><span aria-hidden="true">✳</span> A BETTER WAY TO HANDLE PDFS</span><h1>Study smarter.<br /><em>Sort your PDFs.</em></h1><p>From scattered lecture notes to polished submissions, PageKit is being built to make the little document tasks feel effortless.</p><a className="hero-link" href="#catalog">Explore the planned tools <span aria-hidden="true">↓</span></a><div className="hero-note"><span className="note-dot" /> Building the first release now · Tools are not available yet</div></div>
        <div className="hero-art" aria-hidden="true"><div className="art-orbit art-orbit--one" /><div className="art-orbit art-orbit--two" /><div className="art-spark art-spark--one">✳</div><div className="art-spark art-spark--two">✦</div><div className="art-card art-card--back"><span className="art-card__top"/><span className="art-line"/><span className="art-line short"/><span className="art-block"/></div><div className="art-card art-card--front"><div className="art-card__label"><span className="mini-file">PDF</span><span>STUDY NOTES</span></div><div className="art-title-lines"><span/><span/></div><div className="art-highlight"/><div className="art-copy-lines"><span/><span/><span/></div><div className="art-chart"><span/><span/><span/><span/></div></div><div className="art-sticker"><span>✦</span><strong>Make space<br/>for ideas.</strong></div></div>
      </div></section>

      <div className="container"><div className="promise-strip"><div><span className="promise-icon"><Icon name="pages" /></span><p><strong>One place for every PDF task</strong><span>A growing toolkit for study life</span></p></div><div><span className="promise-icon"><Icon name="spark" /></span><p><strong>Simple by design</strong><span>Clear steps, no extra clutter</span></p></div><div><span className="promise-icon"><Icon name="lock" /></span><p><strong>Privacy in the plan</strong><span>Files handled with care</span></p></div></div></div>

      <div className="container"><ToolCatalog /></div>

      <section className="about-section" id="about"><div className="container about-inner"><div><span className="eyebrow">BUILT FOR WHAT'S NEXT</span><h2>Less file juggling.<br /><em>More getting things done.</em></h2></div><div><p>PageKit is taking shape around the document jobs students run into every week: combining notes, preparing assignments, and keeping pages in order.</p><p>The first release will focus on seven essential tools. More ways to convert, edit, review, and understand PDFs are planned for later.</p><span className="about-note">Currently in development · No PDF tools are live yet</span></div></div></section>
    </main>

    <footer className="site-footer"><div className="container footer-inner"><a className="brand" href="#top" aria-label="PageKit home"><span className="brand-mark" aria-hidden="true"><span /></span><span>pagekit<span className="brand-dot">.</span></span></a><p>Good ideas deserve less paperwork.</p><span>Made for the way students work.</span></div></footer>
  </div>
}
