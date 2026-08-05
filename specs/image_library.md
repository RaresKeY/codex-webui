# Image library

The current library is a flat filesystem collection under `/data/images`, not a database index. `backend/app/main.py` lists, serves, uploads, and deletes files with generated 32-hex-character IDs. Uploads accept signature-detected PNG, JPEG, GIF, and WebP up to 20 MiB. The frontend imports, refreshes, displays, filters by displayed name, and deletes live items. Original upload names are returned for the immediate response but are not persisted across refresh.

Formats are checked by magic bytes, not fully decoded. There are no dimension/decode-cost checks, thumbnails, hashes, tags, project associations, workspace indexing, composer attachment, or generated-image event import. Delete removes the app-owned bytes immediately.

## Gaps

- Persist useful original names/metadata so search remains meaningful after refresh, and surface upload/delete failures.
- Add full safe decode/dimension bounds, metadata/indexing, thumbnails, association, attachment, and recovery/trash behavior.
