# Intelligence Capabilities + WhyNow Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new Intelligence Capabilities staircase section and redesign WhyNowSection with a convergence block, wiring both into the homepage flow.

**Architecture:** Two independent section components following existing patterns (SectionHeader, useScrollReveal, card-base/card-feature classes). IntelligenceCapabilitiesSection is a new file; WhyNowSection is modified in-place. App.tsx wires the new section between AIIntelligenceSection and WhyNowSection.

**Tech Stack:** React, TypeScript, Tailwind CSS, lucide-react, GSAP (via useScrollReveal hook)

---

## File Structure

| Action | File | Responsibility |
|---|---|---|
| Create | `src/sections/IntelligenceCapabilitiesSection.tsx` | 4-stage staircase section with connecting line |
| Modify | `src/sections/WhyNowSection.tsx` | Add convergence block, update description, scale up stat card |
| Modify | `src/App.tsx` | Import and place IntelligenceCapabilitiesSection |

---

### Task 1: Create IntelligenceCapabilitiesSection

**Files:**
- Create: `src/sections/IntelligenceCapabilitiesSection.tsx`

- [ ] **Step 1: Create the section component**

Create `src/sections/IntelligenceCapabilitiesSection.tsx` with the full staircase implementation:

```tsx
import React from 'react';
import {
  BarChart3,
  Search,
  TrendingUp,
  Lightbulb,
  Calendar,
  MapPin,
  Package,
  Users,
} from 'lucide-react';
import SectionHeader from '@/components/SectionHeader';
import { useScrollReveal } from '@/hooks/useScrollReveal';

interface Stage {
  number: string;
  label: string;
  question: string;
  description: string;
  exampleIcon: React.ElementType;
  exampleLabel: string;
  exampleText: string;
  bg: string;
  border: string;
  dotColor: string;
  glow?: boolean;
}

const stages: Stage[] = [
  {
    number: '01',
    label: 'Descriptive',
    question: 'What happened?',
    description:
      'Establish accurate baselines during Ramadan rushes, not just average Tuesdays.',
    exampleIcon: Calendar,
    exampleLabel: 'Baseline accuracy during peak seasons',
    exampleText:
      'Capture real baselines during high-traffic periods like Ramadan to distinguish signal from noise.',
    bg: 'bg-surface-soft',
    border: 'border-hairline',
    dotColor: 'bg-stone',
  },
  {
    number: '02',
    label: 'Diagnostic',
    question: 'Why did it happen?',
    description:
      'Use interior heatmaps and POS integration to explain why the Riyadh store converted at 18% while Jeddah hit 28%.',
    exampleIcon: MapPin,
    exampleLabel: 'Cross-store performance analysis',
    exampleText:
      'Correlate conversation quality with conversion data to diagnose performance gaps between locations.',
    bg: 'bg-canvas-pure',
    border: 'border-hairline',
    dotColor: 'bg-stone',
  },
  {
    number: '03',
    label: 'Predictive',
    question: 'What will happen?',
    description:
      'Forecast inventory needs for Eid al-Fitr and Eid al-Adha promotional windows before demand spikes.',
    exampleIcon: Package,
    exampleLabel: 'Demand forecasting for seasonal events',
    exampleText:
      'Use conversation-derived demand signals to predict inventory needs ahead of major shopping events.',
    bg: 'bg-brand-green/[0.06]',
    border: 'border-brand-green/20',
    dotColor: 'bg-brand-green/50',
  },
  {
    number: '04',
    label: 'Prescriptive',
    question: 'What should you do?',
    description:
      'AI-driven recommendations for dynamic staffing during Friday prayer transitions and automated planogram adjustments.',
    exampleIcon: Users,
    exampleLabel: 'Automated operational recommendations',
    exampleText:
      'Generate actionable staffing and layout recommendations from conversation patterns in real time.',
    bg: 'bg-brand-green-soft',
    border: 'border-brand-green/30',
    dotColor: 'bg-brand-green',
    glow: true,
  },
];

const StageCard: React.FC<{ stage: Stage }> = ({ stage }) => {
  const ExampleIcon = stage.exampleIcon;

  return (
    <div
      className={`relative rounded-lg border p-6 md:p-8 transition-all duration-300 ${stage.bg} ${stage.border} ${
        stage.glow ? 'shadow-brand-glow' : ''
      }`}
    >
      {/* Stage number */}
      <span
        className="text-4xl md:text-5xl font-semibold text-brand-green"
        style={{ fontVariantNumeric: 'tabular-nums' }}
      >
        {stage.number}
      </span>

      {/* Label + Question */}
      <h3 className="text-heading-4 text-ink mt-4">
        {stage.label}{' '}
        <span className="text-slate font-normal">— {stage.question}</span>
      </h3>

      {/* Description */}
      <p className="text-body-md text-charcoal mt-3 max-w-2xl">
        {stage.description}
      </p>

      {/* Retail example callout */}
      <div className="mt-5 flex items-start gap-3 bg-canvas-pure rounded-lg p-4 border border-hairline">
        <div className="flex-shrink-0 w-8 h-8 rounded-md bg-surface flex items-center justify-center">
          <ExampleIcon className="w-4 h-4 text-slate" strokeWidth={1.5} />
        </div>
        <div>
          <span className="text-body-sm-medium text-ink">{stage.exampleLabel}</span>
          <p className="text-caption text-slate mt-0.5">{stage.exampleText}</p>
        </div>
      </div>
    </div>
  );
};

const IntelligenceCapabilitiesSection: React.FC = () => {
  const staircaseRef = useScrollReveal<HTMLDivElement>({ stagger: 0.12, y: 40 });

  return (
    <section className="bg-white section-padding">
      <div className="container-main">
        <SectionHeader
          badge="INTELLIGENCE CAPABILITIES"
          heading="From Hindsight to Foresight"
          description="Four levels of retail intelligence — each one building on the last to turn raw conversation data into automated competitive advantage."
        />

        {/* Staircase with connecting line */}
        <div className="relative max-w-4xl mx-auto">
          {/* Connecting vertical line (desktop only) */}
          <div className="hidden lg:block absolute left-[19px] top-0 bottom-0 w-px bg-hairline" />

          <div ref={staircaseRef} className="space-y-6">
            {stages.map((stage, index) => (
              <div
                key={stage.number}
                className="relative lg:pl-12"
                style={{
                  marginLeft: `${index * 40}px`,
                }}
              >
                {/* Connecting dot (desktop only) */}
                <div
                  className={`hidden lg:flex absolute left-[14px] top-8 w-3 h-3 rounded-full items-center justify-center z-10 ${stage.dotColor} ${
                    index === stages.length - 1 ? 'animate-pulse-dot' : ''
                  }`}
                />

                <StageCard stage={stage} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};

export default IntelligenceCapabilitiesSection;
```

- [ ] **Step 2: Verify the file compiles**

Run: `npx tsc --noEmit`
Expected: No errors related to `IntelligenceCapabilitiesSection.tsx`

- [ ] **Step 3: Commit**

```bash
git add src/sections/IntelligenceCapabilitiesSection.tsx
git commit -m "feat: add IntelligenceCapabilitiesSection with 4-stage staircase"
```

---

### Task 2: Redesign WhyNowSection

**Files:**
- Modify: `src/sections/WhyNowSection.tsx`

- [ ] **Step 1: Rewrite WhyNowSection with convergence block**

Replace the entire contents of `src/sections/WhyNowSection.tsx` with:

```tsx
import React from 'react';
import {
  Package,
  Users,
  Receipt,
  Footprints,
  MessageCircle,
  Check,
  Mic,
  Cpu,
  Zap,
} from 'lucide-react';
import SectionHeader from '@/components/SectionHeader';
import { useScrollReveal } from '@/hooks/useScrollReveal';

const measuredItems = [
  { icon: Package, label: 'Inventory — ERP Systems' },
  { icon: Users, label: 'Customer — CRM Systems' },
  { icon: Receipt, label: 'Transactions — Billing Systems' },
  { icon: Footprints, label: 'Traffic — Footfall Counters' },
];

const convergenceItems = [
  {
    icon: Mic,
    metric: '99%+',
    subtitle: 'accuracy',
    description:
      'Whisper-class models now run on-device across 100+ languages and dialects — including Arabic.',
  },
  {
    icon: Cpu,
    metric: '<50ms',
    subtitle: 'latency',
    description:
      'Store-level processing with no cloud dependency. Real-time analysis without bandwidth bottlenecks.',
  },
  {
    icon: Zap,
    metric: '$0.003/min',
    subtitle: 'transcription cost',
    description:
      'Cost dropped 1000x in 3 years. Full-conversation analysis is now economically trivial.',
  },
];

const WhyNowSection: React.FC = () => {
  const listRef = useScrollReveal<HTMLDivElement>({ stagger: 0.1, y: 24 });
  const highlightRef = useScrollReveal<HTMLDivElement>({ y: 24, duration: 0.6 });
  const convergenceRef = useScrollReveal<HTMLDivElement>({ stagger: 0.1, y: 30 });
  const statRef = useScrollReveal<HTMLDivElement>({ y: 20, duration: 0.6 });

  return (
    <section className="bg-canvas section-padding">
      <div className="container-main">
        <SectionHeader
          badge="CXSAMAA"
          heading="Why Now"
          description="Everything in retail is measured — except the conversations that actually drive sales. The technology to change that just arrived."
        />

        {/* Beat 1: Measured Items (tightened) */}
        <div ref={listRef} className="max-w-3xl mx-auto space-y-2 mb-3">
          {measuredItems.map((item) => (
            <div
              key={item.label}
              className="card-base flex items-center gap-4 py-3 px-5"
            >
              <item.icon
                className="w-5 h-5 text-steel flex-shrink-0"
                strokeWidth={1.5}
              />
              <span className="text-body-md text-slate">{item.label}</span>
              <Check
                className="w-5 h-5 text-steel ml-auto flex-shrink-0"
                strokeWidth={1.5}
              />
            </div>
          ))}
        </div>

        {/* Highlighted Row — Conversations */}
        <div ref={highlightRef} className="max-w-3xl mx-auto mb-12">
          <div className="bg-brand-green-soft border border-brand-green/30 rounded-xl flex items-center gap-4 py-4 px-6">
            <MessageCircle
              className="w-6 h-6 text-ink flex-shrink-0"
              strokeWidth={1.5}
            />
            <span className="text-body-md-medium text-ink uppercase tracking-wide">
              CONVERSATIONS — The Missing Layer
            </span>
            <span className="ml-auto inline-block px-3 py-1.5 bg-ink text-brand-green text-micro-uppercase rounded-full tracking-wider whitespace-nowrap">
              UNLOCKED BY CXSAMAA
            </span>
          </div>
        </div>

        {/* Beat 2: Convergence Block */}
        <div className="max-w-4xl mx-auto mb-12">
          {/* Subheading */}
          <div className="text-center mb-8">
            <span className="text-micro-uppercase tracking-wider text-brand-green">
              THE TECHNOLOGY CONVERGENCE
            </span>
          </div>

          {/* 3-column grid */}
          <div
            ref={convergenceRef}
            className="grid grid-cols-1 md:grid-cols-3 gap-5 lg:gap-6"
          >
            {convergenceItems.map((item) => (
              <div
                key={item.subtitle}
                className="card-feature p-6"
              >
                {/* Icon */}
                <div className="w-10 h-10 rounded-lg bg-brand-green-soft flex items-center justify-center mb-4">
                  <item.icon
                    className="w-5 h-5 text-brand-green"
                    strokeWidth={1.5}
                  />
                </div>

                {/* Metric */}
                <div className="text-heading-3 text-brand-green font-semibold">
                  {item.metric}
                </div>

                {/* Subtitle */}
                <div className="text-caption text-slate mt-0.5">
                  {item.subtitle}
                </div>

                {/* Description */}
                <p className="text-body-sm text-charcoal mt-3">
                  {item.description}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Beat 3: Stat Card (scaled up) */}
        <div ref={statRef} className="max-w-3xl mx-auto">
          <div className="card-base py-8 px-8 text-center shadow-brand-glow border-brand-green/20">
            <p className="text-body-md text-slate leading-relaxed">
              <span className="text-heading-2 text-ink font-semibold inline-block mr-2">
                $4.2T
              </span>
              <span className="text-body-md text-slate">
                global offline retail — a 1% conversion improvement =
              </span>
              <span className="text-heading-2 text-brand-green font-semibold inline-block ml-2">
                $42B
              </span>
              <span className="text-body-md text-slate">
                {' '}in incremental revenue
              </span>
            </p>
          </div>
        </div>
      </div>
    </section>
  );
};

export default WhyNowSection;
```

- [ ] **Step 2: Verify the file compiles**

Run: `npx tsc --noEmit`
Expected: No errors related to `WhyNowSection.tsx`

- [ ] **Step 3: Commit**

```bash
git add src/sections/WhyNowSection.tsx
git commit -m "feat: redesign WhyNowSection with convergence block"
```

---

### Task 3: Wire IntelligenceCapabilitiesSection into App.tsx

**Files:**
- Modify: `src/App.tsx`

- [ ] **Step 1: Add import and place section in page flow**

In `src/App.tsx`, add the import after the existing section imports (around line 35):

```tsx
import IntelligenceCapabilitiesSection from './sections/IntelligenceCapabilitiesSection';
```

Then place `<IntelligenceCapabilitiesSection />` between `<AIIntelligenceSection />` and `<WhyNowSection />` in the HomePage component. The relevant section of App.tsx should look like:

```tsx
      <AIIntelligenceSection />
      <IntelligenceCapabilitiesSection />
      <WhyNowSection />
```

- [ ] **Step 2: Verify the full build**

Run: `npx tsc --noEmit && npx vite build`
Expected: Zero TypeScript errors and a successful Vite build.

- [ ] **Step 3: Commit**

```bash
git add src/App.tsx
git commit -m "feat: wire IntelligenceCapabilitiesSection into homepage flow"
```
