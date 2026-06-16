import React, { useEffect } from 'react';
import { useLocation } from 'react-router';
import { Mail, MapPin, Phone, Send, MessageSquare } from 'lucide-react';
import TopNavigation from '@/components/TopNavigation';
import Footer from '@/components/Footer';
import SectionHeader from '@/components/SectionHeader';
import { BRAND_NAME } from '@/constants/brand';

const contactInfo = [
  {
    icon: Mail,
    title: 'Email',
    details: ['hello@samaa.ai', 'support@samaa.ai'],
    action: 'Send Email',
  },
  {
    icon: MapPin,
    title: 'Office',
    details: ['548 Market St, Suite 101', 'San Francisco, CA 94104'],
    action: 'Get Directions',
  },
  {
    icon: Phone,
    title: 'Phone',
    details: ['+1 (415) 555-0123', 'Mon-Fri, 9AM-6PM PST'],
    action: 'Call Us',
  },
  {
    icon: MessageSquare,
    title: 'Live Chat',
    details: ['Available during business hours', 'Average response: 2 minutes'],
    action: 'Start Chat',
  },
];

const Contact: React.FC = () => {
  const location = useLocation();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);

  return (
    <div className="font-inter">
      <TopNavigation />
      <main className="pt-16">
        <section className="section-padding bg-gradient-to-b from-canvas to-white" id="contact">
          <div className="container-main">
            <SectionHeader
              badge="CONTACT"
              heading="Get in Touch"
              description={`Have a question about ${BRAND_NAME}? We'd love to hear from you. Send us a message and we'll respond as soon as possible.`}
            />

            <div className="grid md:grid-cols-5 gap-8 mt-8 max-w-5xl mx-auto">
              {/* Contact Info */}
              <div className="md:col-span-2 space-y-4">
                {contactInfo.map((info) => (
                  <div key={info.title} className="card-feature">
                    <div className="flex items-start gap-3">
                      <div className="w-10 h-10 rounded-lg bg-brand-green/10 flex items-center justify-center flex-shrink-0">
                        <info.icon className="w-5 h-5 text-brand-green" strokeWidth={1.5} />
                      </div>
                      <div>
                        <h4 className="text-body-md-medium text-ink mb-1">{info.title}</h4>
                        {info.details.map((detail) => (
                          <p key={detail} className="text-body-sm text-charcoal">{detail}</p>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Contact Form */}
              <div className="md:col-span-3 card-feature">
                <h3 className="text-heading-5 text-ink mb-6">Send Us a Message</h3>
                <form className="space-y-4" onSubmit={(e) => e.preventDefault()}>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-body-sm-medium text-ink mb-1.5">First Name</label>
                      <input
                        type="text"
                        className="w-full px-3 py-2.5 bg-canvas-pure border border-hairline rounded-md text-body-sm text-ink placeholder:text-steel focus:outline-none focus:border-brand-green/50 focus:ring-2 focus:ring-brand-green/10 transition-all"
                        placeholder="John"
                      />
                    </div>
                    <div>
                      <label className="block text-body-sm-medium text-ink mb-1.5">Last Name</label>
                      <input
                        type="text"
                        className="w-full px-3 py-2.5 bg-canvas-pure border border-hairline rounded-md text-body-sm text-ink placeholder:text-steel focus:outline-none focus:border-brand-green/50 focus:ring-2 focus:ring-brand-green/10 transition-all"
                        placeholder="Doe"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-body-sm-medium text-ink mb-1.5">Email</label>
                    <input
                      type="email"
                      className="w-full px-3 py-2.5 bg-canvas-pure border border-hairline rounded-md text-body-sm text-ink placeholder:text-steel focus:outline-none focus:border-brand-green/50 focus:ring-2 focus:ring-brand-green/10 transition-all"
                      placeholder="john@company.com"
                    />
                  </div>
                  <div>
                    <label className="block text-body-sm-medium text-ink mb-1.5">Subject</label>
                    <input
                      type="text"
                      className="w-full px-3 py-2.5 bg-canvas-pure border border-hairline rounded-md text-body-sm text-ink placeholder:text-steel focus:outline-none focus:border-brand-green/50 focus:ring-2 focus:ring-brand-green/10 transition-all"
                      placeholder="How can we help?"
                    />
                  </div>
                  <div>
                    <label className="block text-body-sm-medium text-ink mb-1.5">Message</label>
                    <textarea
                      rows={4}
                      className="w-full px-3 py-2.5 bg-canvas-pure border border-hairline rounded-md text-body-sm text-ink placeholder:text-steel focus:outline-none focus:border-brand-green/50 focus:ring-2 focus:ring-brand-green/10 transition-all resize-none"
                      placeholder="Tell us more about your needs..."
                    />
                  </div>
                  <button type="submit" className="btn-accent w-full">
                    <Send className="w-4 h-4 mr-2" strokeWidth={1.5} />
                    Send Message
                  </button>
                </form>
              </div>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
};

export default Contact;
