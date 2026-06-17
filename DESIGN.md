# VibeLign Design System

## 1. Atmosphere & Identity

VibeLign feels like a practical command desk for non-expert builders: direct, high-contrast, and tactile. The signature is neo-brutalist utility: strong black outlines, warm paper surfaces, vivid action color, and dense controls that stay readable during repeated work.

## 2. Color

### Palette

| Role | Token | Light | Dark | Usage |
|------|-------|-------|------|-------|
| Surface/primary | --bg | #FEFBF0 | #1E2216 | App background |
| Surface/elevated | --white | #FFFFFF | #1A1A1A | Cards, modals, panels |
| Text/primary | --black | #1A1A1A | #FFFFFF | Primary text and outlines |
| Text/secondary | --gray-dark | #999999 | #D4D0C8 | Captions and secondary text |
| Border/default | --border | #1A1A1A | #FFFFFF | Strong outlines |
| Accent/primary | --primary | #F5621E | #FF8F5E | Primary actions and active states |
| Accent/secondary | --purple | #7B4DFF | #A78BFA | Secondary emphasis |
| Status/success | --green | #4DFF91 | #7DFF6B | Success states |
| Status/error | --red | #FF4D4D | #FF6B6B | Error and destructive states |
| Data/info | --blue | #4D9FFF | #8EC5FF | Informational marks |

### Rules

- Use black outlines as the main separation device.
- Reserve orange for primary actions and active navigation.
- Use accent colors as semantic markers, not decorative gradients.

## 3. Typography

### Scale

| Level | Size | Weight | Line Height | Tracking | Usage |
|-------|------|--------|-------------|----------|-------|
| H1 | 28px | 800 | 1.15 | 0 | Page titles |
| H2 | 20px | 700 | 1.2 | 0 | Panel and section headers |
| Body | 14px | 400 | 1.5 | 0 | Default UI text |
| Body/sm | 12px | 400 | 1.5 | 0 | Secondary text |
| Caption | 11px | 700 | 1.3 | 0.05em | Labels and badges |

### Font Stack

- Primary: "Space Grotesk", system-ui, sans-serif
- Mono: "IBM Plex Mono", ui-monospace, monospace
- Report output may use document-safe Korean stacks such as Pretendard, Apple SD Gothic Neo, and Noto Serif KR.

### Rules

- Letter spacing is 0 for body text.
- Uppercase labels may use positive tracking only.
- Body text should not drop below 12px inside dense tool surfaces.

## 4. Spacing & Layout

### Base Unit

All spacing derives from a base of 4px.

| Token | Value | Usage |
|-------|-------|-------|
| --space-1 | 4px | Tight inline spacing |
| --space-2 | 8px | Compact control spacing |
| --space-3 | 12px | Form and list padding |
| --space-4 | 16px | Card padding |
| --space-6 | 24px | Panel grouping |
| --space-8 | 32px | Page section breaks |

### Grid

- Work surfaces use split panes and constrained panels rather than marketing layouts.
- Fixed-format controls should have stable dimensions to avoid layout shift.

### Rules

- Use dense but scannable grouping.
- Do not nest cards inside cards.
- Keep toolbars and modal controls predictable over decorative.

## 5. Components

### Button

- Structure: native `button` with visible label or familiar icon.
- Variants: primary orange, black, white, danger, ghost, small.
- States: hover moves by 1-2px, active removes shadow, disabled lowers opacity.
- Accessibility: visible label or `aria-label`, keyboard focus preserved.

### Card

- Structure: white surface, black border, hard offset shadow.
- Usage: repeated items, modals, and framed tools only.
- Depth: hard shadow, not soft blur.

### Modal

- Structure: elevated white panel over dim overlay.
- Usage: focused decisions and exports.
- Accessibility: role dialog and labeled controls.

## 6. Motion & Interaction

| Type | Duration | Easing | Usage |
|------|----------|--------|-------|
| Micro | 60ms | cubic-bezier(.2, 0, 0, 1) | Button press |
| Pop | 140ms | cubic-bezier(.2, 0, 0, 1) | Badges and small reveals |

### Rules

- Animate transform and box-shadow only for existing brutalist controls.
- Never animate layout dimensions.
- Keep interactions immediate; avoid slow decorative transitions.

## 7. Depth & Surface

### Strategy

Mixed, with black borders and hard offset shadows as the primary depth language.

| Level | Value | Usage |
|-------|-------|-------|
| Default border | 2px solid var(--black) | Cards, buttons, modals |
| Small shadow | 2px 2px 0 var(--black) | Compact controls |
| Default shadow | 4px 4px 0 var(--black) | Cards and primary buttons |
| Large shadow | 6px 6px 0 var(--black) | Hover emphasis |
