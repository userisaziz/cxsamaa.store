import React from 'react';
import { useNavigate } from 'react-router';
import { ArrowUp } from 'lucide-react';
import { BRAND_NAME } from '@/constants/brand';

interface LinkColumn {
  title: string;
  links: { label: string; path: string }[];
}

const footerColumns: LinkColumn[] = [
  {
    title: 'Product',
    links: [
      { label: 'Features', path: '/features' },
    ],
  },
  {
    title: 'Roles',
    links: [
      { label: 'Store Managers', path: '/roles/store-manager' },
      { label: 'Sales Leaders', path: '/roles/sales-leadership' },
      { label: 'Brand Teams', path: '/roles/brand-team' },
      { label: 'Executive Leadership', path: '/roles/executive-leadership' },
    ],
  },
  // {
  //   title: 'Industries',
  //   links: [
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
  {
    title: 'Company',
    links: [
      { label: 'About Us', path: '/company/about' },
    ],
  },
  {
    title: 'Legal',
    links: [
      { label: 'Privacy Policy', path: '/legal/privacy-policy' },
      { label: 'Terms of Service', path: '/legal/terms-of-service' },
      { label: 'Cookie Policy', path: '/legal/cookie-policy' },
    ],
  },
];

const Footer: React.FC = () => {
  const navigate = useNavigate();

  const handleNavigate = (path: string) => {
    navigate(path);
    window.scrollTo(0, 0);
  };

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <footer className="bg-canvas-dark border-t border-hairline-dark relative">
      {/* Top gradient accent */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-brand-green/40 to-transparent" />

      <div className="container-main py-12 md:py-16">
        {/* Brand + Back to top */}
        <div className="flex items-start justify-between mb-10">
          <div className="flex items-center gap-3">
            <button
              onClick={() => handleNavigate('/')}
              className="flex items-center gap-2.5"
            >
              <svg
                width="22"
                height="22"
                viewBox="0 0 16 16"
                fill="none"
                className="flex-shrink-0"
              >
                <rect x="0" y="11" width="2" height="5" rx="1" fill="#00d4a4" />
                <rect x="4" y="7" width="2" height="9" rx="1" fill="#00d4a4" />
                <rect x="8" y="3" width="2" height="13" rx="1" fill="#00d4a4" />
                <rect x="12" y="0" width="2" height="16" rx="1" fill="#00d4a4" />
              </svg>
              <span className="text-heading-5 font-semibold text-white tracking-tight">
                {BRAND_NAME}
              </span>
            </button>
          </div>

          <button
            onClick={scrollToTop}
            className="flex items-center gap-1.5 text-body-sm text-on-dark-muted hover:text-white transition-colors duration-150"
          >
            Back to top
            <ArrowUp className="w-3.5 h-3.5" strokeWidth={1.5} />
          </button>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-8 md:gap-12">
          {/* Link Columns */}
          {footerColumns.map((col) => (
            <div key={col.title}>
              <h4 className="text-micro-uppercase text-on-dark-subtle tracking-wider mb-4">
                {col.title}
              </h4>
              <ul className="space-y-2.5">
                {col.links.map((link) => (
                  <li key={link.label}>
                    <button
                      onClick={() => handleNavigate(link.path)}
                      className="text-body-sm text-on-dark-muted hover:text-brand-green transition-colors duration-150"
                    >
                      {link.label}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom Bar */}
        <div className="mt-12 pt-6 border-t border-hairline-dark flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-micro text-on-dark-subtle">
            &copy; 2026 {BRAND_NAME}. All rights reserved.
          </p>
          <div className="flex items-center gap-4">
            <span className="text-micro-uppercase text-on-dark-subtle border border-hairline-dark px-2 py-0.5 rounded-xs">
              Confidential
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default React.memo(Footer);
