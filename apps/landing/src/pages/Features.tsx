import React, { useEffect } from 'react';
import { useLocation } from 'react-router';
import { AudioWaveform, Brain, Shield, BarChart3, Users, Layers } from 'lucide-react';
import TopNavigation from '@/components/TopNavigation';
import Footer from '@/components/Footer';
import SectionHeader from '@/components/SectionHeader';
import { BRAND_NAME } from '@/constants/brand';

const features = [
  {
    icon: AudioWaveform,
    title: 'Audio Collection',
    description: 'Capture in-store conversations with high-fidelity audio recording. Our system intelligently filters background noise and isolates customer-agent interactions.',
    color: 'text-brand-green',
    bgColor: 'bg-brand-green/10',
  },
  {
    icon: Brain,
    title: 'AI Intelligence',
    description: 'Proprietary AI processes conversations in real-time, extracting key insights, sentiment analysis, and actionable intelligence for retail optimization.',
    color: 'text-brand-blue',
    bgColor: 'bg-brand-blue/10',
  },
  {
    icon: Shield,
    title: 'Security & Privacy',
    description: 'Enterprise-grade encryption and compliance with data protection regulations. Conversations are anonymized and processed with privacy-first architecture.',
    color: 'text-semantic-success',
    bgColor: 'bg-brand-green/10',
  },
  {
    icon: BarChart3,
    title: 'Performance Analytics',
    description: 'Comprehensive dashboards and reports that transform raw conversation data into clear, actionable metrics for store performance improvement.',
    color: 'text-brand-blue',
    bgColor: 'bg-brand-blue/10',
  },
  {
    icon: Users,
    title: 'Team Management',
    description: 'Role-based access controls and team management tools that enable organizations to structure their coaching and review workflows effectively.',
    color: 'text-semantic-success',
    bgColor: 'bg-brand-green/10',
  },
  {
    icon: Layers,
    title: 'Scalable Architecture',
    description: `Cloud-native infrastructure that scales with your business. From single stores to enterprise deployments, ${BRAND_NAME} grows with you.`,
    color: 'text-brand-blue',
    bgColor: 'bg-brand-blue/10',
  },
];

const Features: React.FC = () => {
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
              badge="FEATURES"
              heading="Everything You Need to Transform Retail Performance"
              description={`${BRAND_NAME} combines cutting-edge audio AI with deep retail intelligence to deliver insights that drive measurable results.`}
            />

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mt-8">
              {features.map((feature) => (
                <div key={feature.title} className="card-feature group">
                  <div className={`w-12 h-12 rounded-lg ${feature.bgColor} flex items-center justify-center mb-4`}>
                    <feature.icon className={`w-6 h-6 ${feature.color}`} strokeWidth={1.5} />
                  </div>
                  <h3 className="text-heading-5 text-ink mb-2">{feature.title}</h3>
                  <p className="text-body-sm text-charcoal leading-relaxed">
                    {feature.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="section-padding bg-canvas-dark">
          <div className="container-main text-center">
            <h2 className="text-heading-2 text-white mb-4">Ready to Get Started?</h2>
            <p className="text-body-md text-on-dark-muted max-w-xl mx-auto mb-8">
              See how {BRAND_NAME} can transform your retail operations with AI-powered conversation intelligence.
            </p>
            <button className="btn-accent">Request a Demo</button>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
};

export default Features;
