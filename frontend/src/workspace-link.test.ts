import { describe, expect, it } from 'vitest'
import { workspaceLink } from './workspace-link'
describe('workspace Markdown links', () => {
  it('resolves relative, absolute and encoded file paths', () => {
    expect(workspaceLink('dog_breeds.txt', '/workspace/chat')).toBe('/workspace/chat/dog_breeds.txt')
    expect(workspaceLink('/workspace/a%20b.txt#L3', '/workspace/chat')).toBe('/workspace/a b.txt')
    expect(workspaceLink('../report.md', '/workspace/chat')).toBe('/workspace/chat/../report.md')
  })
  it('leaves websites, anchors and non-file schemes alone', () => {
    for (const href of ['https://example.org/file.txt', '//example.org/file', '#section', 'mailto:a@b.org', 'javascript:alert(1)', 'file:///etc/passwd', '%00secret', '%ZZ']) expect(workspaceLink(href, '/workspace')).toBeNull()
  })
})
