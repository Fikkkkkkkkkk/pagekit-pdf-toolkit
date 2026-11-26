export type CategoryId = 'organize' | 'optimize' | 'convert' | 'edit' | 'security' | 'intelligence'

export type Tool = {
  name: string
  description: string
  category: CategoryId
  release?: boolean
  available?: boolean
  icon: string
}

export const categories: { id: CategoryId; label: string; description: string }[] = [
  { id: 'organize', label: 'Organize', description: 'Keep every page in the right place.' },
  { id: 'optimize', label: 'Optimize', description: 'Make large files easier to share.' },
  { id: 'convert', label: 'Convert', description: 'Move between documents and formats.' },
  { id: 'edit', label: 'Edit', description: 'Add what your document needs.' },
  { id: 'security', label: 'Security & review', description: 'Protect, sign, and check your work.' },
  { id: 'intelligence', label: 'PDF intelligence', description: 'Find meaning in complex material.' },
]

export const tools: Tool[] = [
  { name: 'Merge PDF', description: 'Bring readings or handouts into one file.', category: 'organize', release: true, available: true, icon: 'merge' },
  { name: 'Split PDF', description: 'Keep only the sections you need.', category: 'organize', release: true, available: true, icon: 'split' },
  { name: 'Organize pages', description: 'Reorder, add, or remove pages.', category: 'organize', release: true, available: true, icon: 'pages' },
  { name: 'Rotate PDF', description: 'Turn sideways pages the right way up.', category: 'organize', release: true, available: true, icon: 'rotate' },
  { name: 'Add page numbers', description: 'Make notes and citations easier to follow.', category: 'organize', release: true, available: true, icon: 'numbers' },
  { name: 'Crop PDF', description: 'Hide areas outside the selected page bounds.', category: 'organize', release: true, available: true, icon: 'crop' },
  { name: 'Repair PDF', description: 'Try to recover a damaged document.', category: 'organize', icon: 'repair' },
  { name: 'Scan to PDF', description: 'Turn a scan into a shareable PDF.', category: 'organize', icon: 'scan' },
  { name: 'Compress PDF', description: 'Try a smaller copy for easier submission.', category: 'optimize', release: true, available: true, icon: 'compress' },
  { name: 'PDF to Word', description: 'Create an editable Word document.', category: 'convert', release: true, available: true, icon: 'word' },
  { name: 'PDF to PowerPoint', description: 'Move PDF content into slides.', category: 'convert', icon: 'slides' },
  { name: 'PDF to Excel', description: 'Bring tables into a spreadsheet.', category: 'convert', icon: 'sheet' },
  { name: 'PDF to JPG', description: 'Export every page as a JPG in one ZIP.', category: 'convert', release: true, available: true, icon: 'image' },
  { name: 'PDF to PDF/A', description: 'Prepare a file for long-term archiving.', category: 'convert', icon: 'archive' },
  { name: 'PDF to Markdown', description: 'Make PDF content easier to reuse in notes.', category: 'convert', icon: 'markdown' },
  { name: 'Word to PDF', description: 'Make a Word file ready to share.', category: 'convert', icon: 'word' },
  { name: 'PowerPoint to PDF', description: 'Share slides as a PDF.', category: 'convert', icon: 'slides' },
  { name: 'Excel to PDF', description: 'Export a spreadsheet as a PDF.', category: 'convert', icon: 'sheet' },
  { name: 'JPG to PDF', description: 'Combine JPG and PNG images into one PDF.', category: 'convert', release: true, available: true, icon: 'image' },
  { name: 'HTML/webpage to PDF', description: 'Save a web page as a PDF.', category: 'convert', icon: 'web' },
  { name: 'Edit PDF', description: 'Add text, images, shapes, and annotations.', category: 'edit', icon: 'edit' },
  { name: 'Watermark PDF', description: 'Add customizable text to every page.', category: 'edit', release: true, available: true, icon: 'watermark' },
  { name: 'PDF forms', description: 'Create, fill, and edit PDF forms.', category: 'edit', icon: 'form' },
  { name: 'Protect PDF', description: 'Require a password to open a PDF copy.', category: 'security', release: true, available: true, icon: 'lock' },
  { name: 'Unlock PDF', description: 'Remove an opening password you know.', category: 'security', release: true, available: true, icon: 'unlock' },
  { name: 'Sign PDF', description: 'Place a visual signature on selected pages.', category: 'security', release: true, available: true, icon: 'sign' },
  { name: 'Redact PDF', description: 'Permanently hide sensitive content.', category: 'security', icon: 'redact' },
  { name: 'Compare two PDFs', description: 'Spot changes between versions.', category: 'security', icon: 'compare' },
  { name: 'OCR for scanned PDFs', description: 'Make scanned text searchable.', category: 'intelligence', icon: 'scan' },
  { name: 'AI PDF summarizer', description: 'Get a concise view of a long reading.', category: 'intelligence', icon: 'spark' },
  { name: 'Translate PDF', description: 'Read a document in another language.', category: 'intelligence', icon: 'translate' },
]
