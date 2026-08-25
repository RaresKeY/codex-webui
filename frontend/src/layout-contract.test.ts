import { describe, expect, it } from 'vitest'

// The production browser bundle intentionally omits Node typings; this test alone reads a source fixture.
// @ts-expect-error node:fs is provided by the Vitest runtime.
const { readFileSync } = await import('node:fs')
const styles = readFileSync(new URL('./styles.css', import.meta.url), 'utf8') as string
const appSource = readFileSync(new URL('./App.tsx', import.meta.url), 'utf8') as string

describe('application shell layout contract', () => {
  it('pins navigation, the primary conversation, and context to named desktop areas', () => {
    expect(styles).toContain('grid-template-areas: "rail conversations conversation context"')
    expect(styles).toContain('.app-rail { z-index: 8; grid-area: rail;')
    expect(styles).toContain('.chat-sidebar { grid-area: conversations;')
    expect(styles).toContain('.content-area { grid-area: conversation;')
    expect(styles).toContain('.context-panel { grid-area: context;')
    expect(styles).toContain('.rail-panel-controls { width: 100%; display: flex;')
    expect(styles).toContain('.chat-surface.left-panel-closed .chat-header > .icon-button:first-child { display: grid; }')
  })

  it('starts with the optional right context panel collapsed', () => {
    expect(appSource).toContain('const [rightOpen, setRightOpen] = useState(false)')
    expect(appSource).toContain('<IconButton label="Open context panel" onClick={openRight}>')
  })

  it('keeps model selection visible in the header and model provenance on assistant rows', () => {
    expect(appSource).toContain('className="chat-model-select"')
    expect(appSource).toContain('className="message-model"')
    expect(styles).toContain('.chat-model-select { height: 29px;')
    expect(styles).toContain('.message-model { min-width: 0;')
  })

  it('reduces to rail plus conversation and overlays both drawers at the narrow breakpoint', () => {
    const narrowStyles = styles.slice(styles.indexOf('@media (max-width: 1000px)'))
    expect(narrowStyles).toContain('grid-template-areas: "rail conversation"')
    expect(narrowStyles).toContain('.chat-sidebar, .context-panel { position: fixed;')
    expect(narrowStyles).toContain('.context-panel { top: 8px; right: 8px; bottom: 8px;')
    expect(narrowStyles).toContain('.chat-project-select { display: none; }')
  })
})
