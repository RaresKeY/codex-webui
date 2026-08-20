import { describe, expect, it } from 'vitest'

// The production browser bundle intentionally omits Node typings; this test alone reads a source fixture.
// @ts-expect-error node:fs is provided by the Vitest runtime.
const { readFileSync } = await import('node:fs')
const styles = readFileSync(new URL('./styles.css', import.meta.url), 'utf8') as string

describe('application shell layout contract', () => {
  it('pins navigation, the primary conversation, and context to named desktop areas', () => {
    expect(styles).toContain('grid-template-areas: "rail conversations conversation context"')
    expect(styles).toContain('.app-rail { z-index: 8; grid-area: rail;')
    expect(styles).toContain('.chat-sidebar { grid-area: conversations;')
    expect(styles).toContain('.content-area { grid-area: conversation;')
    expect(styles).toContain('.context-panel { grid-area: context;')
  })

  it('reduces to rail plus conversation and overlays both drawers at the narrow breakpoint', () => {
    const narrowStyles = styles.slice(styles.indexOf('@media (max-width: 1000px)'))
    expect(narrowStyles).toContain('grid-template-areas: "rail conversation"')
    expect(narrowStyles).toContain('.chat-sidebar, .context-panel { position: fixed;')
    expect(narrowStyles).toContain('.context-panel { top: 8px; right: 8px; bottom: 8px;')
  })
})
