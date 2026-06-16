import { Store, Building2, Palette, Crown } from 'lucide-react';

export interface RoleGain {
  title: string;
  description: string;
}

export interface RolePage {
  slug: string;
  role: string;
  tagline: string;
  overview: string;
  outcome: string;
  gains: RoleGain[];
  makesVisible: string[];
  dashboardFeatures: string[];
  icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
}

export const roles: RolePage[] = [
  {
    slug: 'store-manager',
    role: 'Store Managers',
    tagline: 'Run better stores, every day.',
    overview:
      'SAMAA helps store managers understand what\'s happening on the floor, identify coaching opportunities, and improve team performance through real customer interactions.',
    outcome: 'Better execution, stronger teams, higher conversions.',
    gains: [
      {
        title: 'Better Visibility',
        description: 'See how customer conversations impact sales outcomes.',
      },
      {
        title: 'Faster Coaching',
        description: 'Identify coaching moments without constant observation.',
      },
      {
        title: 'Team Consistency',
        description: 'Ensure associates follow best practices every day.',
      },
      {
        title: 'Early Issue Detection',
        description: 'Spot service gaps before they affect results.',
      },
    ],
    makesVisible: [
      'Missed sales opportunities',
      'Customer objections',
      'SOP compliance gaps',
      'High-performing sales behaviors',
      'Individual associate performance',
    ],
    dashboardFeatures: [
      'Daily coaching dashboard',
      'Associate scorecards',
      'SOP compliance alerts',
    ],
    icon: Store,
  },
  {
    slug: 'sales-leadership',
    role: 'Sales Leaders',
    tagline: 'Scale winning sales behaviors.',
    overview:
      'SAMAA helps sales leaders understand why teams succeed, replicate winning behaviors, and improve performance across stores and regions.',
    outcome: 'Consistent sales growth across teams and locations.',
    gains: [
      {
        title: 'Operational Clarity',
        description: 'Understand what drives wins and losses.',
      },
      {
        title: 'Scalable Success',
        description: 'Turn top-performer behaviors into standards.',
      },
      {
        title: 'Measurable Improvement',
        description: 'Track progress through real conversations.',
      },
      {
        title: 'Better Coaching',
        description: 'Focus support where it creates impact.',
      },
    ],
    makesVisible: [
      'Conversion drivers',
      'Objection trends',
      'Sales behavior patterns',
      'Coaching opportunities',
      'Regional performance differences',
    ],
    dashboardFeatures: [
      'Multi-store comparison',
      'Regional benchmarking',
      'Conversion intelligence',
    ],
    icon: Building2,
  },
  {
    slug: 'brand-team',
    role: 'Brand Teams',
    tagline: 'Protect and strengthen brand experience.',
    overview:
      'SAMAA helps brand teams understand how customers experience the brand in real interactions.',
    outcome: 'Stronger brand alignment across every store.',
    gains: [
      {
        title: 'Brand Consistency',
        description: 'Ensure messaging is delivered correctly.',
      },
      {
        title: 'Customer Understanding',
        description: 'Hear what customers actually care about.',
      },
      {
        title: 'Faster Feedback Loops',
        description: 'Learn what\'s working and what isn\'t.',
      },
      {
        title: 'Better Decisions',
        description: 'Use customer conversations to guide strategy.',
      },
    ],
    makesVisible: [
      'Brand message adoption',
      'Customer sentiment',
      'Product feedback',
      'Experience gaps',
      'Messaging effectiveness',
    ],
    dashboardFeatures: [
      'Brand consistency score',
      'Sentiment tracking',
      'Experience monitoring',
    ],
    icon: Palette,
  },
  {
    slug: 'executive-leadership',
    role: 'Executive Leadership',
    tagline: 'Make decisions with confidence.',
    overview:
      'SAMAA connects customer conversations to business performance, giving leaders a clearer view of what drives growth.',
    outcome: 'Faster, smarter business decisions.',
    gains: [
      {
        title: 'Enterprise Visibility',
        description: 'See performance across all locations.',
      },
      {
        title: 'Revenue Intelligence',
        description: 'Understand drivers behind business outcomes.',
      },
      {
        title: 'Strategic Confidence',
        description: 'Make decisions backed by real customer data.',
      },
      {
        title: 'Competitive Advantage',
        description: 'Identify opportunities before competitors.',
      },
    ],
    makesVisible: [
      'Enterprise-wide trends',
      'Revenue drivers',
      'Customer demand shifts',
      'Operational strengths and weaknesses',
      'Market opportunities',
    ],
    dashboardFeatures: [
      'Executive KPI dashboard',
      'Revenue attribution insights',
      'Strategic reporting',
    ],
    icon: Crown,
  },
];

export function getRoleBySlug(slug: string): RolePage | undefined {
  return roles.find((role) => role.slug === slug);
}
