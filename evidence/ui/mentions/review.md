# Effort labels and combined mentions — 2026-10-05

VERDICT: APPROVE for the requested local source and image changes.

## Scope

Reviewed the composer, assistant message labels, native catalog adapter, routed submission and bounded selection persistence. Production Firefox checks cover 1440×1000 and 390×844; keyboard selection and dense scrolling were exercised on desktop, with narrow menu geometry checked on phone. The existing neutral layout, exact ask preservation, Jev → acknowledged settings → turn ordering, eight-selection limit and credential/workspace boundaries are retained. Existing unrelated changes were preserved.

## Findings and changes

1. Assistant labels lacked effort, and native history does not expose it per turn. Ordered model notifications now include effort; successful WebUI turns save only native IDs/model/effort. Hydration restores matching labels, while old/unrecorded effort stays explicitly unknown. Later selections do not relabel earlier messages.
2. The composer exposed only plugins. `@`/`$` now search enabled skills, available plugins, callable apps and rooted fuzzy files. Selection inserts native invocation text; fresh backend resolution adds supported skill/app/plugin inputs after the unchanged ask. File references remain text, with protected paths and symlink escapes rejected.
3. Catalog edge cases hid otherwise useful entries or failed for unopened history. Valid skills survive unrelated parse failures; category errors remain visible. Unloaded app discovery uses the global snapshot, and selected apps are loaded/revalidated against effective thread configuration before Jev runs.
4. Long menus needed keyboard visibility and coherent controls. Twelve suggestions are interleaved across categories, the active option scrolls into view, controls retain 44 px minimum height, and the menu reuses the existing neutral scrollbar and selected state.
5. Optional selection storage must not cause duplicate execution or hide history. SQLite write failure after turn acknowledgement preserves successful submission; read failure preserves native history without guessed labels.

No remaining actionable finding was identified in this scope after the fixes and final checks.

## Verification

- `./tools/build-image.sh`: frontend TypeScript, production build and lint passed; **64 frontend tests**, **121 backend tests**. Runtime tests ran with network disabled and no credential mounts.
- The packaged standalone 0.160.0 binary passed `tools/check_thread_lifecycle.py`: a disposable project skill, installed plugin/app catalogs, rooted fuzzy file search, legacy creation/history and real settings acknowledgements for both routing models. Only paid routing/inference transports were mocked for the full send.
- `python3 tools/check_browser.py --output-dir evidence/ui/mentions`: both viewports passed with zero uncaught JavaScript errors and no horizontal overflow. Checks cover native skill/app/plugin/file selection metadata, deleted selection retention, exact padded asks, historical Luna/medium versus live Sol/low, dense keyboard scrolling, existing navigation/image/context behavior, and failure-draft retention.
- `git diff --check`: passed.
- Earlier matched layout evidence remains in `../code-review/`; the new menu/labels are captured in `desktop-all-mentions.png`, `desktop-mentions-keyboard.png`, `desktop.png` and `phone-plugins.png`. `checks.json` records the fixture checks.
- Current candidate image: `localhost/codex-webui-2:local`, SHA-256 `4ff6223cec8243c49a192b1fab88866181fbf6b8464007d1c7322844bba1c375`.

## Unverified

Paid Jev/Codex inference, real skill/plugin/connected-app execution, complete CLI feature parity, live microphone/audio, touch gestures, full accessibility coverage and ARM64. Native offline app discovery validates an empty runtime snapshot, not an authenticated connector session. Old/native external turns cannot gain an effort label without recorded metadata. Selection retention and fork copying remain documented gaps.

The existing running container remains healthy on image `7fabc199e785847f2c00d7b4e3b61b2707a45f2319e356c490a56c85607add73`; it was not restarted during this side conversation. The new source and image are local and uncommitted.
