# Design System Specification (DESIGN.md)
*F-Commerce Order Extractor — Senior Front-End Architecture & UI/UX Standards*

---

## 1. System Vision & Philosophy

OrderDesk is a specialized commerce operating desk tailored for Bangladeshi social commerce merchants and their buyers. The interface eliminates conversational back-and-forth by transforming chaotic Messenger chat transcripts into crystal-clear, structured order ledgers and one-click shareable checkout pages.

### Core Tenets
1. **Tool, Not Marketing:** Clean, high-density utility inspired by developer instruments (Linear, Raycast) rather than generic SaaS landing pages.
2. **Authentic Craft (Anti-AI-Slop):** Zero artificial AI tropes — no glowing neon gradients, no cards nested inside cards, no tracked uppercase eyebrows, and no fake status dots.
3. **Tactile Interaction:** Every button press, toggle, input focus, and toast message responds with sub-200ms spring physics and optical concentricity.
4. **Resilient Dual-Audience Usability:**
   - **Seller Workspace:** High-density, keyboard-friendly data entry with tabular figures and clear inventory counters.
   - **Buyer Portal:** Frictionless mobile-first checkout with bilingual clarity (Bangla + English), cash-on-delivery certainty, and live delivery timeline.

---

## 2. Design Tokens Architecture (`frontend/tokens.css`)

### 2.1 Perceptual Color Palette (OKLCH)

```css
:root {
  /* Surfaces & Canvas */
  --color-paper:        oklch(17% 0.008 250);   /* Root application canvas */
  --color-paper-2:      oklch(21% 0.009 250);   /* Elevated panel surface */
  --color-paper-3:      oklch(13.5% 0.007 250); /* Recessed inputs & wells */
  --color-paper-hover:  oklch(24% 0.010 250);   /* Interactive hover state */

  /* Inks & Typography */
  --color-ink:          oklch(95% 0.005 250);   /* Primary high-contrast text */
  --color-ink-2:        oklch(83% 0.008 250);   /* Body secondary text */
  --color-muted:        oklch(71% 0.010 250);   /* Captions, labels, placeholders */

  /* Structural Rules & Borders */
  --color-rule:         oklch(31% 0.010 250);   /* Hairline container dividers */
  --color-rule-2:       oklch(42% 0.012 250);   /* Active state borders & spine */

  /* Primary Accent & Signal */
  --color-accent:       oklch(82% 0.150 80);    /* Warm amber (human action / primary) */
  --color-accent-ink:   oklch(18% 0.040 75);    /* High-contrast ink on amber */
  --color-accent-soft:  oklch(29% 0.050 80);    /* Soft amber pill background */
  --color-focus:        oklch(82% 0.150 80);    /* 2px instant focus ring */

  /* Order Lifecycle Semantic Signals */
  --color-cool:         oklch(77% 0.120 245);   /* Confirmed status (Slate blue) */
  --color-cool-soft:    oklch(29% 0.050 245);
  --color-packed:       oklch(78% 0.130 290);   /* Packed status (Violet) */
  --color-packed-soft:  oklch(27% 0.050 290);
  --color-shipped:      oklch(78% 0.120 195);   /* Shipped status (Teal) */
  --color-shipped-soft: oklch(27% 0.050 195);
  --color-ok:           oklch(76% 0.150 150);   /* Delivered / Success (Emerald) */
  --color-ok-soft:      oklch(24.5% 0.030 150);
  --color-bad:          oklch(70% 0.170 25);    /* Cancelled / Error (Coral red) */
  --color-bad-soft:     oklch(24.5% 0.035 25);
  --color-returned:     oklch(74% 0.160 10);    /* Returned status (Rose) */
  --color-returned-soft:oklch(25% 0.040 10);
}
```

---

## 3. Typography & Numerical Precision

### 3.1 Typeface Selection
- **Interface Reading:** `Host Grotesk` (weights 400, 500, 600) — Calm, humanist sans with balanced optical geometry.
- **Data & Measurement:** `Atkinson Hyperlegible Mono` (weights 400, 500) — Distinctive slashed zeroes, tailed numerals, and tabular alignment designed for extreme legibility under rapid order scanning.

### 3.2 Modular Scale & Rules
- `h1`: `1.5rem` / `line-height: 1.15` / `letter-spacing: -0.025em` / `text-wrap: balance`
- `h2`: `1.125rem` / `line-height: 1.2` / `letter-spacing: -0.015em` / `text-wrap: balance`
- `h3`: `1.0rem` / `line-height: 1.25` / `font-weight: 500`
- `body`: `1.0rem` (16px) / `line-height: 1.5` / `color: var(--color-ink-2)`
- `captions / labels`: `0.875rem` (14px) / `font-weight: 500` / `color: var(--color-muted)` / sentence-case
- **Tabular Figures:** All financial figures, order IDs, phone numbers, and timestamps strictly enforce `font-variant-numeric: tabular-nums;`.

---

## 4. Spacing, Geometry & Concentric Radii

### 4.1 Strict 4px Spacing Grid
All paddings, margins, gaps, and hit heights follow the geometric 4px scale:
`4px (2xs) · 8px (xs) · 12px (sm) · 16px (md) · 20px · 24px (lg) · 32px (xl) · 48px (2xl) · 64px (3xl)`

### 4.2 Concentric Radii Formula
Nested rounded elements maintain optical harmony:
$$\text{Outer Radius} = \text{Inner Radius} + \text{Padding}$$
- Card Panels: `radius: 10px` with `padding: 24px`
- Inputs & Controls: `radius: 6px` with `padding: 0 12px`
- Interactive Pills / Badges: `radius: 4px` with `padding: 3px 8px`
- Action Buttons: `radius: 6px` with `height: 36px`

---

## 5. Component Interaction & State Engine

Every interactive primitive enforces all 8 standard states:

1. **Default:** Subtly recessed or framed surface with 1px hairline border.
2. **Hover:** Surface lightness shift (`+3% lightness`), border tint to `--color-rule-2`.
3. **Focus-Visible:** Instant 2px `--color-focus` outline with 2px offset (zero transition delay).
4. **Active (Pressed):** Tactile `transform: scale(0.98) translateY(1px)` for immediate physical feedback.
5. **Loading:** Disabled pointer, button text hidden or accompanied by smooth 16px CSS spinner.
6. **Disabled:** Native `disabled` attribute + `opacity: 0.55; cursor: not-allowed;`.
7. **Error / Invalid:** Hairline border in `--color-bad`, focused ring turns coral.
8. **Success:** Toast notification confirmation (`✓ Copied!`, `✓ Saved`) auto-cleared in 2200ms.

---

## 6. Layout & Responsive Architecture

### 6.1 Desktop Grid (&ge; 900px)
- **Navigation:** Persistent left navigation rail (240px) with brand anchor, active section pill, seller session identifier, and logout.
- **Main Desk:** Split two-column layout:
  - Left column (340px): Search bar, status filter dropdown, scrollable order cards queue.
  - Right column (flex 1): Order review workspace, chat extractor drawer, line-items ledger, buyer contact fields, courier dispatch, and history audit trail.

### 6.2 Mobile Layout (&le; 900px)
- Single-column linear flow.
- Sidebar collapses into top utility bar.
- Stats row wraps to 2&times;2 grid.
- **Buyer Checkout Inversion:** On mobile viewports (&le;650px), the Order Summary Card strictly leads at the top (`order: 1`), followed by the delivery address input form (`order: 2`), ensuring the buyer immediately validates what they are paying for before entering address details.
- Minimum touch target: &ge;44&times;44px on all buttons and tap surfaces.
