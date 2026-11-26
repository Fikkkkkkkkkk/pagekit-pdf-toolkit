import { lazy, Suspense, useEffect, useState } from 'react'
import { Icon } from '../shared/components/Icon'
import { ToolCatalog } from '../features/tool-catalog/ToolCatalog'
import { tools } from '../features/tool-catalog/catalog'
import { AboutGuide, SiteFooter, SiteHeader } from './SiteChrome'
import { SplitPdfPage } from '../features/split-pdf/SplitPdfPage'
import { MergePdfPage } from '../features/merge-pdf/MergePdfPage'

const OrganizePagesPage = lazy(() => import('../features/organize-pages/OrganizePagesPage').then(module => ({ default: module.OrganizePagesPage })))
const RotatePdfPage = lazy(() => import('../features/rotate-pdf/RotatePdfPage').then(module => ({ default: module.RotatePdfPage })))
const AddPageNumbersPage = lazy(() => import('../features/add-page-numbers/AddPageNumbersPage').then(module => ({ default: module.AddPageNumbersPage })))
const CropPdfPage = lazy(() => import('../features/crop-pdf/CropPdfPage').then(module => ({ default: module.CropPdfPage })))
const CompressPdfPage = lazy(() => import('../features/compress-pdf/CompressPdfPage').then(module => ({ default: module.CompressPdfPage })))
const PdfToWordPage = lazy(() => import('../features/pdf-to-word/PdfToWordPage').then(module => ({ default: module.PdfToWordPage })))
const ProtectPdfPage = lazy(() => import('../features/protect-pdf/ProtectPdfPage').then(module => ({ default: module.ProtectPdfPage })))
const WatermarkPdfPage = lazy(() => import('../features/watermark-pdf/WatermarkPdfPage').then(module => ({ default: module.WatermarkPdfPage })))
const JpgToPdfPage = lazy(() => import('../features/jpg-to-pdf/JpgToPdfPage').then(module => ({ default: module.JpgToPdfPage })))
const UnlockPdfPage = lazy(() => import('../features/unlock-pdf/UnlockPdfPage').then(module => ({ default: module.UnlockPdfPage })))
const SignPdfPage = lazy(() => import('../features/sign-pdf/SignPdfPage').then(module => ({ default: module.SignPdfPage })))
const PdfToJpgPage = lazy(() => import('../features/pdf-to-jpg/PdfToJpgPage').then(module => ({ default: module.PdfToJpgPage })))

function currentTool() {
  if (window.location.hash === '#merge-pdf') return 'merge'
  if (window.location.hash === '#split-pdf') return 'split'
  if (window.location.hash === '#organize-pages') return 'organize'
  if (window.location.hash === '#rotate-pdf') return 'rotate'
  if (window.location.hash === '#add-page-numbers') return 'numbers'
  if (window.location.hash === '#crop-pdf') return 'crop'
  if (window.location.hash === '#compress-pdf') return 'compress'
  if (window.location.hash === '#pdf-to-word') return 'word'
  if (window.location.hash === '#protect-pdf') return 'protect'
  if (window.location.hash === '#watermark-pdf') return 'watermark'
  if (window.location.hash === '#jpg-to-pdf') return 'jpg'
  if (window.location.hash === '#unlock-pdf') return 'unlock'
  if (window.location.hash === '#pdf-to-jpg') return 'pdfjpg'
  if (window.location.hash === '#sign-pdf') return 'sign'
  return null
}

export function App() {
  const [activeTool, setActiveTool] = useState(currentTool)

  useEffect(() => {
    const updatePage = () => setActiveTool(currentTool())
    window.addEventListener('hashchange', updatePage)
    return () => window.removeEventListener('hashchange', updatePage)
  }, [])

  useEffect(() => {
    if (!activeTool && (window.location.hash === '#catalog' || window.location.hash === '#about')) {
      const target = window.location.hash.slice(1)
      requestAnimationFrame(() => document.getElementById(target)?.scrollIntoView())
    } else if (activeTool) {
      window.scrollTo(0, 0)
    }
  }, [activeTool])

  const availableToolCount = tools.filter(tool => tool.available).length

  return <div className="app-shell">
    <SiteHeader />

    {activeTool === 'sign' ? <main id='top'><Suspense fallback={<p className='container' role='status'>Opening Sign PDF...</p>}><SignPdfPage /></Suspense></main> : activeTool === 'merge' ? <main id="top"><MergePdfPage /></main> : activeTool === 'split' ? <main id="top"><SplitPdfPage /></main> : activeTool === 'organize' ? <main id="top"><Suspense fallback={<p className="container" role="status">Opening Organize pages…</p>}><OrganizePagesPage /></Suspense></main> : activeTool === 'rotate' ? <main id="top"><Suspense fallback={<p className="container" role="status">Opening Rotate PDF…</p>}><RotatePdfPage /></Suspense></main> : activeTool === 'numbers' ? <main id="top"><Suspense fallback={<p className="container" role="status">Opening Add page numbers…</p>}><AddPageNumbersPage /></Suspense></main> : activeTool === 'crop' ? <main id="top"><Suspense fallback={<p className="container" role="status">Opening Crop PDF…</p>}><CropPdfPage /></Suspense></main> : activeTool === 'compress' ? <main id="top"><Suspense fallback={<p className="container" role="status">Opening Compress PDF…</p>}><CompressPdfPage /></Suspense></main> : activeTool === 'word' ? <main id="top"><Suspense fallback={<p className="container" role="status">Opening PDF to Word…</p>}><PdfToWordPage /></Suspense></main> : activeTool === 'protect' ? <main id="top"><Suspense fallback={<p className="container" role="status">Opening Protect PDF…</p>}><ProtectPdfPage /></Suspense></main> : activeTool === 'watermark' ? <main id="top"><Suspense fallback={<p className="container" role="status">Opening Watermark PDF…</p>}><WatermarkPdfPage /></Suspense></main> : activeTool === 'jpg' ? <main id="top"><Suspense fallback={<p className="container" role="status">Opening JPG to PDF…</p>}><JpgToPdfPage /></Suspense></main> : activeTool === 'unlock' ? <main id="top"><Suspense fallback={<p className="container" role="status">Opening Unlock PDF…</p>}><UnlockPdfPage /></Suspense></main> : activeTool === 'pdfjpg' ? <main id="top"><Suspense fallback={<p className="container" role="status">Opening PDF to JPG…</p>}><PdfToJpgPage /></Suspense></main> : <main id="top">
      <section className="hero"><div className="container hero-inner">
        <div className="hero-copy"><span className="hero-kicker"><span aria-hidden="true">✳</span> A BETTER WAY TO HANDLE PDFS</span><h1>Study smarter.<br /><em>Sort your PDFs.</em></h1><p>From scattered lecture notes to polished submissions, PageKit is being built to make the little document tasks feel effortless.</p><a className="hero-link" href="#catalog">Explore the tools <span aria-hidden="true">↓</span></a><div className="hero-note"><span className="note-dot" /> {availableToolCount} tools ready, including Sign PDF · More are on the way</div></div>
        <div className="hero-art" aria-hidden="true"><div className="art-orbit art-orbit--one" /><div className="art-orbit art-orbit--two" /><div className="art-spark art-spark--one">✳</div><div className="art-spark art-spark--two">✦</div><div className="art-card art-card--back"><span className="art-card__top"/><span className="art-line"/><span className="art-line short"/><span className="art-block"/></div><div className="art-card art-card--front"><div className="art-card__label"><span className="mini-file">PDF</span><span>STUDY NOTES</span></div><div className="art-title-lines"><span/><span/></div><div className="art-highlight"/><div className="art-copy-lines"><span/><span/><span/></div><div className="art-chart"><span/><span/><span/><span/></div></div><div className="art-sticker"><span>✦</span><strong>Make space<br/>for ideas.</strong></div></div>
      </div></section>

      <div className="container"><div className="promise-strip"><div><span className="promise-icon"><Icon name="pages" /></span><p><strong>One place for every PDF task</strong><span>A growing toolkit for study life</span></p></div><div><span className="promise-icon"><Icon name="spark" /></span><p><strong>Simple by design</strong><span>Clear steps, no extra clutter</span></p></div><div><span className="promise-icon"><Icon name="lock" /></span><p><strong>Privacy in the plan</strong><span>Files handled with care</span></p></div></div></div>

      <div className="container"><ToolCatalog /></div>

      <AboutGuide />
    </main>}

    <SiteFooter />
  </div>
}
