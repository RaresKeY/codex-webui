import type { MessageImage } from './types'

const rasterData = /^data:image\/(?:png|jpeg|gif|webp);base64,[A-Za-z0-9+/=\r\n]+$/
const localLibrary = /^\/api\/images\/[a-f0-9]{32}\.(?:png|jpg|gif|webp)$/

export function imageSource(source: string): string | undefined {
  if (!source || source.length > 28_000_000) return undefined
  if (rasterData.test(source) || localLibrary.test(source)) return source
  if (source.startsWith('/api/workspace/image?path=')) return source
  let path = source
  if (source.startsWith('file://')) {
    try {
      const url = new URL(source)
      if (url.hostname && url.hostname !== 'localhost') return undefined
      path = decodeURIComponent(url.pathname)
    } catch { return undefined }
  } else if (/^[a-z][a-z0-9+.-]*:/i.test(source) || source.startsWith('//')) return undefined
  return `/api/workspace/image?path=${encodeURIComponent(path)}`
}

export function contentImages(value: unknown): MessageImage[] {
  if (!Array.isArray(value)) return []
  return value.flatMap((raw, index) => {
    if (!raw || typeof raw !== 'object') return []
    const item = raw as Record<string, unknown>
    const type = String(item.type ?? '').toLowerCase()
    if (!['image', 'localimage', 'inputimage', 'input_image'].includes(type)) return []
    const source = item.path ?? item.url ?? item.imageUrl ?? item.image_url ?? (typeof item.data === 'string' ? `data:${item.mimeType};base64,${item.data}` : '')
    const url = typeof source === 'string' ? imageSource(source) : undefined
    return url ? [{ url, alt: typeof item.alt === 'string' ? item.alt : `Image ${index + 1}` }] : []
  }).slice(0, 16)
}
