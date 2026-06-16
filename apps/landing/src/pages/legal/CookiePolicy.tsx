import React, { useEffect } from 'react';
import { useLocation } from 'react-router';
import TopNavigation from '@/components/TopNavigation';
import Footer from '@/components/Footer';
import SectionHeader from '@/components/SectionHeader';
import { BRAND_NAME } from '@/constants/brand';

const CookiePolicy: React.FC = () => {
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
              badge="COOKIE POLICY"
              heading="Cookie Policy"
              description="Last updated: May 1, 2026"
            />

            <div className="space-y-8 text-body-md text-charcoal leading-relaxed">
              <section>
                <h3 className="text-heading-4 text-ink mb-3">1. What Are Cookies</h3>
                <p>
                  Cookies are small text files that are stored on your device when you visit a website. They are widely used to make websites work more efficiently and provide information to the website operators.
                </p>
              </section>

              <section>
                <h3 className="text-heading-4 text-ink mb-3">2. How We Use Cookies</h3>
                <p className="mb-3">{BRAND_NAME} uses cookies for the following purposes:</p>
                <ul className="list-disc pl-6 space-y-2">
                  <li><strong>Essential Cookies:</strong> Required for the platform to function properly, including authentication and session management.</li>
                  <li><strong>Analytics Cookies:</strong> Help us understand how users interact with our platform and improve our services.</li>
                  <li><strong>Preference Cookies:</strong> Remember your settings and preferences to enhance your experience.</li>
                  <li><strong>Security Cookies:</strong> Help protect your account and detect suspicious activity.</li>
                </ul>
              </section>

              <section>
                <h3 className="text-heading-4 text-ink mb-3">3. Types of Cookies We Use</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-body-sm">
                    <thead>
                      <tr className="border-b border-hairline">
                        <th className="text-left py-2 pr-4 text-ink font-medium">Cookie Type</th>
                        <th className="text-left py-2 pr-4 text-ink font-medium">Purpose</th>
                        <th className="text-left py-2 text-ink font-medium">Duration</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="border-b border-hairline">
                        <td className="py-2 pr-4">session_token</td>
                        <td className="py-2 pr-4">Authentication session</td>
                        <td className="py-2">Session</td>
                      </tr>
                      <tr className="border-b border-hairline">
                        <td className="py-2 pr-4">_ga</td>
                        <td className="py-2 pr-4">Google Analytics user tracking</td>
                        <td className="py-2">2 years</td>
                      </tr>
                      <tr className="border-b border-hairline">
                        <td className="py-2 pr-4">preferences</td>
                        <td className="py-2 pr-4">User preference storage</td>
                        <td className="py-2">1 year</td>
                      </tr>
                      <tr>
                        <td className="py-2 pr-4">csrf_token</td>
                        <td className="py-2 pr-4">Cross-site request forgery protection</td>
                        <td className="py-2">Session</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </section>

              <section>
                <h3 className="text-heading-4 text-ink mb-3">4. Third-Party Cookies</h3>
                <p>
                  We may use third-party services such as Google Analytics, Intercom, and Stripe that set their own cookies. These third-party cookies are governed by the respective third parties' privacy policies.
                </p>
              </section>

              <section>
                <h3 className="text-heading-4 text-ink mb-3">5. Managing Cookies</h3>
                <p className="mb-3">
                  You can control and manage cookies in your browser settings. Please note that disabling certain cookies may affect the functionality of our platform.
                </p>
                <p className="mb-3">Most browsers allow you to:</p>
                <ul className="list-disc pl-6 space-y-2">
                  <li>View cookies stored on your device</li>
                  <li>Delete individual or all cookies</li>
                  <li>Block cookies from specific websites</li>
                  <li>Block all cookies</li>
                  <li>Set preferences for when cookies are set</li>
                </ul>
              </section>

              <section>
                <h3 className="text-heading-4 text-ink mb-3">6. Updates to This Policy</h3>
                <p>
                  We may update this Cookie Policy from time to time. Changes will be posted on this page with an updated revision date. We encourage you to review this policy periodically.
                </p>
              </section>

              <section>
                <h3 className="text-heading-4 text-ink mb-3">7. Contact</h3>
                <p>
                  If you have questions about our use of cookies, please contact us at privacy@samaa.ai.
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

export default CookiePolicy;
