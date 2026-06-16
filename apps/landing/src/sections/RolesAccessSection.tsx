import React from 'react';
import { Info } from 'lucide-react';
import SectionHeader from '@/components/SectionHeader';
import { useScrollReveal } from '@/hooks/useScrollReveal';

const roles = [
  {
    name: 'Brand Head',
    desc: 'Full platform access. Can create users, roles, manage stores, and access all analytics.',
    tags: ['All Regions', 'All Stores', 'All Users', 'Custom Roles', 'Full Analytics'],
    opacity: 1,
  },
  {
    name: 'Regional Manager',
    desc: 'Can access assigned regions and all stores/areas within those regions.',
    tags: ['Assigned Regions', 'Regional Analytics', 'Store Comparison'],
    opacity: 0.8,
  },
  {
    name: 'Area Manager',
    desc: 'Can access assigned areas and stores. Can view team performance across managed locations.',
    tags: ['Assigned Areas', 'Area Analytics', 'Team Performance'],
    opacity: 0.6,
  },
  {
    name: 'Store Manager',
    desc: 'Can access assigned store data, team performance, and coaching reports.',
    tags: ['Assigned Store', 'Team Analytics', 'Coaching Reports'],
    opacity: 0.4,
  },
  {
    name: 'Salesperson',
    desc: 'Can only access personal performance information and coaching recommendations.',
    tags: ['Personal Data', 'Performance Score', 'Coaching'],
    opacity: 0.2,
  },
];

const RolesAccessSection: React.FC = () => {
  const rolesRef = useScrollReveal<HTMLDivElement>({ x: -20, stagger: 0.1 });

  return (
    <section data-dark-section className="bg-canvas-dark section-padding">
      <div className="container-main">
        <SectionHeader
          badge="IDENTITY & ACCESS"
          heading="Enterprise-Grade RBAC"
          description="Role-based access control with five predefined levels. Brand Heads can create custom roles and define granular permissions."
          variant="dark"
        />

        <div ref={rolesRef} className="space-y-4 max-w-4xl mx-auto">
          {roles.map((role) => (
            <div
              key={role.name}
              className="card-dark relative overflow-hidden"
            >
              {/* Access indicator */}
              <div
                className="absolute left-0 top-0 bottom-0 w-1"
                style={{
                  backgroundColor: `rgba(0, 212, 164, ${role.opacity})`,
                }}
              />
              <div className="pl-5">
                <h4 className="text-heading-5 text-white mb-1">{role.name}</h4>
                <p className="text-body-sm text-on-dark-muted mb-3">
                  {role.desc}
                </p>
                <div className="flex flex-wrap gap-2">
                  {role.tags.map((tag) => (
                    <span
                      key={tag}
                      className="badge-tag"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-12 text-center max-w-xl mx-auto flex items-start justify-center gap-2">
          <Info className="w-4 h-4 text-steel flex-shrink-0 mt-0.5" strokeWidth={1.5} />
          <p className="text-body-sm text-on-dark-muted">
            Brand Heads can create custom roles, define permissions, share resources,
            and delegate responsibilities across the organization.
          </p>
        </div>
      </div>
    </section>
  );
};

export default RolesAccessSection;
