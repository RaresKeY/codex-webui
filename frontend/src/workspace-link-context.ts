import { createContext } from 'react'

export const WorkspaceLinkContext = createContext<((path: string) => void) | null>(null)
