import React from 'react';
import { MessageSquare, UserCheck, Store, Crown, MessageCircle } from 'lucide-react';
import SectionHeader from '@/components/SectionHeader';
import { useScrollReveal } from '@/hooks/useScrollReveal';
import { BRAND_NAME } from '@/constants/brand';

const intelligenceLayers = [
  {
    icon: MessageSquare,
    label: 'L1',
    title: 'Conversation Intelligence',
    description: 'Extract intent, sentiment, objections, and product interest from every conversation. Multi-language support across all transcripts.',
  },
  {
    icon: UserCheck,
    label: 'L2',
    title: 'Employee Intelligence',
    description: 'Analyze salesperson effectiveness, identify coaching opportunities, detect skill gaps, and understand individual conversion drivers.',
  },
  {
    icon: Store,
    label: 'L3',
    title: 'Store Intelligence',
    description: 'Explain why stores perform differently, why conversion rates change, and which behaviors drive sales across locations.',
  },
  {
    icon: Crown,
    label: 'L4',
    title: 'Leadership Intelligence',
    description: 'Enterprise insights, revenue drivers, workforce effectiveness, and strategic recommendations for retail leadership.',
  },
];

const copilotQuestions = [
  'Why did Store 12 underperform this week?',
  'Which employee improved most this month?',
  'What objections are increasing across regions?',
];

const AIIntelligenceSection: React.FC = () => {
  const layersRef = useScrollReveal<HTMLDivElement>({ y: 20, stagger: 0.12 });
  const copilotRef = useScrollReveal<HTMLDivElement>({ y: 40, duration: 0.6 });

  return (
    <section className="bg-canvas-pure section-padding">
      <div className="container-main">
        <SectionHeader
          badge="AI INTELLIGENCE"
          heading="From Conversations to Intelligence"
          description={`The ${BRAND_NAME} Intelligence Engine transforms raw conversation audio into structured business intelligence across four layers.`}
        />

        {/* Intelligence Stack */}
        <div ref={layersRef} className="max-w-4xl mx-auto mb-12">
          {intelligenceLayers.map((layer, index) => (
            <div
              key={layer.label}
              className={`card-base relative flex items-start gap-4 pl-6 ${
                index === 0 ? 'rounded-b-none' : index === intelligenceLayers.length - 1 ? 'rounded-t-none' : 'rounded-none'
              } ${index < intelligenceLayers.length - 1 ? 'border-b-0' : ''}`}
            >
              {/* Left accent bar */}
              <div className="absolute left-0 top-0 bottom-0 w-1 bg-brand-green rounded-l-lg" />

              <div className="w-10 h-10 rounded-full bg-brand-green-soft flex items-center justify-center flex-shrink-0">
                <layer.icon className="w-5 h-5 text-brand-green" strokeWidth={1.5} />
              </div>
              <div className="flex-1">
                <h4 className="text-heading-4 text-ink mb-1">{layer.title}</h4>
                <p className="text-body-sm text-slate">{layer.description}</p>
              </div>
              <span className="text-micro-uppercase text-steel font-mono flex-shrink-0">
                {layer.label}
              </span>
            </div>
          ))}
        </div>

        {/* Copilot Card */}
        <div
          ref={copilotRef}
          className="max-w-4xl mx-auto border-2 border-brand-green rounded-lg p-6 md:p-8 shadow-brand-glow"
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Left Content */}
            <div>
              <span className="badge-section mb-4 inline-block">
                RETAIL COPILOT
              </span>
              <h3 className="text-heading-2 text-ink mb-4">
                Ask Questions. Get Answers.
              </h3>
              <p className="text-body-md text-charcoal mb-6">
                Managers can ask natural-language questions and receive intelligent
                answers based on conversation data across the organization.
              </p>
              <div className="space-y-3">
                {copilotQuestions.map((q) => (
                  <div key={q} className="flex items-start gap-2">
                    <MessageCircle
                      className="w-3.5 h-3.5 text-brand-green flex-shrink-0 mt-1"
                      strokeWidth={1.5}
                    />
                    <span className="text-body-sm text-slate">{q}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Right Content - Chat Mockup */}
            <div className="card-code rounded-lg flex flex-col">
              <div className="flex items-center justify-between mb-4 pb-3 border-b border-white/10">
                <span className="text-caption-bold text-on-dark-muted">
                  {BRAND_NAME} Copilot
                </span>
                <div className="flex gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-brand-green" />
                  <span className="w-2 h-2 rounded-full bg-white/20" />
                  <span className="w-2 h-2 rounded-full bg-white/20" />
                </div>
              </div>
              <div className="flex-1 space-y-3">
                <div className="bg-white/10 rounded-lg px-3 py-2 self-end max-w-[85%] ml-auto">
                  <p className="text-body-sm text-white">
                    Why did Store 12 underperform?
                  </p>
                </div>
                <div className="bg-brand-green/15 rounded-lg px-3 py-2 max-w-[90%]">
                  <p className="text-body-sm text-brand-green">
                    Store 12 had 23% fewer upselling attempts this week. Two
                    employees missed closing opportunities on high-intent customers.
                  </p>
                </div>
              </div>
              <div className="mt-4 pt-3 border-t border-white/10">
                <span className="text-caption text-on-dark-subtle">
                  Ask anything about your stores...
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default AIIntelligenceSection;
