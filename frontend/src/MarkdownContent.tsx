import { isValidElement, useEffect, useRef, useState, type ReactNode } from 'react'
import ReactMarkdown, { defaultUrlTransform, type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Check, Copy } from 'lucide-react'
import { InlineImages } from './InlineImages'
import { imageSource } from './images'

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

const components: Components = {
  a: ({ href, children, title }) => <a href={href} title={title} target="_blank" rel="noreferrer noopener">{children}</a>,
  pre: ({ children }) => <CodeBlock>{children}</CodeBlock>,
  table: ({ children }) => <div className="markdown-table-wrap"><table>{children}</table></div>,
  img: ({ src, alt }) => typeof src === 'string' && src ? <InlineImages images={[{ url: src, alt: alt || 'Image' }]} /> : <span>Image unavailable</span>,
}

export function MarkdownContent({ source, compact = false, cwd }: { source: string; compact?: boolean; cwd?: string }) {
  return <div className={`markdown-content ${compact ? 'compact' : ''}`}>
    <ReactMarkdown components={components} remarkPlugins={[remarkGfm]} skipHtml urlTransform={(url, key) => key === 'src' ? imageSource(url, cwd) ?? '' : defaultUrlTransform(url)}>{source}</ReactMarkdown>
  </div>
}
