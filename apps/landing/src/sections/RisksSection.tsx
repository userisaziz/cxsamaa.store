import React from 'react';
import SectionHeader from '@/components/SectionHeader';
import { useScrollReveal } from '@/hooks/useScrollReveal';

const risks = [
  {
    risk: 'Audio quality',
    mitigation: 'Noise suppression algorithms and comprehensive device testing protocols',
    color: '#f59e0b',
  },
  {
    risk: 'Employee adoption',
    mitigation: 'Simple one-tap wearable workflow with minimal training required',
    color: '#3772cf',
  },
  {
    risk: 'Upload failures',
    mitigation: 'Local caching with automatic retry mechanisms and offline queue',
    color: '#ef4444',
  },
  {
    risk: 'Data privacy concerns',
    mitigation: 'Role-based access controls and configurable data retention policies',
    color: '#00d4a4',
  },
  {
    risk: 'AI accuracy',
    mitigation: 'Human review workflows and continuous model improvement pipeline',
    color: '#3772cf',
  },
  {
    risk: 'Enterprise scaling',
    mitigation: 'Cloud-native distributed architecture with horizontal scaling',
    color: '#00d4a4',
  },
];

const RisksSection: React.FC = () => {
  const desktopRef = useScrollReveal<HTMLTableSectionElement>({ stagger: 0.06 });
  const mobileRef = useScrollReveal<HTMLDivElement>({ stagger: 0.06 });

  return (
    <section data-dark-section className="bg-canvas-dark section-padding">
      <div className="container-main">
        <SectionHeader
          badge="RISK MANAGEMENT"
          heading="Identified Risks & Mitigations"
          description="Proactive risk identification and mitigation strategies ensure reliable platform delivery."
          variant="dark"
        />

        {/* Desktop Table */}
        <div className="hidden md:block overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-white/5">
                <th className="text-left text-body-sm-medium text-white py-3 px-5 w-[35%]">
                  Risk
                </th>
                <th className="text-left text-body-sm-medium text-white py-3 px-5 w-[65%]">
                  Mitigation
                </th>
              </tr>
            </thead>
            <tbody ref={desktopRef}>
              {risks.map((item) => (
                <tr
                  key={item.risk}
                  className="border-b border-hairline-dark"
                >
                  <td className="py-4 px-5">
                    <div className="flex items-center gap-3">
                      <span
                        className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                        style={{ backgroundColor: item.color }}
                      />
                      <span className="text-body-sm text-white">{item.risk}</span>
                    </div>
                  </td>
                  <td className="py-4 px-5 text-body-sm text-on-dark-muted">
                    {item.mitigation}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Mobile Cards */}
        <div className="md:hidden space-y-4" ref={mobileRef}>
          {risks.map((item) => (
            <div key={item.risk} className="card-dark">
              <div className="flex items-center gap-3 mb-2">
                <span
                  className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                  style={{ backgroundColor: item.color }}
                />
                <span className="text-body-sm-medium text-white">{item.risk}</span>
              </div>
              <p className="text-body-sm text-on-dark-muted pl-4">
                {item.mitigation}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default RisksSection;
