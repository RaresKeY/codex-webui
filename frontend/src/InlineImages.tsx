import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { X } from 'lucide-react'
import type { MessageImage } from './types'

function ImageViewer({ image, onClose }: { image: MessageImage; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null)
  useEffect(() => { if (!dialog.current?.open) dialog.current?.showModal() }, [])
  return <dialog ref={dialog} className="image-viewer" aria-label={image.alt} onClose={onClose} onClick={event => { if (event.target === event.currentTarget) dialog.current?.close() }}>
    <button className="icon-button image-viewer-close" type="button" aria-label="Close image" onClick={() => dialog.current?.close()}><X size={22} /></button>
    <img src={image.url} alt={image.alt} />
  </dialog>
}

export function InlineImages({ images }: { images: MessageImage[] }) {
  const [active, setActive] = useState<MessageImage | null>(null)
  const [unavailable, setUnavailable] = useState<string[]>([])
  return <span className="inline-images">
    {images.map((image, index) => unavailable.includes(image.url)
      ? <span className="image-unavailable" key={index}>{image.alt} · Image unavailable</span>
      : <button type="button" className="inline-image" key={index} aria-label={`View ${image.alt}`} onClick={event => { event.currentTarget.focus(); setActive(image) }}><img src={image.url} alt={image.alt} loading="lazy" referrerPolicy="no-referrer" onError={() => setUnavailable(current => [...current, image.url])} /></button>)}
    {active && createPortal(<ImageViewer image={active} onClose={() => setActive(null)} />, document.body)}
  </span>
}
