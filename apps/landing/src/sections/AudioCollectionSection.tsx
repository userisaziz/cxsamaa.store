import React from 'react';
import { Watch, Mic, Sparkles, PieChart } from 'lucide-react';
import SectionHeader from '@/components/SectionHeader';
import { useScrollReveal } from '@/hooks/useScrollReveal';
import { BRAND_NAME } from '@/constants/brand';

const workflowSteps = [
  {
    number: '01',
    icon: Watch,
    label: 'Wear & Go',
    description: 'Lightweight wearable device. Sales associates simply wear and start their day. Zero friction, zero training required.',
  },
  {
    number: '02',
    icon: Mic,
    label: 'Listen & Capture',
    description: 'AI automatically captures and transcribes every customer conversation in real-time. Privacy-compliant by design.',
  },
  {
    number: '03',
    icon: Sparkles,
    label: 'Analyze',
    description: 'Proprietary NLP engine identifies objections, sentiment, SOP adherence, and coaching opportunities.',
  },
  {
    number: '04',
    icon: PieChart,
    label: 'Insights',
    description: 'Actionable dashboards deliver insights to managers, heads, and leadership — from store-level to enterprise-wide.',
  },
];

const AudioCollectionSection: React.FC = () => {
  const stepsRef = useScrollReveal<HTMLDivElement>({ stagger: 0.12, y: 30 });

  return (
    <section data-dark-section className="bg-canvas-dark section-padding border-t border-hairline-dark">
      <div className="container-main">
        <SectionHeader
          badge="HOW IT WORKS"
          heading="From Wear to Insight in Four Steps"
          description={`${BRAND_NAME}'s intelligent pipeline transforms in-store conversations into actionable intelligence — automatically.`}
          variant="dark"
        />

        {/* Workflow Steps */}
        <div
          ref={stepsRef}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6"
        >
          {workflowSteps.map((step) => (
            <div
              key={step.label}
              className="card-dark flex flex-col"
            >
              {/* Step Number */}
              <span className="text-4xl font-bold text-brand-green leading-none mb-5">
                {step.number}
              </span>

              {/* Icon */}
              <div className="w-12 h-12 rounded-full border border-brand-green/30 bg-brand-green/10 flex items-center justify-center mb-4">
                <step.icon
                  className="w-6 h-6 text-brand-green"
                  strokeWidth={1.5}
                />
              </div>

              {/* Title */}
              <h4 className="text-body-sm-medium text-white uppercase tracking-wide mb-2">
                {step.label}
              </h4>

              {/* Description */}
              <p className="text-body-sm text-on-dark-muted leading-relaxed flex-1">
                {step.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default AudioCollectionSection;
