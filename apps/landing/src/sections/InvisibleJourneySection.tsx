import React from 'react';
import { EyeOff } from 'lucide-react';
import SectionHeader from '@/components/SectionHeader';
import { useScrollReveal } from '@/hooks/useScrollReveal';
const journeySteps = [
  { step: 1, label: 'Walk-In', subtitle: 'Customer enters store', status: 'TRACKED', captured: true },
  { step: 2, label: 'Conversation', subtitle: 'Needs & preferences', status: 'NOT CAPTURED', captured: false },
  { step: 3, label: 'Questions', subtitle: 'Product inquiries', status: 'NOT ANALYZED', captured: false },
  { step: 4, label: 'Objections', subtitle: 'Price, fit, concerns', status: 'NOT DETECTED', captured: false },
  { step: 5, label: 'Decision', subtitle: 'Purchase intent', status: 'NOT UNDERSTOOD', captured: false },
  { step: 6, label: 'Sale', subtitle: 'Transaction completed', status: 'TRACKED', captured: true },
];



const InvisibleJourneySection: React.FC = () => {
  const stepsRef = useScrollReveal<HTMLDivElement>({ stagger: 0.08, y: 20 });
  const mobileRef = useScrollReveal<HTMLDivElement>({ stagger: 0.08, y: 20 });
  const cardRef = useScrollReveal<HTMLDivElement>({ y: 30, stagger: 0.15 });

  return (
    <section data-dark-section className="bg-canvas-dark section-padding overflow-hidden">
      <div className="container-main">
        <SectionHeader
          badge="THE VISIBILITY GAP"
          heading="The Invisible Customer Journey"
          description="70% of purchase decisions happen in-store — yet conversations are invisible."
          variant="dark"
        />

     

        {/* Desktop Timeline (lg+) */}
        <div className="hidden lg:block">
          <div className="relative">
            {/* Connector line behind circles */}
            <div className="absolute top-6 left-[4%] right-[4%] h-px bg-gradient-to-r from-transparent via-hairline-dark to-transparent" />

            <div ref={stepsRef} className="flex justify-between">
              {journeySteps.map((step) => (
                <div key={step.step} className="flex flex-col items-center flex-1">
                  {/* Circle */}
                  <div
                    className={`relative z-10 w-12 h-12 rounded-full flex items-center justify-center text-lg font-semibold border-2 transition-colors duration-200 ${
                      step.captured
                        ? 'bg-brand-green border-brand-green text-white'
                        : 'bg-transparent border-brand-warn/40 text-brand-warn'
                    }`}
                  >
                    {step.step}
                  </div>

                  {/* Label */}
                  <span className="text-body-sm-medium text-white mt-4">
                    {step.label}
                  </span>

                  {/* Subtitle */}
                  <span className="text-caption text-on-dark-subtle mt-0.5 text-center max-w-[100px]">
                    {step.subtitle}
                  </span>

                  {/* Status */}
                  <span
                    className={`inline-block mt-3 text-micro-uppercase tracking-wider px-2 py-1 rounded ${
                      step.captured
                        ? 'bg-brand-green/10 text-brand-green'
                        : 'bg-brand-warn/10 text-brand-warn'
                    }`}
                  >
                    {step.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Mobile/Tablet Timeline (< lg) */}
        <div ref={mobileRef} className="lg:hidden space-y-4 max-w-lg mx-auto">
          {journeySteps.map((step) => (
            <div
              key={step.step}
              className="flex items-center gap-4 card-dark border border-hairline-dark py-4 px-5"
            >
              {/* Circle */}
              <div
                className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center text-base font-semibold border-2 ${
                  step.captured
                    ? 'bg-brand-green border-brand-green text-white'
                    : 'bg-transparent border-brand-warn/40 text-brand-warn'
                }`}
              >
                {step.step}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-body-sm-medium text-white">
                    {step.label}
                  </span>
                  <span
                    className={`flex-shrink-0 text-micro-uppercase tracking-wider ${
                      step.captured ? 'text-brand-green' : 'text-brand-warn'
                    }`}
                  >
                    {step.status}
                  </span>
                </div>
                <span className="text-caption text-on-dark-subtle block mt-0.5">
                  {step.subtitle}
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* Stats Card */}
        <div ref={cardRef} className="card-dark border border-hairline-dark flex items-center gap-6 md:gap-10 py-6 px-6 md:py-8 md:px-10 mt-12 md:mt-16 max-w-3xl mx-auto">
          {/* Text */}
          <div className="flex-1">
            <p className="text-body-md-medium text-white">
              Revenue tells you <span className="text-on-dark-muted">WHAT</span> happened.
            </p>
            <p className="text-body-md-medium text-brand-green mt-1">
              Conversations tell you <span className="font-semibold">WHY</span>.
            </p>
            <div className="mt-4 flex items-baseline gap-2">
              <span className="text-5xl md:text-6xl font-semibold text-brand-green leading-none">
                90%
              </span>
              <span className="text-body-sm text-on-dark-muted">
                of sales conversations go unrecorded and unanalyzed.
              </span>
            </div>
          </div>

          {/* Icon */}
          <div className="flex-shrink-0">
            <div className="w-14 h-14 md:w-16 md:h-16 rounded-full bg-surface-dark-card border border-hairline-dark flex items-center justify-center">
              <EyeOff className="w-6 h-6 text-on-dark-subtle" strokeWidth={1.5} />
            </div>
          </div>
          
        </div>

     
      </div>
    </section>
  );
};

export default InvisibleJourneySection;