import { useContext, isValidElement, useEffect, useRef, useState, type ReactNode } from 'react'
import ReactMarkdown, { defaultUrlTransform, type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Check, Copy, WrapText } from 'lucide-react'
import { InlineImages } from './InlineImages'
import { imageSource } from './images'
import { workspaceLink } from './workspace-link'
import { WorkspaceLinkContext } from './workspace-link-context'


function nodeText(node: ReactNode): string {
  if (typeof node === 'string' || typeof node === 'number' || typeof node === 'bigint') return String(node)
  if (Array.isArray(node)) return node.map(nodeText).join('')
  if (isValidElement<{ children?: ReactNode }>(node)) return nodeText(node.props.children)
  return ''
}

function CodeBlock({ children }: { children?: ReactNode }) {
  const [copied, setCopied] = useState(false)
  const resetTimer = useRef<number | undefined>(undefined)
  const language = isValidElement<{ className?: string }>(children)
    ? children.props.className?.replace(/^language-/, '')
    : undefined
  useEffect(() => () => { if (resetTimer.current !== undefined) window.clearTimeout(resetTimer.current) }, [])
  const copyCode = () => {
    if (!navigator.clipboard) return
    void navigator.clipboard.writeText(nodeText(children).replace(/\n$/, '')).then(() => {
      setCopied(true)
      if (resetTimer.current !== undefined) window.clearTimeout(resetTimer.current)
      resetTimer.current = window.setTimeout(() => setCopied(false), 1600)
    }).catch(() => undefined)
  }
  return <div className="markdown-code-block">
    <div className="markdown-code-header"><span>{language || 'Code'}</span><button type="button" onClick={copyCode} aria-label="Copy code block">{copied ? <Check size={12} /> : <Copy size={12} />}{copied ? 'Copied' : 'Copy'}</button></div>
    <pre>{children}</pre>
  </div>
}

function MarkdownTable({ children }: { children?: ReactNode }) {
  const [wrap, setWrap] = useState(false)
  return <div className="markdown-table"><div className="markdown-table-toolbar"><button type="button" aria-label="Soft wrap table" aria-pressed={wrap} onClick={() => setWrap(value => !value)}><WrapText size={14} />Soft wrap</button></div><div className={`markdown-table-wrap ${wrap ? 'soft-wrap' : ''}`}><table>{children}</table></div></div>
}

const components: Components = {
  a: ({ href, children, title }) => <a href={href} title={title} target="_blank" rel="noreferrer noopener">{children}</a>,
  pre: ({ children }) => <CodeBlock>{children}</CodeBlock>,
  table: ({ children }) => <MarkdownTable>{children}</MarkdownTable>,
  img: ({ src, alt }) => typeof src === 'string' && src ? <InlineImages images={[{ url: src, alt: alt || 'Image' }]} /> : <span>Image unavailable</span>,
}

export function MarkdownContent({ source, compact = false, cwd }: { source: string; compact?: boolean; cwd?: string }) {
  const openFile = useContext(WorkspaceLinkContext)
  const linkedComponents: Components = { ...components, a: ({ href, children, title }) => {
    const path = href ? workspaceLink(href, cwd) : null
    return <a href={href} title={title || (path && openFile ? 'Open file in sidebar' : undefined)} target={path && openFile ? undefined : '_blank'} rel="noreferrer noopener" onClick={event => { if (path && openFile && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey) { event.preventDefault(); openFile(path) } }}>{children}</a>
  } }
  return <div className={`markdown-content ${compact ? 'compact' : ''}`}>
    <ReactMarkdown components={linkedComponents} remarkPlugins={[remarkGfm]} skipHtml urlTransform={(url, key) => key === 'src' ? imageSource(url, cwd) ?? '' : defaultUrlTransform(url)}>{source}</ReactMarkdown>
  </div>
}
