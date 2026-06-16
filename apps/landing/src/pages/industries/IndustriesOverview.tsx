import React, { useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router';
import { ArrowRight } from 'lucide-react';
import TopNavigation from '@/components/TopNavigation';
import Footer from '@/components/Footer';
import SectionHeader from '@/components/SectionHeader';
import { industries } from '@/data/industries';
import { BRAND_NAME } from '@/constants/brand';

const Industries: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);

  return (
    <div className="font-inter">
      <TopNavigation />
      <main className="pt-16">
        <section className="section-padding bg-gradient-to-b from-canvas to-white">
          <div className="container-main">
            <SectionHeader
              badge="INDUSTRIES"
              heading={`Every Industry Sells Differently. ${BRAND_NAME} Reveals Why.`}
              description="Understand the conversations, objections, and buying signals that drive results in your industry."
            />

            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5 mt-8">
              {industries.map((ind) => (
                <button
                  key={ind.slug}
                  onClick={() => { navigate(`/industries/${ind.slug}`); window.scrollTo(0, 0); }}
                  className="card-feature text-left group cursor-pointer"
                >
                  <div className="w-12 h-12 rounded-lg bg-brand-green/10 flex items-center justify-center mb-4">
                    <ind.icon className="w-6 h-6 text-brand-green" strokeWidth={1.5} />
                  </div>
                  <h3 className="text-heading-5 text-ink mb-2 group-hover:text-brand-green transition-colors duration-150">
                    {ind.name}
                  </h3>
                  <p className="text-body-sm text-charcoal mb-4 line-clamp-2">
                    {ind.heroDescription.split('\n')[0]}
                  </p>
                  <span className="text-body-sm-medium text-brand-green flex items-center gap-1.5">
                    Explore Insights
                    <ArrowRight className="w-3.5 h-3.5" strokeWidth={1.5} />
                  </span>
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

export default Industries;
