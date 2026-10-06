import { useEffect, useRef, useState, type Dispatch, type SetStateAction } from 'react'
import { AlertCircle, ChevronDown, ChevronRight, Copy, File, Folder, RefreshCw, Save, Search, X } from 'lucide-react'
import { loadFile, loadWorkspaceTree, saveFile } from './api'
import type { WorkspaceFile } from './types'
import './workspace-file-view.css'

export interface FileDraft { content: string; saved: string }
export type FileDrafts = Record<string, FileDraft>
export interface FileOpenRequest { path: string; id: number }

function TreeEntry({ file, selected, query, onOpen, demo }: { file: WorkspaceFile; selected: string | null; query: string; onOpen: (path: string) => void; demo: boolean }) {
  const [expanded, setExpanded] = useState(false)
  const [children, setChildren] = useState(file.children)
  const fetched = useRef(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const mounted = useRef(true)
  useEffect(() => { mounted.current = true; return () => { mounted.current = false } }, [])
  const folder = file.type === 'folder'
  if (query && !folder && !file.name.toLowerCase().includes(query)) return null
  const toggle = () => {
    if (!folder) { onOpen(file.path); return }
    setExpanded(value => !value)
    if (fetched.current || loading || demo) return
    setLoading(true); setError('')
    void loadWorkspaceTree(file.path).then(value => { if (mounted.current) { setChildren(value); fetched.current = true } }).catch(() => { if (mounted.current) setError('Could not load folder. Close and reopen to retry.') }).finally(() => { if (mounted.current) setLoading(false) })
  }
  return <div className="workspace-tree-entry"><button type="button" className={`tree-row ${file.path === selected ? 'active' : ''}`} title={file.path} aria-expanded={folder ? expanded : undefined} onClick={toggle}>{folder ? expanded ? <ChevronDown size={13} /> : <ChevronRight size={13} /> : <span className="tree-spacer" />}{folder ? <Folder size={14} /> : <File size={14} />}<span>{file.name}</span></button>{expanded && <div className="workspace-tree-children">{loading && <small>Loading…</small>}{error && <small role="alert">{error}</small>}{children?.map(child => <TreeEntry key={child.path} file={child} selected={selected} query={query} onOpen={onOpen} demo={demo} />)}</div>}</div>
}

export function WorkspaceFileView({ cwd, request, demo, drafts, setDrafts }: { cwd: string; request: FileOpenRequest | null; demo: boolean; drafts: FileDrafts; setDrafts: Dispatch<SetStateAction<FileDrafts>> }) {
  const [path, setPath] = useState<string | null>(request?.path ?? null)
  const [identity, setIdentity] = useState(request?.path ?? '')
  const [tree, setTree] = useState<WorkspaceFile[]>([])
  const [treeError, setTreeError] = useState('')
  const [query, setQuery] = useState('')
  const [firstLine, setFirstLine] = useState(0)
  const [content, setContent] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [saveError, setSaveError] = useState('')
  const [saving, setSaving] = useState(false)
  const savingRef = useRef(false)
  const activePath = useRef(path)
  activePath.current = path
  const [treeVersion, setTreeVersion] = useState(0)
  const editor = useRef<HTMLTextAreaElement>(null)
  const gutter = useRef<HTMLDivElement>(null)
  useEffect(() => { if (request) setPath(request.path) }, [request])
  useEffect(() => {
    let disposed = false
    setTree([]); setTreeError('')
    void loadWorkspaceTree(cwd).then(items => { if (!disposed) setTree(items) }).catch(() => { if (!disposed) setTreeError('Files could not be loaded. Use Refresh to retry.') })
    return () => { disposed = true }
  }, [cwd, treeVersion])
  useEffect(() => {
    let disposed = false
    setFirstLine(0); setIdentity(path ?? ''); setContent(''); setError(''); setSaveError(''); setLoading(Boolean(path))
    if (path) void loadFile(path, demo).then(result => {
      if (disposed) return
      setIdentity(result.path ?? path); setContent(result.content); setError(result.error ?? ''); setLoading(false)
      if (!result.error) requestAnimationFrame(() => { if (!disposed) editor.current?.focus() })
    })
    return () => { disposed = true }
  }, [path, demo])
  const draft = path ? drafts[identity] : undefined
  const text = draft?.content ?? content
  const lineCount = text.split('\n').length
  const visibleStart = Math.min(firstLine, Math.max(0, lineCount - 1))
  const dirty = draft !== undefined && draft.content !== draft.saved
  const name = path?.split('/').filter(Boolean).at(-1) ?? ''
  const save = () => {
    if (demo || !path || !dirty || savingRef.current || error || loading) return
    const savedPath = path, savedIdentity = identity, savedText = text
    savingRef.current = true; setSaving(true); setSaveError('')
    void saveFile(savedPath, savedText).then(() => {
      if (activePath.current === savedPath) setContent(savedText)
      setDrafts(current => {
        const item = current[savedIdentity]
        if (!item) return current
        if (item.content !== savedText) return { ...current, [savedIdentity]: { ...item, saved: savedText } }
        const next = { ...current }; delete next[savedIdentity]; return next
      })
    }).catch(reason => { if (activePath.current === savedPath) setSaveError(reason instanceof Error ? reason.message : 'File could not be saved.') }).finally(() => { savingRef.current = false; setSaving(false) })
  }
  return <section className="workspace-file-view" role="tabpanel" id="context-tool-explorer" aria-label="Explorer">
    <div className="workspace-file-tabs">{path ? <div className="workspace-file-tab"><File size={14} /><span title={path}>{name}</span>{dirty && <span aria-label="Unsaved changes">•</span>}<button type="button" className="icon-button" title="Close file" aria-label="Close file" onClick={() => setPath(null)}><X size={14} /></button></div> : <span>Files</span>}</div>
    <div className="workspace-file-layout"><div className="workspace-file-main">
      {path && <nav className="workspace-breadcrumbs" aria-label="File path" title={path}>{path.split('/').filter(Boolean).map((part, index) => <span key={index}>{index > 0 && <ChevronRight size={12} />}{part}</span>)}</nav>}
      {saveError && <p className="workspace-file-error" role="alert">{saveError}</p>}
      {!path ? <div className="context-empty"><File size={24} /><strong>Select a file</strong><span>Open a chat file link or choose a file from the tree.</span></div> : loading ? <div className="context-empty" role="status">Loading file…</div> : error ? <div className="context-empty error" role="alert"><AlertCircle size={24} /><strong>File unavailable</strong><span>{error}</span></div> : <div className="workspace-numbered-editor"><div className="workspace-line-numbers" ref={gutter} aria-hidden="true"><div className="workspace-line-number-track" style={{ height: lineCount * 22 + 28 }}>{Array.from({ length: Math.min(120, lineCount - visibleStart) }, (_, offset) => { const index = visibleStart + offset; return <div className="workspace-line-number" key={index} style={{ top: index * 22 + 4 }}>{index + 1}</div> })}</div></div><textarea ref={editor} value={text} wrap="off" spellCheck={false} aria-label={`Edit ${name}`} onScroll={event => { if (gutter.current) gutter.current.scrollTop = event.currentTarget.scrollTop; setFirstLine(Math.floor(event.currentTarget.scrollTop / 22)) }} onKeyDown={event => { if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') { event.preventDefault(); save() } }} onChange={event => { const value = event.target.value; if (path) setDrafts(current => ({ ...current, [identity]: { content: value, saved: current[identity]?.saved ?? content } })) }} /></div>}
    </div><aside className="workspace-file-tree" aria-label="File browser"><div className="workspace-file-actions"><button type="button" className="icon-button" title="Copy file path" aria-label="Copy file path" disabled={!path} onClick={() => { if (path) void navigator.clipboard?.writeText(path).catch(() => undefined) }}><Copy size={15} /></button><button type="button" className="button" title="Save file · Ctrl/⌘ S" onClick={save} disabled={!dirty || saving || loading || Boolean(error) || demo}><Save size={14} />{saving ? 'Saving…' : 'Save'}</button><button type="button" className="icon-button" title="Refresh files" aria-label="Refresh files" onClick={() => setTreeVersion(value => value + 1)}><RefreshCw size={14} /></button></div><div className="workspace-tree-root" title={cwd}><Folder size={14} /><span>{cwd.split('/').filter(Boolean).at(-1) || 'Workspace'}</span></div><label className="workspace-file-filter"><Search size={13} /><input aria-label="Filter files" placeholder="Filter files…" value={query} onChange={event => setQuery(event.target.value)} /></label>{treeError && <p className="workspace-file-error" role="alert">{treeError}</p>}<div className="workspace-file-tree-scroll">{tree.map(file => <TreeEntry key={`${treeVersion}:${file.path}`} file={file} selected={identity} query={query.toLowerCase()} onOpen={setPath} demo={demo} />)}</div></aside></div>
  </section>
}
