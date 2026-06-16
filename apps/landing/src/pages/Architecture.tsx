import React, { useEffect } from 'react';
import { useLocation } from 'react-router';
import { Cloud, Database, Cpu, Lock, Radio, Workflow } from 'lucide-react';
import TopNavigation from '@/components/TopNavigation';
import Footer from '@/components/Footer';
import SectionHeader from '@/components/SectionHeader';
import { BRAND_NAME } from '@/constants/brand';

const layers = [
  {
    icon: Radio,
    title: 'Data Collection Layer',
    description: 'Edge devices in retail locations capture audio with advanced noise cancellation. Data is encrypted at capture and streamed securely to the processing pipeline.',
    details: ['Multi-microphone array support', 'Real-time noise filtering', 'Encrypted edge processing', 'Low-latency streaming'],
  },
  {
    icon: Cpu,
    title: 'AI Processing Layer',
    description: 'Proprietary NLP models process conversations in real-time, extracting intent, sentiment, and actionable insights with high accuracy.',
    details: ['Fine-tuned retail language models', 'Real-time transcription engine', 'Sentiment analysis pipeline', 'Intent classification'],
  },
  {
    icon: Database,
    title: 'Data Storage Layer',
    description: 'Secure, scalable cloud storage with automated retention policies. Data is anonymized and indexed for fast retrieval and compliance.',
    details: ['Encrypted at rest (AES-256)', 'Automated retention management', 'Multi-region replication', 'Time-series optimization'],
  },
  {
    icon: Workflow,
    title: 'Analytics & Insights Layer',
    description: 'Transforms raw processed data into actionable dashboards, reports, and alerts tailored to retail performance metrics.',
    details: ['Custom dashboard builder', 'Automated insight generation', 'Trend analysis', 'Export & integration APIs'],
  },
  {
    icon: Lock,
    title: 'Security & Compliance Layer',
    description: 'End-to-end security infrastructure ensuring data protection across all layers, with comprehensive audit logging and access controls.',
    details: ['RBAC with granular permissions', 'Complete audit trail', 'SOC 2 compliance', 'GDPR/CCPA ready'],
  },
  {
    icon: Cloud,
    title: 'Infrastructure Layer',
    description: 'Cloud-native microservices architecture running on AWS, with auto-scaling, load balancing, and 99.9% uptime SLA.',
    details: ['AWS multi-AZ deployment', 'Auto-scaling infrastructure', 'CDN-backed delivery', 'Disaster recovery'],
  },
];

const Architecture: React.FC = () => {
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
              badge="ARCHITECTURE"
              heading="Enterprise-Grade Architecture Built for Scale"
              description={`${BRAND_NAME}'s multi-layer architecture ensures security, reliability, and performance from edge to cloud.`}
            />

            <div className="space-y-8 mt-8">
              {layers.map((layer, index) => (
                <div key={layer.title} className="card-feature">
                  <div className="flex flex-col md:flex-row md:items-start gap-6">
                    <div className="w-12 h-12 rounded-lg bg-brand-green/10 flex items-center justify-center flex-shrink-0">
                      <layer.icon className="w-6 h-6 text-brand-green" strokeWidth={1.5} />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <span className="text-caption-bold text-steel">0{index + 1}</span>
                        <h3 className="text-heading-5 text-ink">{layer.title}</h3>
                      </div>
                      <p className="text-body-sm text-charcoal mb-4 max-w-3xl">{layer.description}</p>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                        {layer.details.map((detail) => (
                          <span key={detail} className="text-caption text-steel bg-surface-soft px-3 py-1.5 rounded-md">
                            {detail}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="section-padding bg-canvas-dark">
          <div className="container-main text-center">
            <h2 className="text-heading-2 text-white mb-4">Built for Enterprise Reliability</h2>
            <p className="text-body-md text-on-dark-muted max-w-xl mx-auto mb-8">
              Our architecture is designed to meet the highest standards of security, scalability, and performance.
            </p>
            <button className="btn-accent">View Technical Documentation</button>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
};

export default Architecture;
