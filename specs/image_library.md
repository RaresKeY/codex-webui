# Image library

The current library is a flat filesystem collection under `/data/images`, not a database index. `backend/app/main.py` lists, serves, uploads, and deletes files with generated 32-hex-character IDs. Uploads accept signature-detected PNG, JPEG, GIF, and WebP up to 20 MiB. The frontend imports, refreshes, displays, filters by displayed name, and deletes live items. Original upload names are returned for the immediate response but are not persisted across refresh.

Formats are checked by magic bytes, not fully decoded. There are no dimension/decode-cost checks, thumbnails, hashes, tags, project associations, workspace indexing, composer attachment, or generated-image event import. Delete removes the app-owned bytes immediately.

The library loads when opened and shows load/import/delete errors. Transcript image previews and a click-to-zoom native dialog cover user images, generated/viewed images, tool raster content and Markdown local image paths. `GET /api/workspace/image?path=...` applies the existing rooted path policy, signature validation and size cap, and reads bytes off the event loop. Remote/SVG images and file-ID-only inputs remain unavailable; generated previews are not automatically saved into the library. See `chat_interactions.md`.

## Gaps

- Persist useful original names/metadata so search remains meaningful after refresh.
- Add full safe decode/dimension bounds, metadata/indexing, thumbnails, association, attachment, and recovery/trash behavior.
