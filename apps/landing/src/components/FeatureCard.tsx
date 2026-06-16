import React from 'react';
import type { LucideIcon } from 'lucide-react';

interface FeatureCardProps {
  icon: LucideIcon;
  title: string;
  description: string;
  variant?: 'light' | 'dark';
}

const FeatureCard: React.FC<FeatureCardProps> = ({
  icon: Icon,
  title,
  description,
  variant = 'light',
}) => {
  const isDark = variant === 'dark';

  return (
    <div
      className={`rounded-lg p-6 border transition-all duration-200 group hover:border-brand-green/30 hover:shadow-brand-glow ${
        isDark
          ? 'bg-surface-dark-card border-hairline-dark'
          : 'bg-canvas-pure border-hairline'
      }`}
    >
      <div className="w-10 h-10 rounded-full bg-brand-green-soft flex items-center justify-center mb-4 group-hover:bg-brand-green/20 transition-colors">
        <Icon className="w-5 h-5 text-brand-green" strokeWidth={1.5} />
      </div>
      <h3
        className={`text-heading-5 mb-2 ${isDark ? 'text-white' : 'text-ink'}`}
      >
        {title}
      </h3>
      <p className={`text-body-sm ${isDark ? 'text-on-dark-muted' : 'text-slate'}`}>
        {description}
      </p>
    </div>
  );
};

export default React.memo(FeatureCard);
