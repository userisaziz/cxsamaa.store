import React from 'react';
import {
  Calendar, MapPin, Package, Users,
  BarChart2, Store, TrendingUp, SlidersHorizontal,
} from 'lucide-react';
import SectionHeader from '@/components/SectionHeader';
import { useScrollReveal } from '@/hooks/useScrollReveal';

interface Stage {
  number: string;
  label: string;
  question: string;
  description: string;
  icon: React.ElementType;
  calloutIcon: React.ElementType;
  calloutLabel: string;
  calloutText: string;
}

const stages: Stage[] = [
  {
    number: '01',
    label: 'Descriptive',
    question: 'What happened?',
    icon: Calendar,
    description:
      'Establish accurate baselines during peak seasons, not just average days. Understanding what actually happened requires capturing real patterns during high-traffic periods.',
    calloutIcon: BarChart2,
    calloutLabel: 'Baseline accuracy during peak seasons',
    calloutText:
      'Capture real baselines during high-traffic periods to distinguish signal from noise.',
  },
  {
    number: '02',
    label: 'Diagnostic',
    question: 'Why did it happen?',
    icon: MapPin,
    description:
      'Use conversation heatmaps and performance data to explain why one location converts at 18% while another hits 28%. Correlating conversation quality with conversion data uncovers real drivers.',
    calloutIcon: Store,
    calloutLabel: 'Cross-location performance analysis',
    calloutText:
      'Correlate conversation quality with conversion data to diagnose performance gaps.',
  },
  {
    number: '03',
    label: 'Predictive',
    question: 'What will happen?',
    icon: Package,
    description:
      'Forecast inventory needs and demand shifts before they happen. Conversation-derived demand signals surface customer intent early enough to act proactively.',
    calloutIcon: TrendingUp,
    calloutLabel: 'Demand forecasting for seasonal events',
    calloutText:
      'Use conversation-derived demand signals to predict needs ahead of major shopping events.',
  },
  {
    number: '04',
    label: 'Prescriptive',
    question: 'What should you do?',
    icon: Users,
    description:
      'AI-driven recommendations for dynamic staffing and operational adjustments. Move from insight to automated action — the system tells you what to do and when.',
    calloutIcon: SlidersHorizontal,
    calloutLabel: 'Automated operational recommendations',
    calloutText:
      'Generate actionable staffing and layout recommendations from conversation patterns in real time.',
  },
];

const StageCard: React.FC<{ stage: Stage; index: number }> = ({ stage, index }) => {
  const Icon = stage.icon;
  const CalloutIcon = stage.calloutIcon;
  const progress = ((index + 1) / stages.length) * 100;

  return (
    <div className="card-dark group">
      {/* Progress bar */}
      <div className="h-1 rounded-full bg-white/5 mb-6 overflow-hidden">
        <div 
          className="h-full bg-brand-green transition-all duration-500 ease-out" 
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Header */}
      <div className="flex items-start gap-5 mb-5">
        <div className="w-12 h-12 rounded-xl bg-brand-green/10 border border-brand-green/20 flex items-center justify-center flex-shrink-0">
          <Icon className="w-5 h-5 text-brand-green" strokeWidth={1.5} />
        </div>
        <div>
          <div className="inline-flex items-center gap-1.5 text-micro-uppercase tracking-wider text-brand-green bg-brand-green/10 border border-brand-green/20 rounded-full px-3 py-1 mb-2">
            <span className="w-1.5 h-1.5 rounded-full bg-brand-green" />
            Stage {stage.number}
          </div>
          <h3 className="text-heading-4 text-white mb-1">{stage.label}</h3>
          <p className="text-caption text-on-dark-subtle">— {stage.question}</p>
        </div>
      </div>

      {/* Description */}
      <p className="text-body-sm text-on-dark-muted leading-relaxed mb-5">
        {stage.description}
      </p>

      {/* Callout */}
      <div className="bg-black/20 border border-hairline-dark rounded-lg p-4 flex items-start gap-3">
        <div className="w-8 h-8 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center flex-shrink-0">
          <CalloutIcon className="w-4 h-4 text-on-dark-subtle" strokeWidth={1.5} />
        </div>
        <div>
          <div className="text-body-sm-medium text-on-dark-muted mb-1">{stage.calloutLabel}</div>
          <p className="text-caption text-on-dark-subtle leading-relaxed">{stage.calloutText}</p>
        </div>
      </div>
    </div>
  );
};

const IntelligenceCapabilitiesSection: React.FC = () => {
  const gridRef = useScrollReveal<HTMLDivElement>({ stagger: 0.12, y: 30 });

  return (
    <section className="bg-canvas-dark section-padding">
      <div className="container-main">
        <SectionHeader
          badge="INTELLIGENCE CAPABILITIES"
          heading="From Hindsight to Foresight"
          description="Four levels of retail intelligence — each building on the last to turn raw conversation data into automated competitive advantage."
          variant="dark"
        />

        <div
          ref={gridRef}
          className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-8"
        >
          {stages.map((stage, index) => (
            <StageCard key={stage.number} stage={stage} index={index} />
          ))}
        </div>

        {/* Bottom accent */}
        <div className="mt-12 md:mt-16 flex items-center justify-center gap-4">
          <div className="h-px flex-1 max-w-[100px] bg-gradient-to-r from-transparent to-brand-green/40" />
          <div className="w-1.5 h-1.5 rounded-full bg-brand-green" />
          <span className="text-micro-uppercase tracking-widest text-on-dark-muted">
            Intelligence that compounds
          </span>
          <div className="w-1.5 h-1.5 rounded-full bg-brand-green" />
          <div className="h-px flex-1 max-w-[100px] bg-gradient-to-l from-transparent to-brand-green/40" />
        </div>
      </div>
    </section>
  );
};

export default IntelligenceCapabilitiesSection;