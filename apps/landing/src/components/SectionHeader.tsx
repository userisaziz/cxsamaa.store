import React from 'react';

interface SectionHeaderProps {
  badge: string;
  heading: string;
  description?: string;
  variant?: 'light' | 'dark';
}

const SectionHeader: React.FC<SectionHeaderProps> = ({
  badge,
  heading,
  description,
  variant = 'light',
}) => {
  const isDark = variant === 'dark';

  return (
    <div className="text-center mb-12 md:mb-16">
      <span
        className={`inline-block px-3 py-1 text-micro-uppercase rounded-full tracking-wider mb-6 ${
          isDark
            ? 'bg-brand-green/15 text-brand-green'
            : 'bg-brand-green-soft text-brand-green'
        }`}
      >
        {badge}
      </span>
      <h2
        className={`text-heading-2 md:text-heading-1 ${
          isDark ? 'text-white' : 'text-ink'
        }`}
      >
        {heading}
      </h2>
      {description && (
        <p
          className={`text-body-md mt-4 max-w-2xl mx-auto ${
            isDark ? 'text-on-dark-muted' : 'text-charcoal'
          }`}
        >
          {description}
        </p>
      )}
    </div>
  );
};

export default React.memo(SectionHeader);
