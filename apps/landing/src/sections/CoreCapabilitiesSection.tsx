import React from 'react';
import { Mic, MessageSquare, AlertCircle, HeartPulse, ClipboardCheck, Target, BarChart3 } from 'lucide-react';
import SectionHeader from '@/components/SectionHeader';
import FeatureCard from '@/components/FeatureCard';
import { useScrollReveal } from '@/hooks/useScrollReveal';

const capabilities = [
  {
    icon: Mic,
    title: 'Conversation Capture',
    description: 'Capture retail conversations across all stores and locations with wearable devices. Every interaction becomes a data point.',
  },
  {
    icon: MessageSquare,
    title: 'Speech Intelligence',
    description: 'Convert audio into structured transcripts with speaker identification, timestamps, and multi-language support.',
  },
  {
    icon: AlertCircle,
    title: 'Objection Intelligence',
    description: 'Automatically detect customer objections — price concerns, product comparisons, approval needs, competitor references.',
  },
  {
    icon: HeartPulse,
    title: 'Sentiment Intelligence',
    description: 'Measure customer engagement and emotional sentiment throughout every conversation. Identify friction points.',
  },
  {
    icon: ClipboardCheck,
    title: 'SOP Compliance',
    description: 'Measure adherence to predefined sales processes — greeting quality, discovery, recommendations, upselling, closing.',
  },
  {
    icon: Target,
    title: 'Coaching Intelligence',
    description: 'Automatically identify coaching opportunities and improvement areas for every team member.',
  },
  {
    icon: BarChart3,
    title: 'Store Benchmarking',
    description: 'Compare stores, regions, teams, and employees to identify performance drivers and replicate best practices.',
  },
];

const CoreCapabilitiesSection: React.FC = () => {
  const gridRef = useScrollReveal<HTMLDivElement>({ stagger: 0.08, y: 40 });

  return (
    <section id="platform" className="bg-canvas-pure section-padding">
      <div className="container-main">
        <SectionHeader
          badge="CORE CAPABILITIES"
          heading="Seven Intelligence Engines"
          description="From conversation capture to coaching intelligence — a complete intelligence stack for retail operations."
        />

        <div
          ref={gridRef}
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6"
        >
          {capabilities.map((cap) => (
            <FeatureCard
              key={cap.title}
              icon={cap.icon}
              title={cap.title}
              description={cap.description}
            />
          ))}
        </div>
      </div>
    </section>
  );
};

export default CoreCapabilitiesSection;
