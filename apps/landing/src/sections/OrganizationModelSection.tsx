import React from 'react';
import { Shield } from 'lucide-react';
import SectionHeader from '@/components/SectionHeader';
import { useScrollReveal } from '@/hooks/useScrollReveal';

const hierarchyNodes = [
  { label: 'Brand', example: 'Luxury Retail Group' },
  { label: 'Region', example: 'Riyadh' },
  { label: 'Area', example: 'North Riyadh' },
  { label: 'Store', example: 'Kingdom Mall' },
  { label: 'Sales Team', example: 'Store Employees' },
];

const OrganizationModelSection: React.FC = () => {
  const hierarchyRef = useScrollReveal<HTMLDivElement>({ y: 20, stagger: 0.12 });

  return (
    <section className="bg-surface section-padding">
      <div className="container-main">
        <SectionHeader
          badge="ORGANIZATION MODEL"
          heading="Complete Tenant Isolation"
          description="Every brand operates in a fully isolated environment. No brand can access another brand's data. Hierarchical access flows naturally from brand head to salesperson."
        />

        <div className="flex justify-center">
          <div
            ref={hierarchyRef}
            className="flex flex-col items-center max-w-xs w-full"
          >
            {hierarchyNodes.map((node, index) => (
              <React.Fragment key={node.label}>
                <div className="card-base py-3 px-8 w-full text-center">
                  <span className="text-body-sm-medium text-ink block">
                    {node.label}
                  </span>
                  <span className="text-caption text-slate font-mono block mt-1">
                    {node.example}
                  </span>
                </div>
                {index < hierarchyNodes.length - 1 && (
                  <div className="relative w-0.5 h-6 bg-hairline my-1">
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-brand-green animate-pulse-dot" />
                  </div>
                )}
              </React.Fragment>
            ))}
          </div>
        </div>

        <div className="mt-12 text-center max-w-xl mx-auto flex items-start justify-center gap-3">
          <Shield className="w-5 h-5 text-brand-green flex-shrink-0 mt-1" strokeWidth={1.5} />
          <p className="text-body-md-medium text-charcoal">
            Each tenant operates within a fully isolated environment. No brand can
            access another brand's data — guaranteed by architecture, not just policy.
          </p>
        </div>
      </div>
    </section>
  );
};

export default OrganizationModelSection;
