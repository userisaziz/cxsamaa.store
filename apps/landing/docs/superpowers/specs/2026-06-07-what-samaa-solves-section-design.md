# WhatSamaaSolvesSection — Single-Column Redesign

**Date:** 2026-06-07
**File:** `src/sections/WhatSamaaSolvesSection.tsx`
**Status:** Approved (pending spec review)

## Goal

Redesign the "What SAMAA Solves" section to feel less dense and more meaningful. Reduce the visible information per card and let each problem breathe through a single-column stack of full-width horizontal cards with alternating surface tones.

## Problem With Current Design

- 2×2 grid forces all 4 cards to compete for attention on the same viewport
- Each card carries 4 information layers (number, icon, title, description, 3-bullet highlights, image) which adds visual noise
- The 3-bullet highlight list repeats low-signal information already implied by the description
- The image-on-the-right is squeezed into 42% of card width inside a 2-col grid, making the illustration feel cramped

## Approved Direction

A single-column vertical stack of 4 wide horizontal cards. Each card splits internally into a 60/40 text/image composition with a 2-tone alternating surface rhythm. Highlight bullets are removed; the description does the explanatory work on its own.

## Design Specification

### 1. Layout Structure

- **Outer grid:** `grid grid-cols-1 gap-6 lg:gap-8` (single column, vertical stack)
- **Card width:** Fills its grid cell; width is bounded by the parent `container-main` wrapper (`max-w-container mx-auto px-4 md:px-8`)
- **Card min-height:** Content-driven; remove the current `min-h-[280px]` constraint
- **Internal split (desktop, ≥1024px):** Text zone on the left fills the available space, image zone on the right is absolutely positioned at `top-6 right-6 bottom-6 w-[38%]` (narrower than the current 42% so the text zone gets more room now that the highlight list is gone)
- **Internal split (mobile, <1024px):** Image stacks below text in a `h-48` white-bg container at the card's bottom

### 2. Card Composition

**Text zone (left), top-to-bottom:**

1. **Number** — `text-5xl md:text-6xl font-semibold text-brand-green` with `font-variant-numeric: tabular-nums`. The number is the typographic anchor of the card.
2. **Icon chip + Title row** — current `flex items-start gap-3` treatment, `mt-6` below the number. Icon in 9×9 rounded chip with `bg-brand-green-soft`; title in `text-heading-4 text-white`.
3. **Description** — `text-body-md text-on-dark-muted`, `max-w-xl`, `mt-3` below the title row. No bullet list.

**Image zone (right, desktop):**

- `hidden lg:flex` container, `absolute top-6 right-6 bottom-6 w-[38%]`
- White background `bg-white/95`, `rounded-lg`, `shadow-lg`
- `<img>` with `max-h-[88%] max-w-[88%] object-contain`
- Hover: `group-hover:scale-105 transition-all duration-500`

**Image zone (mobile):**

- `lg:hidden`, `relative h-48 bg-white/95 mx-4 mb-4 rounded-lg overflow-hidden flex items-center justify-center`
- `<img>` with `max-h-[85%] max-w-[85%] object-contain`

### 3. Alternating Surface Rhythm

2-tone alternation driven by zero-based card index:

| Index | Card | Background | Border | Visual Feel |
|---|---|---|---|---|
| 0 | 01 — Store Performance | `bg-brand-green/[0.06]` | `border-hairline-dark` | Active / signal card |
| 1 | 02 — New Store Coaching | `bg-surface-dark-card` | `border-hairline-dark` | Charcoal anchor |
| 2 | 03 — Sales Drop | `bg-brand-green/[0.06]` | `border-hairline-dark` | Active return |
| 3 | 04 — Customer Preferences | `bg-surface-dark-card` | `border-hairline-dark` | Charcoal finish |

Implementation: pass a `tone: 'mint' | 'charcoal'` value to `ProblemCard` (derived from `index % 2 === 0` at the map call site) and switch on it for the background class. `mint` → `bg-brand-green/[0.06]`, `charcoal` → `bg-surface-dark-card`. Both variants share the same hover state (`hover:border-brand-green/30 hover:shadow-brand-glow`) so the rhythm doesn't break on interaction.

### 4. Typography & Spacing

- **Card padding:** `p-8 md:p-10 lg:p-12` (more generous than current `p-6`)
- **Number → title gap:** `mt-6`
- **Title → description gap:** `mt-3`
- **Description max-width:** `max-w-xl` to prevent lines spanning the full card width
- **Mobile small (<480px):** Number scales to `text-4xl`; card padding tightens to `p-6`

### 5. Animations, Accessibility & Responsive

- **Reveal animation:** Keep existing `useScrollReveal` hook with `stagger: 0.1, y: 40` — cards enter top-to-bottom down the column
- **Image hover scale:** Keep `group-hover:scale-105` on the image, unchanged
- **Reduced motion:** Already handled by `useReducedMotion` via the scroll-reveal hook
- **Accessibility:** All text retains current contrast (white on dark / muted-on-dark) — no contrast change
- **Responsive:** Single column at all breakpoints; image stacks below text below 1024px

### 6. Data Model

Drop the `highlights` field. New `ProblemCard` shape:

```ts
interface ProblemCard {
  id: string;
  number: string;
  icon: React.ElementType;
  title: string;
  description: string;
  image: string;
  imageAlt: string;
  // highlights: string[]  // REMOVED
}
```

The `problems` array keeps the same 4 entries. The 3-bullet highlight arrays on each entry are removed. The `number`, `icon`, `title`, `description`, `image`, and `imageAlt` on each entry stay identical to current.

## File-Level Change Summary

- **`src/sections/WhatSamaaSolvesSection.tsx`** — only file modified
  - Update `ProblemCard` interface: remove `highlights`
  - Update `problems` data: remove `highlights` arrays from each entry
  - Update `ProblemCard` component: drop the `<ul>` of highlights; rearrange text zone with oversized number; switch to alternating background via index
  - Update `WhatSamaaSolvesSection` component: change grid from `grid-cols-1 lg:grid-cols-2` to `grid-cols-1` only
  - Update image container width from `w-[42%]` to `w-[38%]` to give text more room (since text is now the only information layer below the title)
  - Increase card padding to `p-8 md:p-10 lg:p-12`
  - Pass card index to `ProblemCard` for tone calculation

## Out of Scope (YAGNI)

- No new image assets, no new icons, no new design tokens
- No new components or files
- No change to `SectionHeader`, scroll-reveal hook, or animation library
- All 4 icon imports (`BarChart3`, `GraduationCap`, `SearchCheck`, `Sparkles`) stay — all are still used

## Verification

- `npm run build` (or `npx tsc --noEmit`) must pass with no TypeScript errors
- Visual check at 1280px, 1024px, 768px, 480px, 360px widths
- Scroll-reveal animation still triggers on cards
- Image still scales on card hover
- "Every conversation is a data point" bottom accent line still renders

## Open Questions

None — all decisions resolved during brainstorming.
