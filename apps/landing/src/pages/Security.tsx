import React, { useEffect } from 'react';
import { useLocation } from 'react-router';
import { Shield, Lock, Eye, FileCheck, Server, KeyRound, UserCheck, AlertTriangle } from 'lucide-react';
import TopNavigation from '@/components/TopNavigation';
import Footer from '@/components/Footer';
import SectionHeader from '@/components/SectionHeader';
import { BRAND_NAME } from '@/constants/brand';

const securityItems = [
  {
    icon: Lock,
    title: 'Encryption at Rest & In Transit',
    description: 'All data is encrypted using AES-256 at rest and TLS 1.3 in transit. Audio files are encrypted at the edge before transmission.',
  },
  {
    icon: KeyRound,
    title: 'Access Control & Authentication',
    description: 'Role-based access control (RBAC) with multi-factor authentication. Granular permissions ensure users only access what they need.',
  },
  {
    icon: Eye,
    title: 'Data Privacy & Anonymization',
    description: 'Personally identifiable information is automatically detected and anonymized. Conversations are processed without storing raw audio by default.',
  },
  {
    icon: FileCheck,
    title: 'Compliance & Certifications',
    description: 'SOC 2 Type II compliant, GDPR and CCPA ready. Regular third-party audits validate our security controls and data handling practices.',
  },
  {
    icon: Server,
    title: 'Infrastructure Security',
    description: 'Cloud infrastructure protected by WAF, DDoS mitigation, and intrusion detection systems. All access logged and monitored 24/7.',
  },
  {
    icon: UserCheck,
    title: 'Employee & Process Security',
    description: 'Background-checked staff, security training programs, and strict need-to-know data access policies. Code reviews mandatory for all deployments.',
  },
  {
    icon: Shield,
    title: 'Incident Response',
    description: '24/7 security monitoring with automated alerting. Documented incident response plan tested quarterly with dedicated response team.',
  },
  {
    icon: AlertTriangle,
    title: 'Vulnerability Management',
    description: 'Continuous vulnerability scanning, penetration testing, and responsible disclosure program. Critical patches deployed within 24 hours.',
  },
];

const Security: React.FC = () => {
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
              badge="SECURITY"
              heading="Enterprise Security You Can Trust"
              description={`${BRAND_NAME} is built with security-first principles. We protect your data at every layer with industry-leading practices and compliance certifications.`}
            />

            <div className="grid md:grid-cols-2 gap-6 mt-8">
              {securityItems.map((item) => (
                <div key={item.title} className="card-feature">
                  <div className="flex items-start gap-4">
                    <div className="w-10 h-10 rounded-lg bg-brand-green/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                      <item.icon className="w-5 h-5 text-brand-green" strokeWidth={1.5} />
                    </div>
                    <div>
                      <h3 className="text-heading-5 text-ink mb-1">{item.title}</h3>
                      <p className="text-body-sm text-charcoal">{item.description}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Compliance Badges */}
        <section className="section-padding bg-surface-soft">
          <div className="container-main text-center">
            <h3 className="text-heading-4 text-ink mb-8">Certifications & Compliance</h3>
            <div className="flex flex-wrap justify-center gap-8 items-center">
              {['SOC 2 Type II', 'GDPR Compliant', 'CCPA Ready', 'ISO 27001', 'HIPAA Eligible', 'PCI DSS'].map((badge) => (
                <div key={badge} className="card-base flex items-center gap-2 px-6 py-3">
                  <Shield className="w-4 h-4 text-brand-green" strokeWidth={1.5} />
                  <span className="text-body-sm-medium text-ink">{badge}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="section-padding bg-canvas-dark">
          <div className="container-main text-center">
            <h2 className="text-heading-2 text-white mb-4">Security Is Our Foundation</h2>
            <p className="text-body-md text-on-dark-muted max-w-xl mx-auto mb-8">
              Download our security whitepaper or contact our security team for detailed information.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <button className="btn-accent">Download Security Whitepaper</button>
              <button className="btn-on-dark">Contact Security Team</button>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
};

export default Security;
