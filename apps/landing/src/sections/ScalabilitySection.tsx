import React, { useEffect, useRef, useState } from 'react';
import { Building2, TrendingUp, Zap, Activity } from 'lucide-react';
import SectionHeader from '@/components/SectionHeader';
import { useScrollReveal } from '@/hooks/useScrollReveal';
import { useReducedMotion } from '@/hooks/useReducedMotion';

const stats = [
  { value: 1000, suffix: '+', label: 'Stores per deployment' },
  { value: 10000, suffix: '+', label: 'Employees monitored' },
  { value: 1000000, suffix: '+', label: 'Conversations processed daily', display: '1M+' },
];

const features = [
  {
    icon: Building2,
    title: 'Multi-Tenant Architecture',
    description: 'Isolated tenant environments with zero cross-contamination. Each brand is a fully separate instance.',
  },
  {
    icon: TrendingUp,
    title: 'Horizontal Scaling',
    description: 'Add capacity by adding nodes. No architectural changes required as you grow.',
  },
  {
    icon: Zap,
    title: 'Event-Driven Processing',
    description: 'Asynchronous pipeline ensures no conversation waits. Real-time processing at scale.',
  },
  {
    icon: Activity,
    title: 'High Availability',
    description: 'Distributed infrastructure with automatic failover. 99.9% uptime SLA.',
  },
];

const AnimatedStat: React.FC<{
  value: number;
  suffix: string;
  display?: string;
  label: string;
  delay: number;
}> = ({ value, suffix, display, label, delay }) => {
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLDivElement>(null);
  const reducedMotion = useReducedMotion();
  const hasAnimated = useRef(false);

  useEffect(() => {
    if (!ref.current || hasAnimated.current) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !hasAnimated.current) {
          hasAnimated.current = true;

          if (reducedMotion) {
            setCount(value);
            return;
          }

          setTimeout(() => {
            const duration = 1500;
            const startTime = performance.now();

            const animate = (currentTime: number) => {
              const elapsed = currentTime - startTime;
              const progress = Math.min(elapsed / duration, 1);
              const eased = 1 - Math.pow(1 - progress, 3);
              setCount(Math.floor(eased * value));

              if (progress < 1) {
                requestAnimationFrame(animate);
              }
            };

            requestAnimationFrame(animate);
          }, delay);
        }
      },
      { threshold: 0.5 }
    );

    observer.observe(ref.current);
    return () => observer.disconnect();
  }, [value, delay, reducedMotion]);

  const formatNumber = (n: number) => {
    if (n >= 1000000) return (n / 1000000).toFixed(0) + 'M';
    if (n >= 1000) return (n / 1000).toFixed(0) + 'K';
    return n.toString();
  };

  return (
    <div ref={ref} className="text-center">
      <div className="text-5xl font-semibold text-brand-green mb-2">
        {display || formatNumber(count) + suffix}
      </div>
      <p className="text-body-sm text-slate">{label}</p>
    </div>
  );
};

const ScalabilitySection: React.FC = () => {
  const featuresRef = useScrollReveal<HTMLDivElement>({ stagger: 0.08, y: 30 });

  return (
    <section className="bg-surface section-padding">
      <div className="container-main">
        <SectionHeader
          badge="SCALABILITY & RELIABILITY"
          heading="Built for Global Retail Deployments"
          description="Cloud-native architecture designed to scale from a single store to a global retail network without compromise."
        />

        {/* Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-8 md:gap-12 mb-16 max-w-3xl mx-auto">
          {stats.map((stat, i) => (
            <AnimatedStat
              key={stat.label}
              value={stat.value}
              suffix={stat.suffix}
              display={stat.display}
              label={stat.label}
              delay={i * 200}
            />
          ))}
        </div>

        {/* Features Grid */}
        <div
          ref={featuresRef}
          className="grid grid-cols-1 sm:grid-cols-2 gap-6 max-w-3xl mx-auto"
        >
          {features.map((feature) => (
            <div key={feature.title} className="card-base">
              <feature.icon
                className="w-5 h-5 text-brand-green mb-3"
                strokeWidth={1.5}
              />
              <h4 className="text-heading-5 text-ink mb-2">{feature.title}</h4>
              <p className="text-body-sm text-slate">{feature.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default ScalabilitySection;
