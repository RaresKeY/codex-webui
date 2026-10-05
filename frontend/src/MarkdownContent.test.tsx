import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { MarkdownContent } from './MarkdownContent'

describe('MarkdownContent', () => {
  it('renders CommonMark and GitHub-flavored structures', () => {
    const html = renderToStaticMarkup(<MarkdownContent source={'## Result\n\n**Ready**\n\n- one\n- two\n\n~~old~~\n\n| A | B |\n| - | - |\n| 1 | 2 |'} />)
    expect(html).toContain('<h2>Result</h2>')
    expect(html).toContain('<strong>Ready</strong>')
    expect(html).toContain('<ul>')
    expect(html).toContain('<del>old</del>')
    expect(html).toContain('<table>')
  })

  it('keeps raw HTML disabled and rejects unsafe link schemes', () => {
    const html = renderToStaticMarkup(<MarkdownContent source={'<script>alert(1)</script>\n\n[unsafe](javascript:alert(1)) [safe](https://example.com)'} />)
    expect(html).not.toContain('<script>')
    expect(html).not.toContain('javascript:')
    expect(html).toContain('href="https://example.com"')
    expect(html).toContain('rel="noreferrer noopener"')
  })

  it('wraps fenced code with a copy control and tolerates partial streaming syntax', () => {
    const code = renderToStaticMarkup(<MarkdownContent source={'```ts\nconst answer = 42\n```'} />)
    expect(code).toContain('markdown-code-block')
    expect(code).toContain('Copy code block')
    expect(code).toContain('language-ts')
    expect(() => renderToStaticMarkup(<MarkdownContent source={'A **partial'} />)).not.toThrow()
  })
})
