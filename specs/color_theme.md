# Shared color theme

`frontend/src/theme.css` owns the reusable dark-theme palette. `styles.css` imports it before typography, layout and component rules; the separate conversation and Jev styles consume the same inherited variables. Keep existing token names as the public styling contract. Add a token for a recurring semantic role, and reuse it instead of copying a hex value into component rules.

| Role | Tokens and behavior |
| --- | --- |
| Base surfaces | `--canvas`, `--sidebar`, `--sidebar-rail`, `--surface-inset`, `--surface-field`, `--panel`, `--panel-raised` |
| Interaction surfaces | `--panel-hover`, `--sidebar-hover`, `--surface-selected`, `--surface-pressed`, and control hover/selected/disabled tokens |
| Structure and focus | `--line`, `--line-soft`, `--line-control`, `--line-strong`, `--line-focus`, `--line-focus-soft` |
| Text | `--text`, `--muted`, `--subtle`, secondary/label/control/inverse text and muted icon tokens |
| Semantic colors | Existing accent, danger, warning and blue roles, plus reusable link, unread and destructive-action colors |
| Translucent treatments | Shared scrim, shadow, highlight and focus-glow tokens |

`--surface-header` aliases `--sidebar` (`#1c1c1c`). Markdown tables and code headers use this neutral surface, with shared neutral text/borders. Markdown headings, quotations and inline code also use the palette; link blue remains intentional. Table alignment, Markdown rendering, horizontal scrolling, code copying and the current font/spacing rules are unchanged. Sidebar surfaces are defined once rather than repeated through later overrides. The former undefined `--surface` reference uses `--panel`.

Verification: `tools/check_browser.py --theme-only` renders generic Markdown in the production bundle at 1440×1000, 390×844 and 320×640. It measures neutral headers/borders, shared sidebar/header fill, text contrast, contained table scrolling, disabled send and keyboard copy focus, with no prompt submission. A supplied `--baseline-bundle` captures matched prior styling without running the historical feature baseline. Evidence is under `evidence/ui/color-tokens/`.

## Integrated pane presentation

Context pane chrome now uses the canvas and existing neutral divider/selection tokens. It has square outer edges, no floating shadow, compact title typography and neutral tool tabs. Jev records use simple separators instead of nested rounded cards; browser chrome follows the same neutral surfaces.

## Gaps

- Individual legacy context/tool/status treatments and illustration colors remain with their owners; this pass consolidates recurring shared colors and neutral Markdown chrome.
- Only the current dark theme is implemented. Token reuse does not claim a complete theme-switching API, accessibility audit or physical-device coverage.
