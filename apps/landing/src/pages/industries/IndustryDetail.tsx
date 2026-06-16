import React, { useEffect } from 'react';
import { useParams, useLocation, useNavigate } from 'react-router';
import { ArrowRight, CheckCircle2 } from 'lucide-react';
import TopNavigation from '@/components/TopNavigation';
import Footer from '@/components/Footer';
import SectionHeader from '@/components/SectionHeader';
import { getIndustryBySlug, industries } from '@/data/industries';
import { BRAND_NAME } from '@/constants/brand';

const IndustryDetail: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  const industry = slug ? getIndustryBySlug(slug) : undefined;

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);

  if (!industry) {
    return (
      <div className="font-inter">
        <TopNavigation />
        <main className="pt-16 section-padding">
          <div className="container-main text-center">
            <h1 className="text-heading-2 text-ink mb-4">Industry not found</h1>
            <p className="text-body-md text-charcoal mb-8">The industry page you're looking for doesn't exist.</p>
            <button onClick={() => navigate('/industries')} className="btn-accent">
              View All Industries
            </button>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="font-inter">
      <TopNavigation />
      <main className="pt-16">
        {/* Hero */}
        <section className="section-padding bg-gradient-to-b from-canvas to-white">
          <div className="container-main">
            <div className="grid lg:grid-cols-2 gap-10 lg:gap-14 items-center">
              {/* Text */}
              <div>
                <span className="badge-section mb-4 inline-block">{industry.name}</span>
                <h1 className="text-heading-1 text-ink leading-tight mb-5">
                  {industry.heroTitle}
                </h1>
                {industry.heroDescription.split('\n').map((p, i) => (
                  <p key={i} className="text-body-md text-charcoal mb-3 last:mb-0">
                    {p}
                  </p>
                ))}
                <button className="btn-accent mt-6 group">
                  Request Demo
                  <ArrowRight className="w-4 h-4 ml-2 inline-block group-hover:translate-x-0.5 transition-transform" strokeWidth={1.5} />
                </button>
              </div>

              {/* Hero Image */}
              <div className="rounded-xl overflow-hidden border border-hairline shadow-mockup">
                <img
                  src={industry.heroImage}
                  alt={industry.heroImageAlt}
                  className="w-full h-full object-cover"
                />
              </div>
            </div>
          </div>
        </section>

        {/* Brands */}
        {industry.brands.length > 0 && (
          <section className="py-10 md:py-12 bg-surface-soft border-y border-hairline">
            <div className="container-main">
              <p className="text-body-sm-medium text-slate text-center mb-5">
                Turning conversations into decisions for
              </p>
              <div className="flex flex-wrap justify-center gap-6 md:gap-10 items-center">
                {industry.brands.map((brand) => (
                  <span
                    key={brand}
                    className="text-heading-4 text-ink/40 font-semibold tracking-tight"
                  >
                    {brand}
                  </span>
                ))}
              </div>
            </div>
          </section>
        )}

        {/* Decision Factors */}
        <section className="section-padding">
          <div className="container-main max-w-4xl">
            <div className="text-center mb-10">
              <h2 className="text-heading-2 text-ink mb-3">Decisions are shaped through conversations</h2>
              <p className="text-body-md text-charcoal max-w-2xl mx-auto">
                Most buying decisions slow down when confidence fades before price ever becomes the issue
              </p>
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              {industry.decisionFactors.map((factor) => (
                <div key={factor.title} className="card-feature">
                  <div className="flex gap-4">
                    <div className="w-10 h-10 rounded-lg bg-brand-green/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                      <factor.icon className="w-5 h-5 text-brand-green" strokeWidth={1.5} />
                    </div>
                    <div>
                      <h4 className="text-body-md-medium text-ink mb-1">{factor.title}</h4>
                      <p className="text-body-sm text-charcoal italic">&ldquo;{factor.question}&rdquo;</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* How It Works */}
        <section className="section-padding bg-canvas-dark">
          <div className="container-main">
            <SectionHeader
              badge={`HOW ${BRAND_NAME} WORKS`}
              heading={`How ${BRAND_NAME} works for ${industry.name} Businesses`}
              description="Quietly, Naturally, Without disruption"
              variant="dark"
            />

            <div className="space-y-8 mt-8 max-w-4xl mx-auto">
              {industry.howItWorks.map((step) => (
                <div key={step.number} className="card-dark">
                  <div className="flex flex-col md:flex-row gap-6">
                    {/* Step Number */}
                    <div className="flex-shrink-0">
                      <div className="w-10 h-10 rounded-full bg-brand-green/10 flex items-center justify-center">
                        <span className="text-heading-5 text-brand-green font-bold">{step.number}</span>
                      </div>
                    </div>

                    {/* Content */}
                    <div className="flex-1">
                      <h4 className="text-heading-5 text-white mb-3">{step.title}</h4>
                      {step.descriptions.map((desc, i) => (
                        <p key={i} className="text-body-sm text-on-dark-muted mb-2 last:mb-0">
                          {desc}
                        </p>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <p className="text-caption text-on-dark-subtle text-center mt-6 max-w-xl mx-auto">
              Note: {BRAND_NAME} focuses on conversation patterns and outcomes; not individual surveillance.
            </p>
          </div>
        </section>

        {/* Benefits */}
        <section className="section-padding">
          <div className="container-main">
            <div className="grid lg:grid-cols-2 gap-10 lg:gap-14 items-center">
              {/* Image */}
              <div className="rounded-xl overflow-hidden border border-hairline shadow-mockup">
                <img
                  src={industry.benefitImage}
                  alt={industry.ctaImageAlt}
                  className="w-full object-cover"
                />
              </div>

              {/* Text */}
              <div>
                <span className="badge-section mb-4 inline-block">BENEFITS</span>
                <h2 className="text-heading-2 text-ink mb-6">
                  Benefits {industry.name} chains see with us
                </h2>
                <ul className="space-y-4 mb-8">
                  {industry.benefits.map((benefit) => (
                    <li key={benefit} className="flex items-start gap-3">
                      <CheckCircle2 className="w-5 h-5 text-brand-green flex-shrink-0 mt-0.5" strokeWidth={1.5} />
                      <span className="text-body-md text-charcoal">{benefit}</span>
                    </li>
                  ))}
                </ul>
                <p className="text-body-md-medium text-ink mb-6">
                  {BRAND_NAME} helps {industry.name.toLowerCase()} chains deliver trusted buying experiences consistently, at scale.
                </p>
                <button className="btn-accent group">
                  Request Demo
                  <ArrowRight className="w-4 h-4 ml-2 inline-block group-hover:translate-x-0.5 transition-transform" strokeWidth={1.5} />
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* Related Industries */}
        <section className="section-padding bg-surface-soft">
          <div className="container-main">
            <h3 className="text-heading-3 text-ink text-center mb-8">Explore Other Industries</h3>
            <div className="flex flex-wrap justify-center gap-3">
              {industries.filter((i) => i.slug !== industry.slug).map((ind) => (
                <button
                  key={ind.slug}
                  onClick={() => { navigate(`/industries/${ind.slug}`); window.scrollTo(0, 0); }}
                  className="card-base flex items-center gap-2 px-5 py-3 hover:border-brand-green/30 hover:shadow-brand-glow transition-all duration-200"
                >
                  <ind.icon className="w-4 h-4 text-brand-green" strokeWidth={1.5} />
                  <span className="text-body-sm-medium text-ink">{ind.name}</span>
                </button>
              ))}
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
};

export default IndustryDetail;
