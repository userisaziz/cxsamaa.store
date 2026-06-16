# WhatSamaaSolvesSection Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the "What CXSAMAA Solves" section into a single-column vertical stack of 4 wide horizontal cards with alternating 2-tone surface rhythm, oversized numbers, no highlight bullets.

**Architecture:** Single file (`src/sections/WhatSamaaSolvesSection.tsx`). The data model drops `highlights`; the card component accepts a `tone` prop for alternating surface colors; the outer grid becomes `grid-cols-1` only. All other components (SectionHeader, useScrollReveal) are unchanged.

**Tech Stack:** React, TypeScript, Tailwind CSS (custom CXSAMAA design tokens: `brand-green`, `surface-dark-card`, `hairline-dark`, `on-dark-muted`, etc.), GSAP (via useScrollReveal).

**Spec:** `docs/superpowers/specs/2026-06-07-what-samaa-solves-section-design.md`

---

### Task 1: Update ProblemCard interface and data model

**Files:**
- Modify: `src/sections/WhatSamaaSolvesSection.tsx:16-25`

- [ ] **Step 1: Remove `highlights` from the `ProblemCard` interface**

Replace the existing `ProblemCard` interface (lines 16-25) with:

```ts
interface ProblemCard {
  id: string;
  number: string;
  icon: React.ElementType;
  title: string;
  description: string;
  image: string;
  imageAlt: string;
}
```

- [ ] **Step 2: Remove all `highlights` arrays from the `problems` array**

Delete the `highlights: [...]` property from each of the 4 entries in the `problems` array:
- `store-performance` entry: delete lines 35-39 (the `highlights` array with 3 bullet strings)
- `coaching-support` entry: delete lines 51-55 (the `highlights` array with 3 bullet strings)
- `sales-drop` entry: delete lines 67-71 (the `highlights` array with 3 bullet strings)
- `customer-preferences` entry: delete lines 82-86 (the `highlights` array with 3 bullet strings)

The `number`, `icon`, `title`, `description`, `image`, and `imageAlt` properties on each entry remain identical.

- [ ] **Step 3: Verify TypeScript compiles**

Skip this step — the `ProblemCard` component still references `card.highlights` until Task 2 rewrites it. TypeScript verification happens after Task 2 in Task 4.

---

### Task 2: Rewrite ProblemCard component with new layout + alternating tone

**Files:**
- Modify: `src/sections/WhatSamaaSolvesSection.tsx:93-156` (the `ProblemCard` component)

- [ ] **Step 1: Replace the entire `ProblemCard` component**

Replace the current `ProblemCard` component (lines 93-156) with the following:

```tsx
type Tone = 'mint' | 'charcoal';

const ProblemCard: React.FC<{ card: ProblemCard; tone: Tone }> = ({
  card,
  tone,
}) => {
  const Icon = card.icon;
  const isMint = tone === 'mint';

  return (
    <div
      className={`group relative rounded-lg overflow-hidden border border-hairline-dark transition-all duration-300 hover:border-brand-green/30 hover:shadow-brand-glow ${
        isMint ? 'bg-brand-green/[0.06]' : 'bg-surface-dark-card'
      }`}
    >
      {/* Content area — left side */}
      <div className="relative z-10 p-6 md:p-8 lg:p-12 lg:pr-[42%]">
        {/* Oversized number */}
        <span
          className="text-4xl md:text-5xl lg:text-6xl font-semibold text-brand-green"
          style={{ fontVariantNumeric: 'tabular-nums' }}
        >
          {card.number}
        </span>

        {/* Icon + Title */}
        <div className="flex items-start gap-3 mt-6">
          <div className="flex-shrink-0 w-9 h-9 rounded-full bg-brand-green-soft flex items-center justify-center mt-0.5">
            <Icon className="w-[18px] h-[18px] text-brand-green" strokeWidth={1.5} />
          </div>
          <h3 className="text-heading-4 text-white leading-tight">
            {card.title}
          </h3>
        </div>

        {/* Description */}
        <p className="text-body-md text-on-dark-muted max-w-xl mt-3">
          {card.description}
        </p>
      </div>

      {/* Image overlay — absolute right side with white background (desktop) */}
      <div className="hidden lg:flex absolute top-6 right-6 bottom-6 w-[38%] items-center justify-center rounded-lg bg-white/95 shadow-lg pointer-events-none overflow-hidden">
        <img
          src={card.image}
          alt={card.imageAlt}
          className="max-h-[88%] max-w-[88%] object-contain transition-all duration-500 group-hover:scale-105"
        />
      </div>

      {/* Mobile image — shown below content on small screens */}
      <div className="lg:hidden relative h-48 bg-white/95 mx-4 mb-4 rounded-lg overflow-hidden flex items-center justify-center">
        <img
          src={card.image}
          alt={card.imageAlt}
          className="max-h-[85%] max-w-[85%] object-contain"
        />
      </div>
    </div>
  );
};
```

Key changes from the original:
- New `tone: Tone` prop; background switches between `bg-brand-green/[0.06]` and `bg-surface-dark-card`
- Removed `min-h-[280px]` — height is now content-driven
- Replaced small number badge (9×9 circle with `text-micro`) with oversized typographic number (`text-4xl md:text-5xl lg:text-6xl font-semibold`)
- Added `fontVariantNumeric: 'tabular-nums'` for vertical alignment
- Number → title gap: `mt-6`
- Title → description gap: `mt-3`
- Description: upgraded from `text-body-sm` to `text-body-md`; added `max-w-xl`
- Card padding: `p-6 md:p-8 lg:p-12` (mobile stays at `p-6` per spec)
- Removed the entire `<ul>` of highlight bullets
- Image container: `top-6 right-6 bottom-6 w-[38%]` (was `top-4 right-4 bottom-4 w-[42%]`)
- Left padding for image zone: `lg:pr-[42%]` (was `lg:pr-[45%]`)

---

### Task 3: Update WhatSamaaSolvesSection — single column grid + tone passing

**Files:**
- Modify: `src/sections/WhatSamaaSolvesSection.tsx:158-191` (the main section component)

- [ ] **Step 1: Change grid from 2-col to 1-col and pass `tone` to each card**

Replace the current `<div ref={gridRef} ...>` block (lines 171-178) with:

```tsx
        <div
          ref={gridRef}
          className="grid grid-cols-1 gap-6 lg:gap-8"
        >
          {problems.map((card, index) => (
            <ProblemCard
              key={card.id}
              card={card}
              tone={index % 2 === 0 ? 'mint' : 'charcoal'}
            />
          ))}
        </div>
```

Changes:
- Removed `lg:grid-cols-2` — single column at all breakpoints
- Added `index` to the `.map()` callback
- Pass `tone={index % 2 === 0 ? 'mint' : 'charcoal'}` to each `<ProblemCard />`

The `SectionHeader`, scroll-reveal hook, section wrapper, and bottom accent line remain unchanged.

---

### Task 4: Build verification

**Files:**
- No changes — verification only

- [ ] **Step 1: Run TypeScript compiler**

Run:
```bash
cd /Users/almabetter/Desktop/samaa && npx tsc --noEmit
```
Expected: PASS — no type errors.

- [ ] **Step 2: Run production build**

Run:
```bash
cd /Users/almabetter/Desktop/samaa && npm run build
```
Expected: PASS — `dist/` output generated with no errors.

- [ ] **Step 3: Visual verification**

Start the dev server:
```bash
cd /Users/almabetter/Desktop/samaa && npm run dev
```

Check at these viewport widths:
- **1280px (desktop):** 4 stacked cards, image on the right, alternating mint/charcoal backgrounds, numbers are oversized
- **1024px (tablet):** Same as desktop but cards are narrower
- **768px:** Single column, image stacks below text in white container
- **480px (mobile):** Number scales to `text-4xl`, padding tightens to `p-6`
- **360px (small mobile):** Everything still renders cleanly, no horizontal overflow

Verify:
- Scroll-reveal animation triggers (cards fade in from bottom as they enter viewport)
- Image scales on card hover (`group-hover:scale-105`)
- Bottom accent line ("Every conversation is a data point") still renders
- All 4 cards show with correct alternating tone (cards 1,3 mint; cards 2,4 charcoal)

- [ ] **Step 4: Commit**

```bash
cd /Users/almabetter/Desktop/samaa
git add src/sections/WhatSamaaSolvesSection.tsx
git commit -m "feat: redesign WhatSamaaSolvesSection as single-column alternating cards

- Single-column vertical stack (was 2x2 grid)
- 2-tone alternating surface rhythm: mint tint / charcoal
- Oversized typographic numbers (text-5xl/6xl)
- Removed 3-bullet highlight lists
- Image on right at 38% width (was 42%)
- Increased card padding for breathing room
- Content-driven card height (removed min-h-[280px])"
```
