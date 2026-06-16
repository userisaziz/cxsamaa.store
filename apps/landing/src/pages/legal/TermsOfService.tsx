import React, { useEffect } from 'react';
import { useLocation } from 'react-router';
import TopNavigation from '@/components/TopNavigation';
import Footer from '@/components/Footer';
import SectionHeader from '@/components/SectionHeader';
import { BRAND_NAME } from '@/constants/brand';

const TermsOfService: React.FC = () => {
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
              badge="TERMS OF SERVICE"
              heading="Terms of Service"
              description="Last updated: May 1, 2026"
            />

            <div className="space-y-8 text-body-md text-charcoal leading-relaxed">
              <section>
                <h3 className="text-heading-4 text-ink mb-3">1. Acceptance of Terms</h3>
                <p>
                  By accessing or using {BRAND_NAME}'s platform and services ("Services"), you agree to be bound by these Terms of Service. If you do not agree to these terms, please do not use our Services.
                </p>
              </section>

              <section>
                <h3 className="text-heading-4 text-ink mb-3">2. Description of Services</h3>
                <p>
                  {BRAND_NAME} provides an AI-powered retail performance intelligence platform that captures, analyzes, and transforms in-store conversations into actionable business insights. The specific features and capabilities of our Services are described on our website and in our service documentation.
                </p>
              </section>

              <section>
                <h3 className="text-heading-4 text-ink mb-3">3. User Responsibilities</h3>
                <p className="mb-3">As a user of our Services, you agree to:</p>
                <ul className="list-disc pl-6 space-y-2">
                  <li>Provide accurate and complete information when creating an account</li>
                  <li>Maintain the security of your account credentials</li>
                  <li>Use the Services in compliance with all applicable laws and regulations</li>
                  <li>Obtain all necessary consents for audio recording and data collection</li>
                  <li>Not misuse or attempt to circumvent the Services' security measures</li>
                </ul>
              </section>

              <section>
                <h3 className="text-heading-4 text-ink mb-3">4. Intellectual Property</h3>
                <p>
                  The {BRAND_NAME} platform, including its software, algorithms, user interface, and generated insights, is protected by intellectual property laws. You are granted a limited, non-exclusive, non-transferable license to use the Services in accordance with your subscription plan.
                </p>
              </section>

              <section>
                <h3 className="text-heading-4 text-ink mb-3">5. Data Ownership</h3>
                <p>
                  You retain ownership of all data and audio recordings you upload or capture through our Services. {BRAND_NAME} is granted a limited license to process this data solely for the purpose of providing and improving our Services.
                </p>
              </section>

              <section>
                <h3 className="text-heading-4 text-ink mb-3">6. Service Level</h3>
                <p>
                  We strive to provide reliable and uninterrupted access to our Services. However, we cannot guarantee that the Services will be available at all times. We reserve the right to perform maintenance, updates, and upgrades as needed.
                </p>
              </section>

              <section>
                <h3 className="text-heading-4 text-ink mb-3">7. Limitation of Liability</h3>
                <p>
                  {BRAND_NAME} shall not be liable for any indirect, incidental, special, consequential, or punitive damages resulting from your use of or inability to use our Services. Our total liability shall not exceed the amount paid by you for the Services during the twelve months preceding the claim.
                </p>
              </section>

              <section>
                <h3 className="text-heading-4 text-ink mb-3">8. Termination</h3>
                <p>
                  Either party may terminate this agreement at any time with written notice. Upon termination, your access to the Services will be discontinued, and your data will be handled in accordance with our data retention policy.
                </p>
              </section>

              <section>
                <h3 className="text-heading-4 text-ink mb-3">9. Changes to Terms</h3>
                <p>
                  We reserve the right to modify these terms at any time. We will notify users of material changes via email or through our platform. Continued use of the Services after changes constitutes acceptance of the new terms.
                </p>
              </section>

              <section>
                <h3 className="text-heading-4 text-ink mb-3">10. Contact</h3>
                <p>
                  For questions about these Terms of Service, please contact us at legal@samaa.ai.
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

export default TermsOfService;
