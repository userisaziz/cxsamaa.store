import React from 'react';
import { User, Users, BarChart3, TrendingUp, Crown } from 'lucide-react';
import SectionHeader from '@/components/SectionHeader';
import { useScrollReveal } from '@/hooks/useScrollReveal';
import { BRAND_NAME } from '@/constants/brand';

const roles = [
  { icon: User, name: 'Salesperson', desc: 'Individual performance, coaching recommendations, conversation quality' },
  { icon: Users, name: 'Store Manager', desc: 'Team performance, daily coaching, conversion insights' },
  { icon: BarChart3, name: 'Area Manager', desc: 'Multi-store comparison, regional benchmarking' },
  { icon: TrendingUp, name: 'Regional Manager', desc: 'Region-wide analytics, trend identification' },
  { icon: Crown, name: 'Retail Head', desc: 'Enterprise intelligence, strategic reporting' },
];

const hierarchyNodes = [
  { label: 'Brand', example: 'Luxury Retail Group' },
  { label: 'Region', example: 'Riyadh' },
  { label: 'Area', example: 'North Riyadh' },
  { label: 'Store', example: 'Kingdom Mall' },
  { label: 'Sales Team', example: 'Store Employees' },
];

const ProductOverviewSection: React.FC = () => {
  const textRef = useScrollReveal<HTMLDivElement>({ stagger: 0.1 });
  const rolesRef = useScrollReveal<HTMLDivElement>({ stagger: 0.08 });
  const hierarchyRef = useScrollReveal<HTMLDivElement>({ y: 20, stagger: 0.12 });

  return (
    <section id="features" className="bg-canvas section-padding">
      <div className="container-main">
        <SectionHeader
          badge="PRODUCT OVERVIEW"
          heading="Built for Enterprise Retail Operations"
          description={`Every retail brand operates in a fully isolated environment with complete data separation. ${BRAND_NAME} provides role-specific intelligence across every level of your organization.`}
        />

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16">
          {/* Left Column - Text Content */}
          <div ref={textRef}>
            <div className="mb-10">
              <h3 className="text-heading-3 text-ink mb-4">The Retail Blind Spot</h3>
              <p className="text-body-md text-charcoal">
                Retail organizations invest heavily in ERP, CRM, POS, inventory, and
                workforce management systems. Yet the most critical performance driver —
                the interaction between customers and salespeople — remains invisible.
                {` ${BRAND_NAME} `}illuminates what happens in every conversation.
              </p>
            </div>

            <div className="mb-10">
              <h3 className="text-heading-3 text-ink mb-4">Complete Visibility</h3>
              <p className="text-body-md text-charcoal">
                {BRAND_NAME} captures in-store conversations through wearable devices,
                processes them through AI, and converts them into measurable insights
                across stores, teams, and individuals.
              </p>
            </div>

            <div>
              <h4 className="text-heading-4 text-ink mb-4">Role-Specific Intelligence</h4>
              <div ref={rolesRef} className="space-y-3">
                {roles.map((role) => (
                  <div
                    key={role.name}
                    className="card-base flex items-start gap-3 py-4 px-5"
                  >
                    <role.icon
                      className="w-5 h-5 text-brand-green flex-shrink-0 mt-0.5"
                      strokeWidth={1.5}
                    />
                    <div>
                      <span className="text-body-sm-medium text-ink">
                        {role.name}
                      </span>
                      <span className="text-body-sm text-slate ml-2">
                        — {role.desc}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right Column - Hierarchy Diagram */}
          <div className="flex items-center justify-center">
            <div ref={hierarchyRef} className="flex flex-col items-center w-full max-w-sm">
              {hierarchyNodes.map((node, index) => (
                <React.Fragment key={node.label}>
                  <div className="card-dark py-3 px-6 w-48 text-center">
                    <span className="text-body-sm-medium text-white block">
                      {node.label}
                    </span>
                    <span className="text-caption text-slate font-mono block mt-1">
                      {node.example}
                    </span>
                  </div>
                  {index < hierarchyNodes.length - 1 && (
                    <div className="relative w-0.5 h-6 bg-hairline-dark my-1">
                      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-brand-green animate-pulse-dot" />
                    </div>
                  )}
                </React.Fragment>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default ProductOverviewSection;
