# Image library

The current library is a flat filesystem collection under `/data/images`, not a database index. `backend/app/main.py` lists, serves, uploads, and deletes files with generated 32-hex-character IDs. Uploads accept signature-detected PNG, JPEG, GIF, and WebP up to 20 MiB. The frontend imports, refreshes, displays, filters by displayed name, and deletes live items. Original upload names are returned for the immediate response but are not persisted across refresh.

Formats are checked by magic bytes, not fully decoded. There are no dimension/decode-cost checks, thumbnails, hashes, tags, project associations, workspace indexing, composer attachment, or generated-image byte import. Delete removes the app-owned bytes immediately.

The library loads when opened and shows load/import/delete errors. Transcript image previews and a click-to-zoom native dialog cover user images, generated/viewed images, tool raster content and Markdown local image paths. `GET /api/workspace/image?path=...` applies the existing rooted path policy, signature validation and size cap, and reads bytes off the event loop. Remote/SVG images and file-ID-only inputs remain unavailable; generated previews are not copied into the imported-files directory. The Images page additionally discovers native user/generated/viewed/tool images and common inline Markdown local images from up to 100 loaded recent conversations. It reads history with three cancellable workers, progressively displays results, deduplicates within a conversation and includes current chat events immediately. Chat cards link back to the source conversation; only imported files can be deleted. Filters distinguish chat and imported images. Scan progress and unavailable-history counts remain visible, with explicit Refresh to retry. No resume or inference is requested during discovery. Relative paths are resolved against each conversation cwd and previews retain rooted backend access checks. See `chat_interactions.md`.

Verification: `frontend/src/chat-images.test.ts` tests source links, native image extraction, deduplication, relative paths and remote/code-example exclusion. Production Firefox fixtures exercise decoded chat thumbnails and return navigation (`evidence/ui/gallery-sidebar/`).

## Gaps

- Chat discovery is limited to the loaded recent-history list (at most 100), is rebuilt on opening/refresh, and does not index archived conversations. Inline Markdown extraction covers simple image syntax; reference-style images and complex Markdown destinations remain unindexed. Missing/outside-root source files and file-ID-only remote assets cannot be previewed.
- Persist useful original names/metadata so search remains meaningful after refresh.
- Add full safe decode/dimension bounds, metadata/indexing, thumbnails, association, attachment, and recovery/trash behavior.
