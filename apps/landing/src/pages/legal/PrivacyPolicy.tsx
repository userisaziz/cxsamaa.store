import React, { useEffect } from 'react';
import { useLocation } from 'react-router';
import TopNavigation from '@/components/TopNavigation';
import Footer from '@/components/Footer';
import SectionHeader from '@/components/SectionHeader';

const PrivacyPolicy: React.FC = () => {
  const location = useLocation();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);

  return (
    <div className="font-inter">
      <TopNavigation />
      <main className="pt-16">
        <section className="section-padding bg-gradient-to-b from-canvas to-white">
          <div className="container-main max-w-3xl">
            <SectionHeader
              badge="PRIVACY POLICY"
              heading="Privacy Policy"
              description="Last updated: May 1, 2026"
            />

            <div className="space-y-8 text-body-md text-charcoal leading-relaxed">
              <section>
                <h3 className="text-heading-4 text-ink mb-3">1. Introduction</h3>
                <p>
                  SAMAA ("we," "our," or "us") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our platform and services.
                </p>
              </section>

              <section>
                <h3 className="text-heading-4 text-ink mb-3">2. Information We Collect</h3>
                <p className="mb-3">We collect information that you provide directly to us, including:</p>
                <ul className="list-disc pl-6 space-y-2">
                  <li>Account registration information (name, email address, company name)</li>
                  <li>Billing and payment information</li>
                  <li>Audio recordings of in-store conversations (with appropriate consent)</li>
                  <li>Usage data and analytics from our platform</li>
                  <li>Communications with our support team</li>
                </ul>
              </section>

              <section>
                <h3 className="text-heading-4 text-ink mb-3">3. How We Use Your Information</h3>
                <p className="mb-3">We use the collected information for the following purposes:</p>
                <ul className="list-disc pl-6 space-y-2">
                  <li>To provide, maintain, and improve our services</li>
                  <li>To process transactions and send related information</li>
                  <li>To analyze conversation data and generate insights</li>
                  <li>To communicate with you about our services, updates, and support</li>
                  <li>To detect, prevent, and address technical issues and fraud</li>
                  <li>To comply with legal obligations</li>
                </ul>
              </section>

              <section>
                <h3 className="text-heading-4 text-ink mb-3">4. Data Protection</h3>
                <p>
                  We implement appropriate technical and organizational measures to protect your personal information. This includes encryption at rest and in transit, access controls, regular security audits, and employee training on data protection practices.
                </p>
              </section>

              <section>
                <h3 className="text-heading-4 text-ink mb-3">5. Data Retention</h3>
                <p>
                  We retain your information for as long as your account is active or as needed to provide you services. We will retain and use your information as necessary to comply with our legal obligations, resolve disputes, and enforce our agreements.
                </p>
              </section>

              <section>
                <h3 className="text-heading-4 text-ink mb-3">6. Your Rights</h3>
                <p className="mb-3">Depending on your location, you may have the following rights regarding your personal data:</p>
                <ul className="list-disc pl-6 space-y-2">
                  <li>Right to access your personal data</li>
                  <li>Right to rectify inaccurate data</li>
                  <li>Right to delete your data (right to be forgotten)</li>
                  <li>Right to restrict processing</li>
                  <li>Right to data portability</li>
                  <li>Right to object to processing</li>
                </ul>
              </section>

              <section>
                <h3 className="text-heading-4 text-ink mb-3">7. Third-Party Services</h3>
                <p>
                  We may employ third-party companies and individuals to facilitate our services, provide service-related services, or assist us in analyzing how our services are used. These third parties have access to your personal information only to perform these tasks on our behalf and are obligated not to disclose or use it for any other purpose.
                </p>
              </section>

              <section>
                <h3 className="text-heading-4 text-ink mb-3">8. Contact Us</h3>
                <p>
                  If you have any questions about this Privacy Policy, please contact our Data Protection Officer at privacy@samaa.ai or write to us at 548 Market St, Suite 101, San Francisco, CA 94104.
                </p>
              </section>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
};

export default PrivacyPolicy;
