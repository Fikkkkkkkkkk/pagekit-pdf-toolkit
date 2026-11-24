import type { SVGProps } from 'react'

type Props = SVGProps<SVGSVGElement> & { name: string }

const paths: Record<string, React.ReactNode> = {
  merge: <><rect x="4" y="3" width="10" height="13" rx="2"/><path d="M10 8h7a3 3 0 0 1 3 3v8a2 2 0 0 1-2 2h-8a2 2 0 0 1-2-2v-1"/><path d="M9 11h6m-3-3 3 3-3 3"/></>,
  split: <><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M12 3v18M7 12l3-3m-3 3 3 3m7-3-3-3m3 3-3 3"/></>,
  pages: <><rect x="4" y="4" width="7" height="7" rx="1"/><rect x="13" y="4" width="7" height="7" rx="1"/><rect x="4" y="13" width="7" height="7" rx="1"/><rect x="13" y="13" width="7" height="7" rx="1"/></>,
  rotate: <><path d="M20 11a8 8 0 1 1-3-6.2M20 4v6h-6"/><path d="M9 9h6v7H9z"/></>,
  numbers: <><rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 8h6m-6 4h6m-4 5h2"/></>,
  crop: <><path d="M6 3v14a1 1 0 0 0 1 1h14M3 6h14a1 1 0 0 1 1 1v14"/></>,
  repair: <><path d="M13 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V10zM13 3v7h7"/><path d="m8 16 2 2 5-5"/></>,
  scan: <><path d="M4 8V5a1 1 0 0 1 1-1h3m8 0h3a1 1 0 0 1 1 1v3M4 16v3a1 1 0 0 0 1 1h3m8 0h3a1 1 0 0 0 1-1v-3M3 12h18"/><path d="M8 9h8m-8 6h8"/></>,
  compress: <><rect x="5" y="3" width="14" height="18" rx="2"/><path d="M8 12h8m-6-3 3 3-3 3m4-6-3 3 3 3"/></>,
  word: <><rect x="4" y="3" width="16" height="18" rx="2"/><path d="m7 9 2 7 3-5 3 5 2-7"/></>,
  slides: <><rect x="3" y="4" width="18" height="13" rx="2"/><path d="M12 17v4m-5 0h10m-9-13h8m-8 4h5"/></>,
  sheet: <><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M4 9h16M4 15h16m-10-6v12"/></>,
  image: <><rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="8" cy="9" r="1.5"/><path d="m4 18 6-6 3 3 3-4 5 6"/></>,
  archive: <><rect x="4" y="4" width="16" height="5" rx="1"/><path d="M6 9v11h12V9m-8 4h4"/></>,
  markdown: <><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M6 15V9l3 3 3-3v6m4-6v6m-2-2 2 2 2-2"/></>,
  web: <><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18"/></>,
  edit: <><path d="M12 20H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11a2 2 0 0 1 2 2v6"/><path d="m14 18 5-5 2 2-5 5-3 1zM7 8h7m-7 4h5"/></>,
  watermark: <><rect x="4" y="3" width="16" height="18" rx="2"/><path d="m7 16 4-5 3 3 2-2 2 3M8 8h8"/></>,
  form: <><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h4m3 0h2"/></>,
  lock: <><rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3m-4 4v3"/></>,
  unlock: <><rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 7.5-2m-3.5 9v3"/></>,
  sign: <><path d="M3 19c4-1 4-7 6-7 3 0-2 7 1 7 2 0 3-3 5-3 1 0 1 2 3 2h3M5 7h14M5 4h9"/></>,
  redact: <><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M7 9h10M7 13h10M7 17h7"/><path d="M7 11h10" strokeWidth="3"/></>,
  compare: <><path d="M11 4H5a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h6M13 3h6a2 2 0 0 1 2 2v13a2 2 0 0 1-2 2h-6M12 3v18"/></>,
  spark: <><path d="m12 2 2.2 7.8L22 12l-7.8 2.2L12 22l-2.2-7.8L2 12l7.8-2.2z"/></>,
  translate: <><path d="M3 5h12M9 3v2m4 0c-1 6-4 9-8 11m0-7c2 3 5 5 8 6m2-3 3 9m-6 0 3-9m-1 6h4"/></>,
}

export function Icon({ name, ...props }: Props) {
  return <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>{paths[name] ?? paths.pages}</svg>
}
