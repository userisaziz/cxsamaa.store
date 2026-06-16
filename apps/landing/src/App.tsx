import { useEffect, useRef } from 'react';
import { Routes, Route, useLocation } from 'react-router';
import Lenis from 'lenis';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

import TopNavigation from '@/components/TopNavigation';
import Footer from '@/components/Footer';
import HeroSection from '@/sections/HeroSection';
import SystemArchitectureSection from '@/sections/SystemArchitectureSection';
import AudioCollectionSection from '@/sections/AudioCollectionSection';
import CoreCapabilitiesSection from '@/sections/CoreCapabilitiesSection';

import ConversationsToClaritySection from '@/sections/ConversationsToClaritySection';
import InvisibleJourneySection from '@/sections/InvisibleJourneySection';
import RolesFeaturesSection from '@/sections/RolesFeaturesSection';
import WhyNowSection from '@/sections/WhyNowSection';
import SecurityPrivacySection from '@/sections/SecurityPrivacySection';
import ScalabilitySection from '@/sections/ScalabilitySection';
import TechnicalRoadmapSection from '@/sections/TechnicalRoadmapSection';
import RisksSection from '@/sections/RisksSection';
import WhatSamaaSolvesSection from '@/sections/WhatSamaaSolvesSection';

// Pages
import Features from '@/pages/Features';
import About from '@/pages/company/About';
import PrivacyPolicy from '@/pages/legal/PrivacyPolicy';
import TermsOfService from '@/pages/legal/TermsOfService';
import CookiePolicy from '@/pages/legal/CookiePolicy';

// Industry pages
import RoleDetail from '@/pages/roles/RoleDetail';
import IntelligenceCapabilitiesSection from './sections/IntelligenceCapabilitiesSection';
import OrganizationModelSection from './sections/OrganizationModelSection';

gsap.registerPlugin(ScrollTrigger);

function HomePage() {
  const lenisRef = useRef<Lenis | null>(null);

  useEffect(() => {
    const lenis = new Lenis({
      lerp: 0.1,
      duration: 1.2,
    });
    lenisRef.current = lenis;

    lenis.on('scroll', ScrollTrigger.update);

    gsap.ticker.add((time) => {
      lenis.raf(time * 1000);
    });

    gsap.ticker.lagSmoothing(0);

    return () => {
      lenis.destroy();
      gsap.ticker.remove(lenis.raf as unknown as gsap.TickerCallback);
    };
  }, []);

  return (
    <main>
      <HeroSection />
      <InvisibleJourneySection />
      <ConversationsToClaritySection />
      <AudioCollectionSection />
      <WhatSamaaSolvesSection />
      <RolesFeaturesSection />
      {/* <ProductOverviewSection /> */}
      <SystemArchitectureSection />
      <CoreCapabilitiesSection />
      {/* <AIIntelligenceSection /> */}
      <IntelligenceCapabilitiesSection />
      <WhyNowSection />
      <OrganizationModelSection />
      {/* <RolesAccessSection /> */}
      <SecurityPrivacySection />
      <ScalabilitySection />
      <TechnicalRoadmapSection />
      <RisksSection />
    </main>
  );
}

function App() {
  // Ensure we scroll to top on route changes
  const location = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);

  return (
    <div className="font-inter">
      <Routes>
        <Route
          path="/"
          element={
            <>
              <TopNavigation />
              <HomePage />
              <Footer />
            </>
          }
        />
        <Route path="/features" element={<Features />} />
        <Route path="/roles/:slug" element={<RoleDetail />} />

        {/* <Route path="/industries" element={<IndustriesOverview />} />
        <Route path="/industries/:slug" element={<IndustryDetail />} /> */}
        <Route path="/company/about" element={<About />} />
        <Route path="/legal/privacy-policy" element={<PrivacyPolicy />} />
        <Route path="/legal/terms-of-service" element={<TermsOfService />} />
        <Route path="/legal/cookie-policy" element={<CookiePolicy />} />
      </Routes>
    </div>
  );
}

export default App;
