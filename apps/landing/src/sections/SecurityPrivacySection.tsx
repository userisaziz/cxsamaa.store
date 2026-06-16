import React from 'react';
import { Lock, ShieldCheck, Users, FileText, Clock, Database, Key } from 'lucide-react';
import SectionHeader from '@/components/SectionHeader';
import FeatureCard from '@/components/FeatureCard';
import { useScrollReveal } from '@/hooks/useScrollReveal';

const securityFeatures = [
  {
    icon: Lock,
    title: 'AES-256 Encryption',
    description: 'All audio files and conversation data encrypted at rest with industry-standard AES-256 encryption.',
  },
  {
    icon: ShieldCheck,
    title: 'TLS Encryption',
    description: 'All data in transit protected with TLS 1.3. End-to-end encryption from device to dashboard.',
  },
  {
    icon: Users,
    title: 'Role-Based Access',
    description: 'Granular RBAC ensures users only access data they are authorized to see. No exceptions.',
  },
  {
    icon: FileText,
    title: 'Audit Logging',
    description: 'Complete audit trail of all data access, user actions, and system events. Immutable logs.',
  },
  {
    icon: Clock,
    title: 'Data Retention',
    description: 'Configurable data retention policies. Automatic purging based on organizational requirements.',
  },
  {
    icon: Database,
    title: 'Secure Storage',
    description: 'Enterprise cloud storage with redundancy, backup, and disaster recovery capabilities.',
  },
  {
    icon: Key,
    title: 'Future: SSO & MFA',
    description: 'SSO, MFA, SCIM provisioning, and compliance reporting on the enterprise roadmap.',
  },
];

const SecurityPrivacySection: React.FC = () => {
  const gridRef = useScrollReveal<HTMLDivElement>({ stagger: 0.08, y: 30 });
  const infoRef = useScrollReveal<HTMLDivElement>({ y: 20, duration: 0.6 });

  return (
    <section id="security" data-dark-section className="bg-canvas-dark section-padding">
      <div className="container-main">
        <SectionHeader
          badge="SECURITY & PRIVACY"
          heading="Enterprise-Grade Security"
          description="Multi-layered security controls protect conversation data at rest and in transit. Privacy by design, not as an afterthought."
          variant="dark"
        />

        <div
          ref={gridRef}
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6"
        >
          {securityFeatures.map((feature) => (
            <FeatureCard
              key={feature.title}
              icon={feature.icon}
              title={feature.title}
              description={feature.description}
              variant="dark"
            />
          ))}
        </div>

        <div ref={infoRef} className="mt-12 max-w-2xl mx-auto card-dark border border-hairline-dark text-center py-4 px-6">
          <p className="text-body-sm text-on-dark-muted">
            Future enterprise capabilities include single sign-on (SSO), multi-factor
            authentication (MFA), SCIM user provisioning, and compliance reporting.
          </p>
        </div>
      </div>
    </section>
  );
};

export default SecurityPrivacySection;
