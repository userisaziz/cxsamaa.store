import React, { useEffect, useRef } from 'react';
import gsap from 'gsap';
import { ChevronDown } from 'lucide-react';
import ParticleNetwork from '@/components/ParticleNetwork';
import { useReducedMotion } from '@/hooks/useReducedMotion';

const HeroSection: React.FC = () => {
  const sectionRef = useRef<HTMLElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const scrollIndicatorRef = useRef<HTMLDivElement>(null);
  const reducedMotion = useReducedMotion();

  useEffect(() => {
    if (reducedMotion || !contentRef.current) return;

    const ctx = gsap.context(() => {
      const tl = gsap.timeline({ delay: 0.2 });

      tl.fromTo(
        '.hero-badge',
        { opacity: 0, y: 20 },
        { opacity: 1, y: 0, duration: 0.5, ease: 'expo.out' }
      )
        .fromTo(
          '.hero-headline-word',
          { opacity: 0, y: 30 },
          {
            opacity: 1,
            y: 0,
            duration: 0.6,
            stagger: 0.06,
            ease: 'expo.out',
          },
          '-=0.3'
        )
        .fromTo(
          '.hero-subtitle',
          { opacity: 0, y: 20 },
          { opacity: 1, y: 0, duration: 0.5, ease: 'expo.out' },
          '-=0.2'
        )
        .fromTo(
          '.hero-cta',
          { opacity: 0 },
          { opacity: 1, duration: 0.4, ease: 'power2.out' },
          '-=0.1'
        )
        .fromTo(
          scrollIndicatorRef.current,
          { opacity: 0 },
          { opacity: 1, duration: 0.4, ease: 'power2.out' },
          '-=0.1'
        );
    }, contentRef);

    return () => ctx.revert();
  }, [reducedMotion]);

  // Fade out scroll indicator on scroll
  useEffect(() => {
    const handleScroll = () => {
      if (scrollIndicatorRef.current) {
        const opacity = Math.max(0, 1 - window.scrollY / 100);
        scrollIndicatorRef.current.style.opacity = String(opacity);
      }
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const headlineWords = 'Transform Every Store Conversation Into Revenue Intelligence'.split(' ');

  return (
    <section
      ref={sectionRef}
      className="relative min-h-[100dvh] flex items-center justify-center overflow-hidden"
      style={{
        background: 'linear-gradient(180deg, #e8f4f8 0%, #f5f0e8 100%)',
      }}
    >
      <ParticleNetwork />

      <div
        ref={contentRef}
        className="container-main relative z-10 text-center pt-20"
      >
        <span className="hero-badge badge-section mb-6 inline-block opacity-0">
          RETAIL PERFORMANCE INTELLIGENCE
        </span>

        <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-hero-display font-semibold text-ink leading-tight tracking-tight mb-6">
          {headlineWords.map((word, i) => (
            <span key={i} className="hero-headline-word inline-block opacity-0 mr-[0.3em]">
              {word}
            </span>
          ))}
        </h1>

        <p className="hero-subtitle text-subtitle text-charcoal max-w-2xl mx-auto mb-8 opacity-0">
          CXSAMAA captures in-store customer conversations, processes them through
          proprietary AI, and delivers actionable insights that improve store
          performance, employee coaching, and business outcomes.
        </p>

        <div className="hero-cta flex flex-col sm:flex-row items-center justify-center gap-4 opacity-0">
          <button className="btn-accent">Get Started</button>
          <button className="btn-secondary">Talk to Sales</button>
        </div>
      </div>

      <div
        ref={scrollIndicatorRef}
        className="absolute bottom-8 left-1/2 -translate-x-1/2 z-10 opacity-0"
      >
        <ChevronDown
          className="w-5 h-5 text-slate animate-bounce-chevron"
          strokeWidth={1.5}
        />
      </div>
    </section>
  );
};

export default HeroSection;
