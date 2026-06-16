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
import { BRAND_NAME } from '@/constants/brand';

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
    <section className="bg-canvas-dark section-padding">
      <div className="container-main">
        <SectionHeader
          badge={BRAND_NAME}
          heading="Why Now"
          description="Everything in retail is measured — except the conversations that actually drive sales. The technology to change that just arrived."
          variant="dark"
        />

        {/* Beat 1: Measured Items (tightened) */}
        <div ref={listRef} className="max-w-3xl mx-auto space-y-2 mb-3">
          {measuredItems.map((item) => (
            <div
              key={item.label}
              className="card-dark flex items-center gap-4 py-3 px-5"
            >
              <item.icon
                className="w-5 h-5 text-on-dark-muted flex-shrink-0"
                strokeWidth={1.5}
              />
              <span className="text-body-md text-on-dark-muted">{item.label}</span>
              <Check
                className="w-5 h-5 text-on-dark-muted ml-auto flex-shrink-0"
                strokeWidth={1.5}
              />
            </div>
          ))}
        </div>

        {/* Highlighted Row — Conversations */}
        <div ref={highlightRef} className="max-w-3xl mx-auto mb-12">
          <div className="bg-brand-green-soft border border-brand-green/40 rounded-xl flex items-center gap-4 py-4 px-6">
            <MessageCircle
              className="w-6 h-6 text-brand-green flex-shrink-0"
              strokeWidth={1.5}
            />
            <span className="text-body-md-medium text-on-dark uppercase tracking-wide">
              CONVERSATIONS — The Missing Layer
            </span>
            <span className="ml-auto inline-block px-3 py-1.5 bg-brand-green text-ink text-micro-uppercase rounded-full tracking-wider whitespace-nowrap font-semibold">
              UNLOCKED BY {BRAND_NAME}
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
                className="card-dark p-6 border-hairline-dark hover:border-brand-green/40"
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
                <div className="text-caption text-on-dark-muted mt-0.5">
                  {item.subtitle}
                </div>

                {/* Description */}
                <p className="text-body-sm text-on-dark-muted mt-3">
                  {item.description}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Beat 3: Stat Card (scaled up) */}
        <div ref={statRef} className="max-w-3xl mx-auto">
          <div className="card-dark py-8 px-8 text-center shadow-[0_0_40px_rgba(0,212,164,0.15)] border-brand-green/30">
            <p className="text-body-md text-on-dark-muted leading-relaxed">
              <span className="text-heading-2 text-on-dark font-semibold inline-block mr-2">
                $4.2T
              </span>
              <span className="text-body-md text-on-dark-muted">
                global offline retail — a 1% conversion improvement =
              </span>
              <span className="text-heading-2 text-brand-green font-semibold inline-block ml-2">
                $42B
              </span>
              <span className="text-body-md text-on-dark-muted">
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
