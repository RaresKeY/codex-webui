import type { BootstrapPayload, StreamEvent } from './types'

export const demoBootstrap: BootstrapPayload = {
  projects: [
    { id: 'p1', name: 'Codex Web UI', path: '/workspace/codex-webui', color: '#87d4a6', chatCount: 8, updatedAt: 'Now' },
    { id: 'p2', name: 'Code Review Simulator', path: '/workspace/code-review-simulator', color: '#8aa7ff', chatCount: 21, updatedAt: '2h' },
    { id: 'p3', name: 'Trellis CPP', path: '/workspace/trellis.cpp', color: '#e7b36a', chatCount: 12, updatedAt: 'Yesterday' },
  ],
  conversations: [
    { id: 'c1', projectId: 'p1', title: 'Build responsive workspace shell', preview: 'I wired the streaming transport and file explorer…', updatedAt: 'Now', status: 'running', cwd: '/workspace/codex-webui', model: 'gpt-5.6-sol', contextPercent: 34 },
    { id: 'c2', projectId: 'p1', title: 'Container architecture', preview: 'Docker Compose now keeps app data on the host.', updatedAt: '24m', status: 'ready', cwd: '/workspace/codex-webui', model: 'gpt-5.6-terra', contextPercent: 18 },
    { id: 'c3', projectId: 'p1', title: 'Codex session discovery', preview: 'Indexed 48 resumable local sessions.', updatedAt: 'Yesterday', status: 'ready', cwd: '/workspace/codex-webui', model: 'gpt-5.6-sol', contextPercent: 71 },
    { id: 'c4', projectId: 'p2', title: 'Fix clean import errors', preview: 'Validation completed in Godot 4.7.', updatedAt: 'Mon', status: 'ready', cwd: '/workspace/code-review-simulator', model: 'gpt-5.6-terra', contextPercent: 44 },
  ],
  files: [
    { id: 'f1', name: 'backend', path: 'backend', type: 'folder', children: [
      { id: 'f11', name: 'app', path: 'backend/app', type: 'folder', children: [
        { id: 'f111', name: 'main.py', path: 'backend/app/main.py', type: 'file', language: 'python', status: 'modified' },
        { id: 'f112', name: 'codex.py', path: 'backend/app/codex.py', type: 'file', language: 'python' },
      ] },
    ] },
    { id: 'f2', name: 'frontend', path: 'frontend', type: 'folder', children: [
      { id: 'f21', name: 'src', path: 'frontend/src', type: 'folder', children: [
        { id: 'f211', name: 'App.tsx', path: 'frontend/src/App.tsx', type: 'file', language: 'typescript', status: 'modified' },
        { id: 'f212', name: 'styles.css', path: 'frontend/src/styles.css', type: 'file', language: 'css', status: 'added' },
      ] },
      { id: 'f22', name: 'package.json', path: 'frontend/package.json', type: 'file', language: 'json' },
    ] },
    { id: 'f3', name: 'design', path: 'design', type: 'folder', children: [
      { id: 'f31', name: '_readme.md', path: 'design/_readme.md', type: 'file', language: 'markdown' },
    ] },
    { id: 'f4', name: 'specs', path: 'specs', type: 'folder', children: [
      { id: 'f41', name: '_readme.md', path: 'specs/_readme.md', type: 'file', language: 'markdown' },
    ] },
    { id: 'f5', name: 'compose.yaml', path: 'compose.yaml', type: 'file', language: 'yaml' },
    { id: 'f6', name: 'README.md', path: 'README.md', type: 'file', language: 'markdown', status: 'modified' },
  ],
  schedules: [
    { id: 's1', name: 'Morning repository health', prompt: 'Check dirty worktrees, failed CI, and stale branches.', cadence: 'Every day · 08:30', nextRun: 'Tomorrow, 08:30', enabled: true },
    { id: 's2', name: 'Weekly specs drift review', prompt: 'Compare specs with current implementation and report gaps.', cadence: 'Mondays · 10:00', nextRun: 'Monday, 10:00', enabled: true },
    { id: 's3', name: 'Dependency update check', prompt: 'List safe dependency updates. Do not apply them.', cadence: '1st of month', nextRun: 'Sep 1, 09:00', enabled: false },
  ],
  usage: { fiveHourPercent: 37, weeklyPercent: 62, lifetimeTokens: 2_066_100, peakDailyTokens: 348_200, currentStreakDays: 9, resetsAt: '1h 42m' },
  models: ['gpt-5.6-sol', 'gpt-5.6-terra'],
  images: [],
  demo: true,
  codexVersion: 'Demo value',
  updatesEnabled: false,
}

export const demoEvents: StreamEvent[] = [
  { id: 'e1', kind: 'message', role: 'user', content: 'Build the frontend shell with resumable chats, a live Codex event stream, and an IDE-style file browser.', timestamp: '17:41' },
  { id: 'e2', kind: 'reasoning', title: 'Approach', content: 'I’ll establish the application frame first, then connect the core session and workspace contracts. The UI remains useful if the local service is still starting.', timestamp: '17:41', state: 'done' },
  { id: 'e3', kind: 'command', title: 'Inspect workspace', content: 'rg --files frontend backend specs design | sort', timestamp: '17:42', state: 'done', meta: { exitCode: 0, duration: '86ms' } },
  { id: 'e4', kind: 'file', title: 'Frontend foundation', content: 'frontend/src/App.tsx\nfrontend/src/api.ts\nfrontend/src/styles.css', timestamp: '17:43', state: 'done', meta: { added: 412, removed: 0 } },
  { id: 'e5', kind: 'approval', title: 'Approval requested', content: 'Allow Codex to run `npm install` inside this workspace?', timestamp: '17:44', state: 'pending' },
  { id: 'e6', kind: 'message', role: 'assistant', content: 'The main workspace is in place. I’m tightening the responsive behavior and verifying the production build now.', timestamp: '17:45' },
]

export const demoFileContents: Record<string, string> = {
  'frontend/src/App.tsx': `import { useEffect, useState } from 'react'\nimport { api } from './api'\n\nexport default function App() {\n  const [sessions, setSessions] = useState([])\n\n  useEffect(() => {\n    api.sessions.list().then(setSessions)\n  }, [])\n\n  return <main>{/* Codex workspace */}</main>\n}\n`,
  'frontend/src/styles.css': `:root {\n  --canvas: #0d1110;\n  --panel: #141917;\n  --text: #edf3ef;\n  --accent: #87d4a6;\n}\n\n.workspace {\n  display: grid;\n  grid-template-columns: 280px minmax(420px, 1fr) 320px;\n}\n`,
  'README.md': `# Codex Web UI\n\nA local-first web workspace for Codex CLI.\n\n## Start\n\n\`docker compose up --build\`\n`,
}
