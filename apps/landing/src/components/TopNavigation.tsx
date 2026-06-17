import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Menu, X, ChevronDown } from 'lucide-react';
import gsap from 'gsap';
import { useLocation, useNavigate } from 'react-router';
import { BRAND_NAME } from '@/constants/brand';

interface NavItem {
  label: string;
  path: string;
  sectionId?: string;
}

interface NavDropdown {
  label: string;
  children: NavItem[];
}

type NavEntry = NavItem | NavDropdown;

const NAV_LINKS: NavEntry[] = [
  { label: 'Features', path: '/features', sectionId: 'features' },
  {
    label: 'Roles',
    children: [
      { label: 'Store Managers', path: '/roles/store-manager' },
      { label: 'Sales Leaders', path: '/roles/sales-leadership' },
      { label: 'Brand Teams', path: '/roles/brand-team' },
      { label: 'Executive Leadership', path: '/roles/executive-leadership' },
    ],
  },
  // {
  //   label: 'Industries',
  //   children: [
  //     { label: 'Overview', path: '/industries' },
  //     { label: 'Jewellery', path: '/industries/jewellery' },
  //     { label: 'Furniture', path: '/industries/furniture' },
  //     { label: 'Auto Sales', path: '/industries/auto-sales' },
  //     { label: 'Home Improvement', path: '/industries/home-improvement' },
  //     { label: 'Apparels', path: '/industries/apparels' },
  //     { label: 'Electronics', path: '/industries/electronics' },
  //     { label: 'Hospitality', path: '/industries/hospitality' },
  //   ],
  // },
  { label: 'About Us', path: '/company/about', sectionId: 'about-us' },
];

const isDropdown = (entry: NavEntry): entry is NavDropdown => 'children' in entry;

const TopNavigation: React.FC = () => {
  const [isDark, setIsDark] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);
  const location = useLocation();
  const navigate = useNavigate();
  const isHome = location.pathname === '/';
  const dropdownTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!isHome) {
      setIsDark(false);
      return;
    }
    const darkSections = document.querySelectorAll('[data-dark-section]');
    if (darkSections.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        let anyDarkVisible = false;
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            anyDarkVisible = true;
          }
        });
        setIsDark(anyDarkVisible);
      },
      {
        rootMargin: '-64px 0px -80% 0px',
        threshold: 0,
      }
    );

    darkSections.forEach((section) => observer.observe(section));
    return () => observer.disconnect();
  }, [isHome]);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 50);
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const handleNavClick = useCallback(
    (item: NavItem) => {
      setMobileOpen(false);
      setOpenDropdown(null);
      if (isHome && item.sectionId) {
        const target = document.querySelector(`#${item.sectionId}`);
        if (target) {
          const offset = 80;
          const top = target.getBoundingClientRect().top + window.scrollY - offset;
          window.scrollTo({ top, behavior: 'smooth' });
          return;
        }
      }
      navigate(item.path);
    },
    [isHome, navigate]
  );

  useEffect(() => {
    if (mobileOpen) {
      gsap.fromTo(
        '.mobile-drawer',
        { x: '100%' },
        { x: '0%', duration: 0.3, ease: 'expo.out' }
      );
      gsap.fromTo(
        '.mobile-backdrop',
        { opacity: 0 },
        { opacity: 1, duration: 0.3 }
      );
    }
  }, [mobileOpen]);

  const closeMobile = useCallback(() => {
    gsap.to('.mobile-drawer', { x: '100%', duration: 0.3, ease: 'expo.in' });
    gsap.to('.mobile-backdrop', {
      opacity: 0,
      duration: 0.3,
      onComplete: () => setMobileOpen(false),
    });
  }, []);

  const handleDropdownEnter = (label: string) => {
    if (dropdownTimeoutRef.current) clearTimeout(dropdownTimeoutRef.current);
    setOpenDropdown(label);
  };

  const handleDropdownLeave = () => {
    dropdownTimeoutRef.current = setTimeout(() => {
      setOpenDropdown(null);
    }, 150);
  };

  const textColor = isDark && isHome ? 'text-on-dark-muted hover:text-white' : 'text-slate hover:text-ink';
  const textColorActive = isDark && isHome ? 'text-white' : 'text-ink';

  return (
    <>
      <header
        className={`fixed top-0 left-0 right-0 z-50 h-16 transition-colors duration-300 ${
          isDark && isHome
            ? 'bg-canvas-dark/95 border-b border-hairline-dark'
            : scrolled
            ? 'bg-canvas-pure/95 border-b border-hairline-soft'
            : 'bg-transparent border-b border-transparent'
        }`}
        style={{ backdropFilter: 'blur(8px)' }}
      >
        <div className="container-main h-full flex items-center justify-between">
          {/* Logo */}
          <a
            href="/"
            className="flex items-center gap-2"
            onClick={(e) => {
              e.preventDefault();
              if (isHome) {
                window.scrollTo({ top: 0, behavior: 'smooth' });
              } else {
                navigate('/');
              }
            }}
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 16 16"
              fill="none"
              className="flex-shrink-0"
            >
              <rect x="0" y="11" width="2" height="5" rx="1" fill="#00d4a4" />
              <rect x="4" y="7" width="2" height="9" rx="1" fill="#00d4a4" />
              <rect x="8" y="3" width="2" height="13" rx="1" fill="#00d4a4" />
              <rect x="12" y="0" width="2" height="16" rx="1" fill="#00d4a4" />
            </svg>
            <span
              className={`text-heading-5 font-semibold ${
                isDark && isHome ? 'text-white' : 'text-ink'
              }`}
            >
              {BRAND_NAME}
            </span>
          </a>

          {/* Desktop Nav */}
          <nav className="hidden md:flex items-center gap-1">
            {NAV_LINKS.map((entry) => {
              if (isDropdown(entry)) {
                const isOpen = openDropdown === entry.label;
                return (
                  <div
                    key={entry.label}
                    className="relative"
                    onMouseEnter={() => handleDropdownEnter(entry.label)}
                    onMouseLeave={handleDropdownLeave}
                  >
                    <button
                      className={`flex items-center gap-1 px-3 py-2 text-body-sm rounded-md transition-colors duration-150 ${
                        isOpen ? textColorActive : textColor
                      }`}
                    >
                      {entry.label}
                      <ChevronDown
                        className={`w-3.5 h-3.5 transition-transform duration-200 ${
                          isOpen ? 'rotate-180' : ''
                        }`}
                        strokeWidth={1.5}
                      />
                    </button>
                    {isOpen && (
                      <div
                        className="absolute top-full left-0 mt-1 w-48 bg-canvas-pure border border-hairline rounded-lg shadow-card py-2"
                        onMouseEnter={() => handleDropdownEnter(entry.label)}
                        onMouseLeave={handleDropdownLeave}
                      >
                        {entry.children.map((child) => (
                          <button
                            key={child.path}
                            onClick={() => handleNavClick(child)}
                            className="w-full text-left px-4 py-2 text-body-sm text-slate hover:text-ink hover:bg-surface-soft transition-colors duration-150"
                          >
                            {child.label}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                );
              }
              return (
                <button
                  key={entry.path}
                  onClick={() => handleNavClick(entry)}
                  className={`px-3 py-2 text-body-sm rounded-md transition-colors duration-150 ${
                    textColor
                  }`}
                >
                  {entry.label}
                </button>
              );
            })}
          </nav>

          {/* Desktop CTAs */}
          <div className="hidden md:flex items-center gap-3">
            <a
              href="mailto:azizadnan370@gmail.com"
              className={`text-body-sm-medium px-3 py-2 rounded-md transition-colors ${
                isDark && isHome
                  ? 'text-on-dark-muted hover:text-white hover:bg-white/5'
                  : 'text-slate hover:text-ink hover:bg-surface-soft'
              }`}
            >
              Talk to sales
            </a>
            <button className="btn-accent">Get Started</button>
          </div>

          {/* Mobile Hamburger */}
          <button
            className="md:hidden p-2"
            onClick={() => setMobileOpen(true)}
            aria-label="Open menu"
          >
            <Menu
              className={`w-6 h-6 ${isDark && isHome ? 'text-white' : 'text-ink'}`}
              strokeWidth={1.5}
            />
          </button>
        </div>
      </header>

      {/* Mobile Drawer */}
      {mobileOpen && (
        <>
          <div
            className="mobile-backdrop fixed inset-0 bg-black/30 z-50"
            onClick={closeMobile}
          />
          <div className="mobile-drawer fixed top-0 right-0 bottom-0 w-80 bg-canvas-pure z-50 p-6 shadow-xl overflow-y-auto">
            <button
              className="absolute top-4 right-4 p-2"
              onClick={closeMobile}
              aria-label="Close menu"
            >
              <X className="w-6 h-6 text-ink" strokeWidth={1.5} />
            </button>
            <nav className="mt-12 flex flex-col gap-1">
              {NAV_LINKS.map((entry) => {
                if (isDropdown(entry)) {
                  return (
                    <div key={entry.label} className="py-2">
                      <span className="text-micro-uppercase text-steel px-2 mb-2 block">
                        {entry.label}
                      </span>
                      <div className="flex flex-col gap-0.5">
                        {entry.children.map((child) => (
                          <button
                            key={child.path}
                            onClick={() => {
                              closeMobile();
                              setTimeout(() => handleNavClick(child), 350);
                            }}
                            className="text-body-md text-ink py-2.5 px-3 text-left rounded-md hover:bg-surface-soft transition-colors"
                          >
                            {child.label}
                          </button>
                        ))}
                      </div>
                    </div>
                  );
                }
                return (
                  <button
                    key={entry.path}
                    onClick={() => {
                      closeMobile();
                      setTimeout(() => handleNavClick(entry), 350);
                    }}
                    className="text-body-md text-ink py-2.5 px-3 text-left rounded-md hover:bg-surface-soft transition-colors"
                  >
                    {entry.label}
                  </button>
                );
              })}
            </nav>
            <div className="mt-6 pt-6 border-t border-hairline flex flex-col gap-3">
              <a
                href="mailto:azizadnan370@gmail.com"
                className="btn-secondary w-full text-center"
              >
                Talk to sales
              </a>
              <button
                onClick={() => {
                  closeMobile();
                }}
                className="btn-accent w-full"
              >
                Get Started
              </button>
            </div>
          </div>
        </>
      )}
    </>
  );
};

export default React.memo(TopNavigation);
