# Streamlit Design System — extracted component reference

Source: [Streamlit Design System (Community)](https://www.figma.com/design/IZHqj7ZUjkUFYQFQ5bPNKd/Streamlit-Design-System--Community-)
File key: `IZHqj7ZUjkUFYQFQ5bPNKd`

Extracted via the Figma MCP (`get_design_context` / `get_metadata` / `get_variable_defs`). The
plan's tool-call limit was hit partway through, so `st.button` variants are listed from metadata
only (names/dimensions/ids), without full generated markup. Re-run `get_design_context` on the
node IDs below to pull them in when more calls are available.

## File map (top-level pages)

| Page | Node ID | Contents |
|---|---|---|
| 🚀 Streamlit Design System cover | `5322:0` | Marketing cover frame showing components in a mock app layout |
| 💡 Material icon library | `2048:81911` | Icon set (Material icons, used across widgets) |
| ☎️ Button | `2040:18553` | `st.button`, `st.download_button` |
| 🧮 Numeric | `2137:97812` | `st.number_input`, `st.slider` |
| 💬 Chat elements | `2324:43791` | `st.chat_input`, `st.chat_message`, file/send/spinner sub-components |
| ✅ Status - call outs | `2344:38612` | `st.success`, `st.info`, `st.warning`, `st.error` |

Every category page follows the same layout template (see "Shared page layout" below).

## Design tokens

See `tokens.json` / `tokens.css` in this folder. Pulled from `get_variable_defs` on
`2137:98007` (light theme only — dark theme wasn't re-pulled before the rate limit hit).

## Components

### `st.number_input` — node `2137:98007` (symbol set), base state `2137:98008`
32 variants across: `Hover`, `Selected`, `Disabled`, `Theme` (Light/Dark), `Side bar`,
`Border`, `Chosen option`. Structure: label row (with optional `Help` tooltip icon) above an
input pill (`bg: --sds-color-background-secondary`, `radius: --sds-border-radius`) containing
value/placeholder text and trailing erase/increment icons.

### `st.slider` — node `2137:98889` (symbol set), base state `2137:98890`
8 variants across: `Disabled`, `Theme` (Light/Dark), `Sidebar`. Structure: label row with
`Help` tooltip, then a track (two `<img>` line segments either side of a value bubble showing
the current value in `--sds-color-primary`), then a min/max row underneath.

### `st.chat_input` — node `2324:43836` (symbol set), base state `2324:43837`
14 variants across: `Hover`, `File`, `Drag&Drop`, `Multiple files`, `Theme`, `Disabled`, `Focus`.
Pill-shaped input (`radius: 200px`, `bg: --sds-color-widget`) with an `AttachFile` icon, a
divider, placeholder/question text, and a `Send` icon button (has its own hover/activated states).
Sub-components in the same section: `Files` (attachment chip, node `2324:44014`), `Send` (node
`2324:44062`), `spinner` (19-frame loading animation, node `2324:44069`), `attach_file` (node
`2324:45389`).

### `st.chat_message` — node `2344:36392` (symbol set), base state `2344:36391`
4 variants across: `User` (User 1/User 2), `Theme`. Avatar icon + content column; content can
hold arbitrary child elements — the extracted instance embeds a full `st.bar_chart` (see below).

### `st.bar_chart` (embedded instance inside `st.chat_message`, node `I2344:36246;2048:6935` etc.)
Bar chart built from absolutely-positioned `<div>` bars, not an image — axis labels, gridlines,
legend swatches and bars are all real DOM nodes. Colors used: `--sds-color-chart-blue-40`
(`#83c9ff`) and `--sds-color-chart-blue-80` (`#0068c9`) for the two series.

### `st.success` / `st.info` / `st.warning` / `st.error` — status banners
Same structure, different tokens:

| Component | Node (light) | bg token | text token | icon | emoji |
|---|---|---|---|---|---|
| `st.success` | `2344:39935` | `--sds-color-success-bg` | `--sds-color-success-text` | check_circle_outline | ✅ |
| `st.info` | `2368:31558` | `--sds-color-info-bg` | `--sds-color-info-text` | info | 🫐 |
| `st.warning` | `2368:31714` | `--sds-color-warning-bg` | `--sds-color-warning-text` | warning_amber | ⚠️ |
| `st.error` | `2368:31952` | `--sds-color-error-bg` | `--sds-color-error-text` | error_outline | 🛑 |

All four: `display:flex; gap:8px; align-items:center; padding:16px; border-radius: --sds-border-radius; width:704px` (704px is the fixed widget column width used throughout the system — see layout notes). Each has a light/dark theme variant.

### `st.button` — node `2061:46064` (symbol set) — **metadata only, not yet code-extracted**
Variants across: `Theme` (Light mode/Dark Mode), `Disabled`, `Focus`, `Hover`, `Primary`,
`Secondary`, `Pressed`. Representative node IDs:
- Primary, light, default: `2061:46086`
- Secondary, light, default: `2061:46072`
- Primary, dark, default: `2061:46079`
- Secondary, dark, default: `2061:46065`

Sibling component in the same page: `st.download_button` (page `2040:18553`, frame `2061:46064`
area, base instance `2061:53761`) and `st.button_download` (frame `2061:53048`).

## Shared page layout (applies to every component-category page)

Each Figma page in this file is built from a repeated template — worth mirroring if you build a
docs/style-guide screen in the app:

```
.Page Header        — small "section" label (e.g. "Numeric") + library logo/wordmark, 120px tall
Page
 ├─ .Page Title      — component name (H1) + description text + a `st.code` snippet block
 ├─ .Seperator       — horizontal divider, 128px vertical rhythm
 ├─ .Spacer          — 32px blank
 ├─ .Section Header  — "Playground" section label
 ├─ Wrapper           — single live instance of the component, centered
 ├─ .Seperator / .Section Header — "Properties" section with a 3-column header row
 │                        (Property | Type | Description) built from `Pills` tag components
 └─ Frame 427318175  — repeated `Row Wrapper` rows: one row per prop, each row = a `Pills`
                        label pair on the left + a live component instance on the right
                        showing that prop's effect (e.g. every number_input row shows the
                        widget re-rendered with one property toggled)
```

The `Pills` component (small rounded-rectangle tag/badge, ~28px tall) is reused everywhere as
both the section-header column labels and the per-row property tags.

Column widths recur across pages: `1656px` page column, `1464px` content width, `704px` widget
width in the "no sidebar" state, `272px` widget width in the "sidebar" state — i.e. the kit
designs every widget for exactly two contexts, a full-width main area and a narrower sidebar.

## Known limitations of this extraction

- Icons/images came back as **7-day expiring Figma asset URLs** (`https://www.figma.com/api/mcp/asset/...`).
  None were downloaded — if you want to actually ship these icons, either re-fetch and download
  them before they expire, or swap in your own icon set (most are standard Material icons, e.g.
  `check_circle_outline`, `info`, `warning_amber`, `error_outline`, `attach_file`, `send`).
- Dark-theme token values are placeholders (see note in `tokens.css`), not pulled from Figma.
- `st.button` variants and the `💡 Material icon library` / `🚀 cover` pages were only mapped via
  metadata, not run through `get_design_context` — the Figma MCP Starter-plan rate limit was hit
  mid-extraction. Node IDs above are enough to resume with `get_design_context` later.
