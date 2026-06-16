import React, { useEffect, useRef } from 'react';
import { CheckCircle } from 'lucide-react';
import SectionHeader from '@/components/SectionHeader';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { useReducedMotion } from '@/hooks/useReducedMotion';

gsap.registerPlugin(ScrollTrigger);

const phases = [
  {
    phase: 'PHASE 1',
    title: 'Conversation Intelligence',
    description: 'Foundational audio processing and conversation analysis.',
    features: ['Audio capture & sync', 'Speech-to-text engine', 'Objection detection', 'Dashboard analytics'],
  },
  {
    phase: 'PHASE 2',
    title: 'Store Intelligence',
    description: 'Cross-store benchmarking and performance comparison.',
    features: ['Store benchmarking', 'Performance comparison', 'Coaching recommendations', 'Trend identification'],
  },
  {
    phase: 'PHASE 3',
    title: 'Employee Intelligence',
    description: 'Personalized coaching and individual performance scoring.',
    features: ['Personalized coaching', 'Performance scoring', 'Skill gap analysis', 'Behavioral insights'],
  },
  {
    phase: 'PHASE 4',
    title: 'Retail Copilot',
    description: 'Natural language interface for executive intelligence.',
    features: ['Natural language queries', 'Executive insights', 'Conversational reporting', 'Predictive alerts'],
  },
  {
    phase: 'PHASE 5',
    title: 'Autonomous Operations',
    description: 'Self-optimizing retail intelligence platform.',
    features: ['Predictive insights', 'Automated recommendations', 'Retail optimization engine', 'Autonomous coaching'],
  },
];

const TechnicalRoadmapSection: React.FC = () => {
  const sectionRef = useRef<HTMLElement>(null);
  const lineRef = useRef<HTMLDivElement>(null);
  const reducedMotion = useReducedMotion();

  useEffect(() => {
    if (reducedMotion || !sectionRef.current || !lineRef.current) return;

    const ctx = gsap.context(() => {
      // Animate the timeline line fill
      gsap.fromTo(
        lineRef.current,
        { scaleY: 0 },
        {
          scaleY: 1,
          ease: 'none',
          scrollTrigger: {
            trigger: sectionRef.current,
            start: 'top 60%',
            end: 'bottom 60%',
            scrub: true,
          },
        }
      );

      // Animate phase cards
      const cards = sectionRef.current!.querySelectorAll('.phase-card');
      cards.forEach((card, i) => {
        const isLeft = i % 2 === 0;
        gsap.fromTo(
          card,
          { opacity: 0, x: isLeft ? -40 : 40 },
          {
            opacity: 1,
            x: 0,
            duration: 0.5,
            ease: 'expo.out',
            scrollTrigger: {
              trigger: card,
              start: 'top 80%',
              once: true,
            },
          }
        );
      });

      // Animate markers
      const markers = sectionRef.current!.querySelectorAll('.phase-marker');
      markers.forEach((marker) => {
        gsap.fromTo(
          marker,
          { scale: 0 },
          {
            scale: 1,
            duration: 0.2,
            ease: 'back.out(2)',
            scrollTrigger: {
              trigger: marker,
              start: 'top 75%',
              once: true,
            },
          }
        );
      });
    }, sectionRef);

    return () => ctx.revert();
  }, [reducedMotion]);

  return (
    <section id="roadmap" ref={sectionRef} className="bg-canvas-pure section-padding">
      <div className="container-main">
        <SectionHeader
          badge="TECHNICAL ROADMAP"
          heading="Product Evolution"
          description="A five-phase roadmap from foundational intelligence to autonomous retail operations."
        />

        <div className="relative max-w-4xl mx-auto">
          {/* Timeline Line */}
          <div className="absolute left-4 md:left-1/2 top-0 bottom-0 w-0.5 bg-hairline -translate-x-1/2">
            <div
              ref={lineRef}
              className="absolute inset-x-0 top-0 bg-brand-green origin-top"
              style={{ height: '100%' }}
            />
          </div>

          {/* Phases */}
          <div className="space-y-8 md:space-y-12">
            {phases.map((phase, index) => {
              const isLeft = index % 2 === 0;
              return (
                <div
                  key={phase.phase}
                  className={`relative flex items-start gap-6 md:gap-0 ${
                    isLeft ? 'md:flex-row' : 'md:flex-row-reverse'
                  }`}
                >
                  {/* Marker */}
                  <div className="absolute left-4 md:left-1/2 -translate-x-1/2 z-10">
                    <div className="phase-marker w-4 h-4 rounded-full bg-brand-green border-2 border-canvas-pure shadow-sm" />
                  </div>

                  {/* Spacer for alternating layout */}
                  <div className="hidden md:block md:w-1/2" />

                  {/* Card */}
                  <div className="pl-10 md:pl-0 md:w-1/2 phase-card opacity-0">
                    <div
                      className={`card-base ${
                        isLeft ? 'md:mr-8' : 'md:ml-8'
                      }`}
                    >
                      <span className="text-micro-uppercase text-brand-green block mb-2">
                        {phase.phase}
                      </span>
                      <h4 className="text-heading-4 text-ink mb-2">
                        {phase.title}
                      </h4>
                      <p className="text-body-sm text-slate mb-4">
                        {phase.description}
                      </p>
                      <ul className="space-y-1.5">
                        {phase.features.map((feature) => (
                          <li
                            key={feature}
                            className="flex items-center gap-2"
                          >
                            <CheckCircle
                              className="w-3.5 h-3.5 text-brand-green flex-shrink-0"
                              strokeWidth={2}
                            />
                            <span className="text-body-sm text-charcoal">
                              {feature}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
};

export default TechnicalRoadmapSection;
