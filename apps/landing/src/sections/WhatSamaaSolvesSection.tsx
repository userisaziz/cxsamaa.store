import React from 'react';
import SectionHeader from '@/components/SectionHeader';
import { useScrollReveal } from '@/hooks/useScrollReveal';
import { BRAND_NAME } from '@/constants/brand';

import storesImg from '@/assets/city2.png';
import monthlyImg from '@/assets/confused.png';
import communicationImg from '@/assets/stressed.jpeg';
import talkImg from '@/assets/talking.jpeg';

interface ProblemCard {
  id: string;
  title: string;
  description: string;
  image: string;
}

const problems: ProblemCard[] = [
  {
    id: 'store-performance',
    title: 'Store Performance Analysis',
    description:
      'Find What Top Stores Do Differently. Compare conversation quality across locations and uncover winning behaviors.',
    image: storesImg,
  },
  {
    id: 'coaching-support',
    title: 'New Store Coaching Support',
    description:
      'Train New Stores Faster. Use proven conversation patterns from top performers to accelerate success.',
    image: communicationImg,
  },
  {
    id: 'sales-drop',
    title: 'Sales Drop Investigation',
    description:
      'Understand Sales Declines Quickly. Identify changes in customer sentiment, objections, and sales execution.',
    image: monthlyImg,
  },
  {
    id: 'customer-preferences',
    title: 'Customer Preference Insights',
    description:
      'Hear What Customers Really Want. Capture real customer requests and align inventory with demand.',
    image: talkImg,
  },
];

const ProblemCard: React.FC<{ card: ProblemCard; index: number }> = ({
  card,
  index,
}) => {
  const gradients = [
    'from-emerald-50 to-teal-50/50',
    'from-green-50 to-emerald-50/50',
    'from-teal-50 to-cyan-50/50',
    'from-lime-50 to-green-50/50',
  ];

  return (
    <div
      className="group relative rounded-xl overflow-hidden bg-surface-dark-card border border-hairline-dark
                 min-h-[220px] transition-all duration-300 
                 hover:border-brand-green/50 hover:shadow-lg hover:shadow-brand-green/[0.15]"
    >
      {/* Background wash */}
      <div className={`absolute inset-0 bg-gradient-to-br ${gradients[index]} opacity-0 group-hover:opacity-10 transition-opacity duration-500`} />

      {/* Content area */}
      <div className="relative z-10 p-6 md:p-7">
        {/* Icon circle */}
        <div className="inline-flex items-center justify-center w-10 h-10 rounded-full bg-brand-green-soft mb-5">
          <svg className="w-5 h-5 text-brand-green" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} 
                  d={index === 0 ? 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z'
                   : index === 1 ? 'M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253'
                   : index === 2 ? 'M13 7h8m0 0v8m0-8l-8 8-4-4-6 6'
                   : 'M17 8h2a2 2 0 012 2v6a2 2 0 01-2 2h-2v4l-4-4H9a1.994 1.994 0 01-1.414-.586m0 0L11 14h4a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2v4l.586-.586z'}
            />
          </svg>
        </div>

        {/* Title */}
        <h3 className="text-lg md:text-xl font-semibold text-on-dark leading-tight mb-2">
          {card.title}
        </h3>

        {/* Description */}
        <p className="text-sm md:text-[15px] text-on-dark-muted leading-relaxed max-w-sm">
          {card.description}
        </p>
      </div>

      {/* Right image - subtle */}
      <div className="absolute right-0 top-0 bottom-0 w-[45%] pointer-events-none opacity-0.6 group-hover:opacity-90 transition-opacity duration-500">
        <img
          src={card.image}
          alt=""
          aria-hidden="true"
          className="w-full h-full object-cover object-center opacity-55"
        />
        <div className="absolute inset-y-0 left-0 w-[60%] bg-gradient-to-r from-surface-dark-card to-transparent" />
      </div>
    </div>
  );
};

const WhatSamaaSolvesSection: React.FC = () => {
  const gridRef = useScrollReveal<HTMLDivElement>({ stagger: 0.12, y: 30 });

  return (
    <section className="bg-canvas-dark section-padding">
      <div className="container-main">
        <SectionHeader
          badge={`WHAT ${BRAND_NAME} SOLVES`}
          heading="Making the Invisible, Actionable"
          description={`Four critical retail challenges that ${BRAND_NAME}'s conversation intelligence transforms from blind spots into competitive advantages.`}
          variant="dark"
        />

        <div
          ref={gridRef}
          className="grid grid-cols-1 md:grid-cols-2 gap-5 lg:gap-6"
        >
          {problems.map((card, index) => (
            <ProblemCard
              key={card.id}
              card={card}
              index={index}
            />
          ))}
        </div>

        {/* Bottom accent line */}
        <div className="mt-12 md:mt-16 flex items-center justify-center gap-4">
          <div className="h-px flex-1 max-w-[100px] bg-gradient-to-r from-transparent to-brand-green/40" />
          <div className="w-1.5 h-1.5 rounded-full bg-brand-green" />
          <span className="text-micro-uppercase tracking-widest text-on-dark-muted">
            Every conversation is a data point
          </span>
          <div className="w-1.5 h-1.5 rounded-full bg-brand-green" />
          <div className="h-px flex-1 max-w-[100px] bg-gradient-to-l from-transparent to-brand-green/40" />
        </div>
      </div>
    </section>
  );
};

export default WhatSamaaSolvesSection;
