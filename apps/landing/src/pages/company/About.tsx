import React, { useEffect } from 'react';
import { useLocation } from 'react-router';
import { Target, Shield, Users, Lightbulb } from 'lucide-react';
import TopNavigation from '@/components/TopNavigation';
import Footer from '@/components/Footer';
import SectionHeader from '@/components/SectionHeader';
import { BRAND_NAME } from '@/constants/brand';

const values = [
  {
    icon: Users,
    title: 'Customer First',
    description: 'Every decision we make starts with understanding and serving our customers\' needs.',
  },
  {
    icon: Lightbulb,
    title: 'Innovation',
    description: 'We push the boundaries of what\'s possible with AI to deliver transformative retail intelligence.',
  },
  {
    icon: Shield,
    title: 'Trust & Privacy',
    description: 'We handle customer data with the highest standards of security and ethical responsibility.',
  },
  {
    icon: Target,
    title: 'Results Driven',
    description: 'We measure success by the tangible outcomes and ROI we deliver to our partners.',
  },
];

const stats = [
  { value: '10K+', label: 'Stores Powered' },
  { value: '50M+', label: 'Conversations Analyzed' },
  { value: '98%', label: 'Customer Satisfaction' },
  { value: '35%', label: 'Avg. Performance Uplift' },
];

const About: React.FC = () => {
  const location = useLocation();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);

  return (
    <div className="font-inter">
      <TopNavigation />
      <main className="pt-16">
        {/* Hero */}
        <section className="section-padding bg-gradient-to-b from-canvas to-white">
          <div className="container-main">
            <SectionHeader
              badge="ABOUT US"
              heading="Transforming Retail Through AI-Powered Conversations"
              description={`${BRAND_NAME} was founded with a simple mission: help retailers unlock the hidden intelligence in every customer conversation.`}
            />

            {/* Story */}
            <div className="max-w-3xl mx-auto mt-8 space-y-6">
              <p className="text-body-md text-charcoal leading-relaxed">
                Founded in 2024, {BRAND_NAME} emerged from a simple observation: retail stores generate thousands of customer conversations every day, yet most of this valuable intelligence goes uncaptured. Store managers lack visibility into what's actually happening on the sales floor, and coaching opportunities are missed.
              </p>
              <p className="text-body-md text-charcoal leading-relaxed">
                Our team of AI researchers, retail veterans, and software engineers came together to build a platform that captures, analyzes, and transforms in-store conversations into actionable business intelligence. Today, {BRAND_NAME} powers thousands of retail locations worldwide, helping brands improve sales performance, enhance customer experiences, and build stronger teams.
              </p>
            </div>
          </div>
        </section>

        {/* Stats */}
        <section className="section-padding bg-surface-soft">
          <div className="container-main">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
              {stats.map((stat) => (
                <div key={stat.label} className="text-center">
                  <div className="text-display-lg font-semibold text-brand-green mb-1">{stat.value}</div>
                  <div className="text-body-sm text-charcoal">{stat.label}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Values */}
        <section className="section-padding">
          <div className="container-main">
            <h3 className="text-heading-3 text-ink text-center mb-8">Our Core Values</h3>
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
              {values.map((value) => (
                <div key={value.title} className="card-feature text-center">
                  <div className="w-12 h-12 rounded-lg bg-brand-green/10 flex items-center justify-center mx-auto mb-4">
                    <value.icon className="w-6 h-6 text-brand-green" strokeWidth={1.5} />
                  </div>
                  <h4 className="text-heading-5 text-ink mb-2">{value.title}</h4>
                  <p className="text-body-sm text-charcoal">{value.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="section-padding bg-canvas-dark">
          <div className="container-main text-center">
            <h2 className="text-heading-2 text-white mb-4">Join Us on Our Mission</h2>
            <p className="text-body-md text-on-dark-muted max-w-xl mx-auto mb-8">
              We're always looking for talented people who share our passion for transforming retail through AI.
            </p>
            <button className="btn-accent">View Open Positions</button>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
};

export default About;
