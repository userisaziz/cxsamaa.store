import React from 'react';
import { Eye, Layers, TrendingUp, Target, CheckCircle2, ArrowRight } from 'lucide-react';
import SectionHeader from '@/components/SectionHeader';
import { useScrollReveal } from '@/hooks/useScrollReveal';
import dashboardImg from '@/assets/dashboard.png';
import communicationImg from '@/assets/shield.png';
import { BRAND_NAME } from '@/constants/brand';

const valuePillars = [
  {
    icon: Eye,
    title: 'Complete Visibility',
    description:
      'Understand not just the results, but the conversations that create them.',
  },
  {
    icon: Layers,
    title: 'Consistent Performance',
    description:
      'Discover what top performers do differently and scale those behaviors across teams.',
  },
  {
    icon: TrendingUp,
    title: 'Measurable Improvement',
    description:
      'Track progress through real conversation insights, not assumptions.',
  },
  {
    icon: Target,
    title: 'Smarter Coaching',
    description:
      'Focus coaching where it will have the biggest impact on sales outcomes.',
  },
];

const visibilityItems = [
  'why deals move forward or stall. See the moments that help customers buy or cause them to hesitate.',
  'winning sales behaviors. Identify the approaches that consistently lead to successful outcomes.',
  'customer questions and objections. Understand what customers are asking and where concerns arise.',
  'coaching opportunities. Spot skill gaps and improvement areas across teams and locations.',
  'performance trends. Track changes in sales conversations over time and measure improvement.',
];

const choiceItems = [
  'No extra work. Insights are generated automatically from real customer conversations.',
  'No constant monitoring. No need to spend hours observing associates or reviewing interactions manually.',
  `No manual scoring. ${BRAND_NAME} analyzes conversations without requiring tagging or evaluation forms.`,
  `No workflow disruption. Teams continue selling as usual while ${BRAND_NAME} captures valuable insights in the background.`,
];

const SystemArchitectureSection: React.FC = () => {
  const pillarsRef = useScrollReveal<HTMLDivElement>({ stagger: 0.12, y: 30 });
  const visibilityRef = useScrollReveal<HTMLDivElement>({ y: 30, duration: 0.6 });
  const choiceRef = useScrollReveal<HTMLDivElement>({ y: 30, duration: 0.6 });
  const ctaRef = useScrollReveal<HTMLDivElement>({ y: 20, duration: 0.6 });

  return (
    <section id="sales-leadership" data-dark-section className="bg-canvas-dark section-padding">
      <div className="container-main">
        <SectionHeader
          badge="FOR SALES LEADERSHIP"
          heading={`What Sales Leaders Gain with ${BRAND_NAME}`}
          description={`From blind spots to full visibility — ${BRAND_NAME} equips sales leaders with the conversation intelligence to drive consistent, measurable performance across every team.`}
          variant="dark"
        />

        {/* Value Pillars */}
        <div
          ref={pillarsRef}
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-5 mb-16 md:mb-20"
        >
          {valuePillars.map((pillar) => (
            <div
              key={pillar.title}
              className="card-dark group cursor-default flex flex-col"
            >
              <div className="w-10 h-10 rounded-full bg-brand-green/10 flex items-center justify-center mb-4 group-hover:bg-brand-green/20 transition-colors duration-200">
                <pillar.icon
                  className="w-5 h-5 text-brand-green"
                  strokeWidth={1.5}
                />
              </div>
              <h4 className="text-heading-5 text-white mb-2">
                {pillar.title}
              </h4>
              <p className="text-body-sm text-on-dark-muted leading-relaxed flex-1">
                {pillar.description}
              </p>
            </div>
          ))}
        </div>

        {/* What SAMAA Makes Visible */}
        <div ref={visibilityRef} className="mb-16 md:mb-20">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 items-center">
            {/* Text */}
            <div>
              <span className="badge-section mb-4 inline-block bg-brand-green/10 text-brand-green">
                WHAT {BRAND_NAME} MAKES VISIBLE
              </span>
              <h3 className="text-heading-3 text-white mb-6">
                Why deals move forward—or stall
              </h3>
              <ul className="space-y-4">
                {visibilityItems.map((item) => (
                  <li key={item} className="flex items-start gap-3">
                    <CheckCircle2
                      className="w-5 h-5 text-brand-green flex-shrink-0 mt-0.5"
                      strokeWidth={1.5}
                    />
                    <span className="text-body-md text-on-dark-muted">{item}</span>
                  </li>
                ))}
              </ul>
              <p className="text-body-md-medium text-white mt-6 pt-6 border-t border-hairline-dark">
                Act on issues early—before they affect results.
              </p>
            </div>

            {/* Image */}
            <div>
              <img
                src={dashboardImg}
                alt="Sales leader and team member having a coaching conversation"
                className="w-full rounded-lg"
              />
            </div>
          </div>
        </div>

        {/* Why Sales Leadership Choose SAMAA */}
        <div ref={choiceRef} className="mb-16 md:mb-20">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 items-center">
            {/* Image */}
            <div className="order-last lg:order-first">
              <img
                src={communicationImg}
                alt="Sales leader viewing SAMAA AI Dashboard"
                 className="w-full rounded-lg"
                // className="w-full rounded-lg border border-hairline-dark shadow-mockup"
              />
            </div>

            {/* Text */}
            <div>
              <span className="badge-section mb-4 inline-block bg-brand-green/10 text-brand-green">
                WHY SALES LEADERSHIP CHOOSE {BRAND_NAME}
              </span>
              <h3 className="text-heading-3 text-white mb-6">
                Clear, actionable intelligence
              </h3>
              <ul className="space-y-4">
                {choiceItems.map((item) => (
                  <li key={item} className="flex items-start gap-3">
                    <span className="w-5 h-5 rounded-full bg-brand-green/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                      <span className="w-2 h-2 rounded-full bg-brand-green" />
                    </span>
                    <span className="text-body-md text-on-dark-muted">{item}</span>
                  </li>
                ))}
              </ul>
              <p className="text-body-md-medium text-white mt-6 pt-6 border-t border-hairline-dark">
                Get the visibility needed to coach better, improve performance, and drive growth.
              </p>
            </div>
          </div>
        </div>

        {/* Bottom CTA */}
        <div ref={ctaRef} className="text-center max-w-2xl mx-auto">
          <div className="border-t border-hairline-dark pt-10">
            <h3 className="text-heading-3 text-white mb-4">
              Lead sales teams with complete visibility and zero guesswork
            </h3>
            <p className="text-body-md text-on-dark-muted mb-8">
              {BRAND_NAME} helps sales leaders improve execution, consistency, and rep
              confidence, one conversation at a time.
            </p>
            <button className="btn-accent group">
              See {BRAND_NAME} in Action
              <ArrowRight className="w-4 h-4 ml-2 inline-block group-hover:translate-x-0.5 transition-transform duration-150" />
            </button>
          </div>
        </div>
      </div>
    </section>
  );
};

export default SystemArchitectureSection;
