import React, { useEffect } from 'react';
import { useLocation, useParams, Link } from 'react-router';
import { CheckCircle2, ArrowLeft } from 'lucide-react';
import TopNavigation from '@/components/TopNavigation';
import Footer from '@/components/Footer';
import SectionHeader from '@/components/SectionHeader';
import { getRoleBySlug } from '@/data/roles';
import { BRAND_NAME } from '@/constants/brand';

const RoleDetail: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  const location = useLocation();
  const role = slug ? getRoleBySlug(slug) : undefined;

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);

  if (!role) {
    return (
      <div className="font-inter">
        <TopNavigation />
        <main className="pt-16">
          <section className="section-padding bg-canvas">
            <div className="container-main">
              <SectionHeader
                badge="ROLE NOT FOUND"
                heading="The page you're looking for doesn't exist"
                description="Please return to the homepage to explore available roles."
              />
              <div className="text-center mt-8">
                <Link to="/" className="btn-accent inline-flex items-center gap-2">
                  <ArrowLeft className="w-4 h-4" />
                  Return to Homepage
                </Link>
              </div>
            </div>
          </section>
        </main>
        <Footer />
      </div>
    );
  }

  const Icon = role.icon;

  return (
    <div className="font-inter">
      <TopNavigation />
      <main className="pt-16">
        {/* Hero Section */}
        <section className="section-padding bg-gradient-to-b from-canvas to-white">
          <div className="container-main">
            {/* Breadcrumb */}
            <Link
              to="/"
              className="inline-flex items-center gap-2 text-body-sm text-slate hover:text-ink transition-colors duration-150 mb-8"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Homepage
            </Link>

            {/* Icon */}
            <div className="w-16 h-16 rounded-full bg-brand-green/10 flex items-center justify-center mb-6">
              <Icon className="w-8 h-8 text-brand-green" strokeWidth={1.5} />
            </div>

            {/* Title & Tagline */}
            <h1 className="text-display-3 text-ink mb-4">{role.role}</h1>
            <p className="text-heading-4 text-brand-green mb-6">{role.tagline}</p>

            {/* Overview */}
            <p className="text-body-lg text-charcoal max-w-3xl leading-relaxed mb-8">
              {role.overview}
            </p>

            {/* Outcome */}
            <div className="bg-brand-green/5 border border-brand-green/20 rounded-lg p-6 max-w-3xl">
              <p className="text-body-md text-ink font-medium">
                <span className="text-brand-green font-semibold">Result:</span> {role.outcome}
              </p>
            </div>

            {/* Hero Image Placeholder */}
            <div className="mt-12 rounded-xl bg-surface-soft border border-hairline aspect-video flex items-center justify-center">
              <p className="text-body-md text-steel">Dashboard screenshot placeholder</p>
            </div>
          </div>
        </section>

        {/* What [Role] Gain */}
        <section className="section-padding bg-white">
          <div className="container-main">
            <SectionHeader
              badge="BENEFITS"
              heading={`What ${role.role} Gain`}
              description={`${BRAND_NAME} delivers targeted insights and capabilities designed specifically for your role.`}
            />

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-12">
              {role.gains.map((gain) => (
                <div
                  key={gain.title}
                  className="rounded-xl p-6 md:p-8 bg-canvas border border-hairline"
                >
                  <h3 className="text-heading-5 text-ink mb-3">{gain.title}</h3>
                  <p className="text-body-md text-charcoal">{gain.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* What {BRAND_NAME} Makes Visible */}
        <section className="section-padding bg-canvas">
          <div className="container-main">
            <SectionHeader
              badge="VISIBILITY"
              heading={`What ${BRAND_NAME} Makes Visible`}
              description="Turn invisible conversations into actionable intelligence."
            />

            <div className="max-w-3xl mx-auto mt-12">
              <ul className="space-y-4">
                {role.makesVisible.map((item) => (
                  <li key={item} className="flex items-start gap-3">
                    <CheckCircle2
                      className="w-6 h-6 text-brand-green flex-shrink-0 mt-0.5"
                      strokeWidth={1.5}
                    />
                    <span className="text-body-md text-charcoal">{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>

        {/* Dashboard Features */}
        <section className="section-padding bg-white">
          <div className="container-main">
            <SectionHeader
              badge="FEATURES"
              heading="Dashboard Features"
              description="Purpose-built tools that empower you to drive results every day."
            />

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-12">
              {role.dashboardFeatures.map((feature, index) => (
                <div
                  key={feature}
                  className="rounded-xl p-6 bg-canvas border border-hairline"
                >
                  <div className="w-10 h-10 rounded-full bg-brand-green/10 flex items-center justify-center mb-4">
                    <span className="text-body-sm font-semibold text-brand-green">
                      {index + 1}
                    </span>
                  </div>
                  <h4 className="text-body-md text-ink font-medium">{feature}</h4>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="section-padding bg-canvas-dark" data-dark-section>
          <div className="container-main text-center">
            <h2 className="text-display-3 text-white mb-4">
              Ready to see {BRAND_NAME} in action?
            </h2>
            <p className="text-body-lg text-on-dark-muted max-w-2xl mx-auto mb-8">
              Discover how {BRAND_NAME} can transform your team's performance through real customer
              intelligence.
            </p>
            <button className="btn-accent text-body-md px-8 py-3">
              Talk to Sales
            </button>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
};

export default RoleDetail;
