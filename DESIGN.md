---
name: SAMAA
description: Sales Audio Intelligence dashboard system for retail operations
colors:
  brand-green: "oklch(0.75 0.18 165)"
  brand-green-deep: "oklch(0.65 0.2 165)"
  brand-green-soft: "oklch(0.95 0.05 165)"
  brand-tag: "oklch(0.55 0.15 260)"
  brand-annotate: "oklch(0.7 0.16 165)"
  brand-warn: "oklch(0.75 0.15 80)"
  brand-error: "oklch(0.6 0.22 25)"
  testimonial-orange: "oklch(0.75 0.18 55)"
  ink: "oklch(0.15 0 0)"
  charcoal: "oklch(0.25 0 0)"
  slate: "oklch(0.45 0 0)"
  steel: "oklch(0.55 0 0)"
  stone: "oklch(0.65 0 0)"
  canvas: "oklch(1 0 0)"
  canvas-dark: "oklch(0.15 0 0)"
  surface: "oklch(0.96 0 0)"
  surface-soft: "oklch(0.97 0 0)"
  surface-code: "oklch(0.18 0.02 260)"
  on-dark: "oklch(0.985 0 0)"
  on-dark-muted: "oklch(0.75 0 0)"
  hairline: "oklch(0.92 0 0)"
  hairline-soft: "oklch(0.94 0 0)"
  primary: "oklch(0.15 0 0)"
  primary-foreground: "oklch(0.985 0 0)"
  destructive: "oklch(0.6 0.22 25)"
typography:
  body:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "0"
  headline:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: "28px"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "-0.02em"
  title:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: "18px"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "0"
  label:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: "11px"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "0.05em"
  mono:
    fontFamily: "'Geist Mono', 'SF Mono', Menlo, Consolas, monospace"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "0"
rounded:
  sm: "4px"
  md: "8px"
  lg: "12px"
  xl: "16px"
spacing:
  xs: "8px"
  sm: "12px"
  md: "16px"
  lg: "20px"
  xl: "24px"
  xxl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.primary-foreground}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
  button-outline:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
  card-base:
    backgroundColor: "{colors.canvas}"
    rounded: "{rounded.lg}"
    padding: "{spacing.xl}"
  input-base:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "8px 12px"
    height: "40px"
---

# Design System: SAMAA

## 1. Overview

**Creative North Star: "The Analyst's Workbench"**

SAMAA's visual system is a refined analytical workspace. Like a well-organized analyst's desk, every element has a designated place and purpose. The interface communicates data confidence through clean precision and warm professionalism: considered spacing that lets dense information breathe, approachable hierarchy that guides the eye without hand-holding, and a restrained palette where the mint-green brand accent appears only where it earns attention.

The system explicitly rejects generic enterprise CRM aesthetics. No boilerplate blue-and-white templates, no reskinned admin panel starter kits. SAMAA feels purpose-built for retail audio intelligence. It also rejects cold sterility: the design is warm through accent color and typographic care, not through decorative elements. Every surface, every spacing decision, every color choice serves the analyst's workflow of scanning, drilling, and acting on insights.

Soft layering creates hierarchy without heaviness. Cards float subtly above the surface-soft background, interactive elements respond to hover with gentle elevation, and the 64px sidebar provides a stable frame for the data workspace. The result is an interface that feels like a trusted tool: precise, organized, and always ready to surface the next insight.

**Key Characteristics:**
- Mint-green brand accent (`{colors.brand-green}`) reserved for active states, focus rings, and positive indicators
- Black primary buttons (`{colors.primary}`) for decisive CTAs across all surfaces
- Inter for all UI prose and headings; Geist Mono for data values, code, and type signatures
- Soft elevation via subtle shadows on cards and interactive containers
- shadcn/ui component foundation with custom semantic color tokens
- Dashboard shell: fixed 256px sidebar with flex-1 scrollable content area
- WCAG AAA contrast targets across all text/background combinations

## 2. Colors

The palette is an analytical instrument: neutral grays carry information density, the mint-green accent signals action and positive states, and semantic colors (blue for processing, red for errors, orange for warmth) encode meaning without relying on color alone.

### Primary
- **Brand Mint** (`{colors.brand-green}`): The signature accent. Used on active sidebar indicators, positive trend arrows, focus rings, completed status badges, and KPI icon backgrounds (via `{colors.brand-green-soft}`). Its restraint is its power.
- **Deep Mint** (`{colors.brand-green-deep}`): Pressed/active variant and trend-positive text color. Carries more weight than the base mint for readability on light backgrounds.
- **Soft Mint** (`{colors.brand-green-soft}`): Tinted background for KPI icon containers and confirmation surfaces. A whisper of the brand.

### Semantic
- **Signal Blue** (`{colors.brand-tag}`): Processing states (transcribing, analyzing, scoring status badges). The "work in progress" color.
- **Alert Red** (`{colors.brand-error}`, `{colors.destructive}`): Errors, failed pipeline stages, negative trends. Reserved for genuine attention-required moments.
- **Warm Amber** (`{colors.brand-warn}`): Caution states and deprecated indicators.
- **Testimonial Coral** (`{colors.testimonial-orange}`): Warm accent for testimonial and highlight surfaces. Breaks the analytical palette intentionally for emotional moments.

### Neutral
- **Ink** (`{colors.ink}`): Primary headlines and CTA text. Near-black at oklch(0.15 0 0).
- **Charcoal** (`{colors.charcoal}`): Body text and form labels.
- **Slate** (`{colors.slate}`): Secondary text, descriptions, and metadata.
- **Steel** (`{colors.steel}`): Tertiary text, sidebar inactive items, breadcrumb links, placeholder-adjacent content.
- **Stone** (`{colors.stone}`): Muted captions and de-emphasized labels.
- **Canvas** (`{colors.canvas}`): Pure white card and page backgrounds.
- **Surface Soft** (`{colors.surface-soft}`): Dashboard content area background, creating subtle separation from white cards.
- **Hairline** (`{colors.hairline}`): Borders and primary dividers at oklch(0.92 0 0).
- **Hairline Soft** (`{colors.hairline-soft}`): Quieter dividers between table rows and secondary sections.

### Named Rules
**The Mint Restraint Rule.** Brand mint appears on at most 3-4 elements per viewport: one active nav indicator, one positive trend, one focus ring, and one KPI icon. If you count more than five mint-colored elements on a single screen, the accent has lost its signal.

**The Semantic Pairing Rule.** Color never carries meaning alone. Every color-coded status pairs with a text label (badge text, icon, or tooltip). Color-blind users must get the same information from the non-color channel.

## 3. Typography

**Display Font:** Inter (with -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif)
**Body Font:** Inter (with -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif)
**Mono Font:** Geist Mono (with 'SF Mono', Menlo, Consolas, monospace)

**Character:** Inter carries the full UI hierarchy through weight contrast (400/500/600) rather than introducing a display face. This single-family approach signals tool-grade consistency. Geist Mono appears only for data values, scores, timestamps, and inline code, creating a clear "this is a measured value" signal.

### Hierarchy
- **Page Title** (600, 28px, 1.25 line-height, -0.02em tracking): Dashboard page headers. The largest type on any screen.
- **Section Title** (600, 18px, 1.4 line-height): Card headers, subsection headers, dialog titles.
- **Body** (400, 14px, 1.5 line-height): Primary body text, descriptions, table cells. Max line length 65-75ch.
- **Body Medium** (500, 14px, 1.5 line-height): Active nav items, button labels, emphasis within body text.
- **Label** (600, 11px, 1.4 line-height, uppercase, +0.05em tracking): Sidebar section headers ("NAVIGATION"), role badges, uppercase microcopy. The only uppercase text in the system.
- **Mono Data** (400, 13px, 1.5 line-height): Scores, timestamps, confidence values, transcript timestamps. Geist Mono signals "this is a measured/computed value."

### Named Rules
**The Two-Face Rule.** Inter for human language, Geist Mono for machine values. A score of "87" in Geist Mono says "this was computed." The same "87" in Inter says "someone typed this." The typeface IS the data provenance signal.

**The Uppercase Ceiling Rule.** Uppercase text is limited to 11px labels with wide tracking (section headers, role tags). No all-caps body copy, no uppercase button labels, no uppercase navigation items. Uppercase above 11px is shouting.

## 4. Elevation

SAMAA uses soft layering: subtle, diffused shadows that create gentle separation between the content workspace and its containers. The base surface (`{colors.surface-soft}`) sits below white cards, which float with a barely-perceptible shadow. Interactive elements gain slightly more elevation on hover, signaling responsiveness without drama.

### Shadow Vocabulary
- **Card Rest** (`0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.06)`): Default card elevation. Just enough to lift off the surface-soft background.
- **Card Hover** (`0 4px 12px rgba(0,0,0,0.08)`): Interactive cards on hover. A gentle rise that signals clickability.
- **Login Card** (`0 4px 24px -4px rgba(0,0,0,0.08)`): Deeper diffuse shadow for the login card, the only full-page elevated element.
- **Dropdown / Popover** (`0 8px 24px rgba(0,0,0,0.12)`): Floating menus and popovers. The deepest shadow in the system, reserved for elements that must read as "above everything."

### Named Rules
**The Whisper Rule.** Shadows are whispers, not statements. If a shadow is the first thing you notice about a component, it's too strong. The shadow should be noticeable only when removed.

## 5. Components

### Buttons
- **Shape:** Gently rounded corners (`{rounded.md}`, 8px). Not pill-shaped; the dashboard context calls for structured, not playful.
- **Primary:** Background `{colors.primary}` (near-black), text `{colors.primary-foreground}`, padding `8px 16px`, font-weight 500. The decisive action.
- **Hover:** Slight lighten to `{colors.charcoal}` background, no transform shift.
- **Outline:** Transparent background, `{colors.ink}` text, 1px `{colors.hairline}` border. Secondary actions.
- **Ghost:** No border, `{colors.ink}` text, transparent background with hover fill. Tertiary actions and nav items.
- **Full-width:** Login and critical CTAs use `w-full` with `size="lg"` (taller padding).

### Cards / Containers
- **Corner Style:** `{rounded.lg}` (12px) consistently across all cards.
- **Background:** `{colors.canvas}` (white) on `{colors.surface-soft}` content area.
- **Shadow Strategy:** Card Rest at default, Card Hover on interactive cards. Reference Elevation section.
- **Border:** 1px solid `{colors.hairline}` on non-elevated containers; cards rely on shadow + background contrast.
- **Internal Padding:** `{spacing.xl}` (24px) standard; `{spacing.xxl}` (32px) for dashboard section containers.
- **KPI Cards:** Header row with title (steel, 14px medium) and icon container (brand-green-soft background, 32x32px, brand-green-deep icon). Value in 24px semibold ink. Optional trend line in brand-green-deep or destructive.

### Status Badges
- **Style:** Pill-shaped badge with tinted background + matching text + subtle border. Each pipeline stage maps to a semantic color.
- **Uploaded:** Stone-tinted background, slate text.
- **Processing stages** (Preprocessing, Transcribing, Diarizing, Segmenting, Analyzing, Scoring): Signal Blue tinted background, brand-tag text.
- **Completed:** Soft Mint background, deep mint text, brand-green border.
- **Failed:** Red-tinted background, destructive text.

### Inputs / Fields
- **Style:** 1px `{colors.hairline}` border, `{colors.canvas}` background, `{rounded.md}` corners, 40px height, 12px horizontal padding.
- **Focus:** 2px `{colors.brand-green}` ring (via `{colors.ring}`). The mint accent appears on activation, signaling the field is live.
- **Labels:** 14px medium weight, charcoal color, positioned above with 8px gap.
- **Error:** Destructive-tinted background container with destructive text and border. Error message appears inline below the field.

### Navigation
- **Sidebar:** Fixed 256px width, `{colors.canvas}` background, right border in `{colors.hairline}`. Logo mark (36x36px primary bg with icon) + "SAMAA" wordmark at top.
- **Nav Items:** 14px medium weight, steel text, rounded-md with 8px vertical padding. Active state: brand-green-soft background, ink text, 2px left border in brand-green. Inactive: transparent background, transparent left border.
- **Section Headers:** 11px uppercase tracking-widest steel text above nav groups.
- **User Footer:** Separator + user name (14px medium ink) + role label (11px uppercase steel) + outline sign-out button.
- **Breadcrumbs:** 14px steel text with chevron separators. Active breadcrumb in ink (medium weight). Hover transitions to ink.

### Login Card
- **Signature treatment:** Centered card on atmospheric sky gradient (`hero-sky-from` to `hero-sky-to` to white). 1px brand-green accent bar at card top. Large icon mark (56x56px primary bg) + "SAMAA" title (28px semibold) + subtitle (steel). Card shadow is the deepest in the system.

## 6. Do's and Don'ts

### Do:
- **Do** use `{colors.brand-green}` sparingly. Count mint-colored elements per viewport: 3-4 is the ceiling. Its rarity IS the brand signal.
- **Do** pair Inter for all UI prose and Geist Mono for all computed/measured values. The typeface switch tells the user "this number came from the AI pipeline."
- **Do** maintain 7:1 contrast ratio on body text (WCAG AAA). Charcoal (`{colors.charcoal}`) on white canvas passes. Never use Steel or Stone for body copy.
- **Do** use `{colors.surface-soft}` as the dashboard content background. White cards on soft gray creates depth through contrast, not shadow alone.
- **Do** encode every status with both color AND text. The COMPLETED badge is green AND says "Completed." Color-blind users get the same information.
- **Do** keep the sidebar at 256px fixed width with `{colors.canvas}` background. It's the stable frame around the data workspace.

### Don't:
- **Don't** use the generic enterprise CRM template. No blue-and-white Salesforce layouts, no HubSpot-style sidebar with colored icon tiles. SAMAA is purpose-built for audio intelligence.
- **Don't** use `{colors.brand-green}` on body text, large surfaces, or decorative elements. If it's not signaling an action, active state, or positive indicator, it shouldn't be mint.
- **Don't** introduce pill-shaped buttons. The dashboard uses `{rounded.md}` (8px), not `{rounded.full}`. Pill shapes signal marketing/landing context, not analytical tools.
- **Don't** use all-caps text above 11px. Button labels, nav items, and section titles stay in sentence case. Only micro-labels (sidebar section headers, role tags) use uppercase.
- **Don't** use glassmorphism, gradient text, or decorative blur effects. The Analyst's Workbench is solid, grounded, and functional. Transparency effects belong in marketing, not data tools.
- **Don't** use side-stripe borders (`border-left` > 1px as colored accent) on cards or list items. The sidebar active indicator is the sole exception in the entire system.
- **Don't** create identical card grids (same-sized cards with icon + heading + text repeated endlessly). Vary card sizes and content based on data importance and hierarchy.
- **Don't** use heavy drop shadows. The deepest shadow in the system (`0 8px 24px rgba(0,0,0,0.12)`) is reserved for floating popovers. Cards whisper, they don't shout.
