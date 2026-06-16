import React from 'react';
import { Link } from 'react-router';
import { CheckCircle2 } from 'lucide-react';
import SectionHeader from '@/components/SectionHeader';
import { useScrollReveal } from '@/hooks/useScrollReveal';
import { roles } from '@/data/roles';
import { BRAND_NAME } from '@/constants/brand';

const RoleCard: React.FC<{ slug: string; role: (typeof roles)[0] }> = ({
  slug,
  role,
}) => {
  const isDark = role.slug === 'executive-leadership';
  const Icon = role.icon;

  return (
    <div
      className={`rounded-xl p-6 md:p-8 border transition-colors duration-200 ${
        isDark
          ? 'bg-surface-dark-card border-hairline-dark'
          : 'bg-canvas-pure border-hairline'
      }`}
    >
      {/* Icon */}
      <div
        className={`w-12 h-12 rounded-full flex items-center justify-center mb-5 ${
          isDark ? 'bg-brand-green/10' : 'bg-brand-green-soft'
        }`}
      >
        <Icon
          className={`w-6 h-6 ${isDark ? 'text-brand-green' : 'text-brand-green'}`}
          strokeWidth={1.5}
        />
      </div>

      {/* Title */}
      <h3
        className={`text-heading-4 mb-2 ${
          isDark ? 'text-white' : 'text-ink'
        }`}
      >
        {role.role}
      </h3>

      {/* Tagline */}
      <p
        className={`text-body-sm mb-4 ${
          isDark ? 'text-brand-green' : 'text-brand-green'
        }`}
      >
        {role.tagline}
      </p>

      {/* Divider */}
      <div
        className={`h-px mb-5 ${
          isDark ? 'bg-hairline-dark' : 'bg-hairline'
        }`}
      />

      {/* Features */}
      <ul className="space-y-3 mb-5">
        {role.dashboardFeatures.map((feature) => (
          <li key={feature} className="flex items-start gap-3">
            <CheckCircle2
              className={`w-5 h-5 ${isDark ? 'text-brand-green' : 'text-brand-green'} flex-shrink-0 mt-0.5`}
              strokeWidth={1.5}
            />
            <span
              className={`text-body-sm ${
                isDark ? 'text-on-dark-muted' : 'text-charcoal'
              }`}
            >
              {feature}
            </span>
          </li>
        ))}
      </ul>

      {/* Outcome */}
      <p
        className={`text-body-sm mb-5 ${
          isDark ? 'text-on-dark-muted' : 'text-charcoal'
        }`}
      >
        <span className="font-semibold">Result:</span> {role.outcome}
      </p>

      {/* Learn More Link */}
      <Link
        to={`/roles/${slug}`}
        className={`text-body-sm font-medium inline-flex items-center gap-1 transition-colors duration-150 ${
          isDark
            ? 'text-brand-green hover:text-brand-green/80'
            : 'text-brand-green hover:text-brand-green/80'
        }`}
      >
        Learn More →
      </Link>
    </div>
  );
};

const RolesFeaturesSection: React.FC = () => {
  const gridRef = useScrollReveal<HTMLDivElement>({ stagger: 0.12, y: 30 });

  return (
    <section className="bg-canvas section-padding">
      <div className="container-main">
        <SectionHeader
          badge="ROLES"
          heading="Built for Every Role in Retail"
          description={`From store managers to executive leadership, ${BRAND_NAME} delivers the right insights to the right people—turning customer conversations into measurable business outcomes.`}
        />

        <div
          ref={gridRef}
          className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-5xl mx-auto"
        >
          {roles.map((role) => (
            <RoleCard key={role.slug} slug={role.slug} role={role} />
          ))}
        </div>
      </div>
    </section>
  );
};

export default RolesFeaturesSection;
