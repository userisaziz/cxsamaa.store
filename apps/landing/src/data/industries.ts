import {
  Heart, Shield, UserCheck, Wallet, TrendingUp,
  Home, Palette, Star, HardHat,
  Gem, Armchair, Car, Wrench, Shirt, Tv, Coffee,
  Award, Target, DollarSign, Maximize, Calendar,
} from 'lucide-react';

import heroDefault from '@/assets/communication.png';
import benefitDefault from '@/assets/dashboard.png';

export interface DecisionFactor {
  icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
  title: string;
  question: string;
}

export interface HowItWorksStep {
  number: number;
  title: string;
  descriptions: string[];
  imageAlt: string;
}

export interface Industry {
  slug: string;
  name: string;
  heroTitle: string;
  heroDescription: string;
  heroImage: string;
  heroImageAlt: string;
  benefitImage: string;
  brands: string[];
  decisionFactors: DecisionFactor[];
  howItWorks: HowItWorksStep[];
  benefits: string[];
  ctaImageAlt: string;
  icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
}

export const industries: Industry[] = [
  {
    slug: 'jewellery',
    name: 'Jewellery',
    icon: Gem,
    heroTitle: 'Every Purchase Begins With Trust',
    heroDescription: 'Jewellery sales are shaped by emotion, confidence, and reassurance. SAMAA helps uncover the moments that build trust—or prevent a customer from buying.',
    heroImageAlt: 'Salesperson showing a necklace to a customer in a jewellery store',
    heroImage: heroDefault,
    benefitImage: benefitDefault,
    brands: ['Bluestone', 'Carbon', 'Ethera', 'Fiona', 'Jagadamba', 'CKC Jewels'],
    decisionFactors: [
      {
        icon: Heart,
        title: 'Context & Emotion',
        question: 'Is this the right moment or am I rushing a decision I\'ll regret?',
      },
      {
        icon: Shield,
        title: 'Trust & Authenticity',
        question: 'Can I trust what I\'m being told or am I only hearing what helps the sale?',
      },
      {
        icon: UserCheck,
        title: 'Personal Fit',
        question: 'Does this truly fit my needs or am I adapting myself to the product?',
      },
      {
        icon: Wallet,
        title: 'Financial Comfort',
        question: 'Will this decision make sense once the excitement fades?',
      },
      {
        icon: TrendingUp,
        title: 'Long Term Confidence',
        question: 'When I look back will I feel confident or question this choice?',
      },
    ],
    howItWorks: [
      {
        number: 1,
        title: 'Conversations happen as they always have',
        descriptions: [
          'Your consultants continue serving the way they do today — understanding occasions, explaining craftsmanship, guiding meaningful purchases.',
          'No scripts. No interruptions. No added steps for staff.',
        ],
        imageAlt: 'Sales associate assisting a customer at a jewellery counter',
      },
      {
        number: 2,
        title: 'SAMAA captures what builds confidence',
        descriptions: [
          'SAMAA identifies patterns across conversations: where buyers seek reassurance on authenticity, what creates hesitation around design or pricing, and which moments strengthen emotional certainty.',
        ],
        imageAlt: 'SAMAA device illustration',
      },
      {
        number: 3,
        title: 'Managers coach with greater precision',
        descriptions: [
          'SAMAA turns daily interactions into clear signals of buying intent, repeatable trust-building behaviors, and calmer, more confident guidance on the floor.',
          'Customers feel understood; not pressured.',
        ],
        imageAlt: 'Manager reviewing analytics dashboard',
      },
    ],
    benefits: [
      'Discover trust and certification concerns',
      'Identify price hesitation moments',
      'Understand occasion-driven buying intent',
    ],
    ctaImageAlt: 'Woman trying on jewellery in front of a mirror',
  },
  {
    slug: 'furniture',
    name: 'Furniture',
    icon: Armchair,
    heroTitle: 'Turn Browsing Into Buying',
    heroDescription: 'Furniture purchases involve careful consideration. SAMAA reveals what helps customers move forward—and what causes them to delay decisions.',
    heroImageAlt: 'Salesperson and customer in a furniture showroom',
    heroImage: heroDefault,
    benefitImage: benefitDefault,
    brands: ['Wakefit'],
    decisionFactors: [
      {
        icon: Home,
        title: 'Living Space & Fit',
        question: 'Will this fit and work in my home or will it feel cramped and out of place?',
      },
      {
        icon: Palette,
        title: 'Style & Comfort',
        question: 'Does this furniture suit my taste and will it give me more comfort than the previous one?',
      },
      {
        icon: HardHat,
        title: 'Durability',
        question: 'Does this piece fit my current lifestyle or am I caught in a moment of desire?',
      },
      {
        icon: DollarSign,
        title: 'Value & Investment',
        question: 'Will it still feel like a worthwhile purchase or will I regret it?',
      },
      {
        icon: Award,
        title: 'Long Term Value',
        question: 'When I look back will I be satisfied with the purchase?',
      },
    ],
    howItWorks: [
      {
        number: 1,
        title: 'Conversations unfold as they always have',
        descriptions: [
          'Your consultants continue guiding customers — discussing fit, materials, and comfort.',
          'No scripts. No interruptions. No added steps for staff.',
        ],
        imageAlt: 'Sales associate assisting a customer in a furniture showroom',
      },
      {
        number: 2,
        title: 'SAMAA captures what builds certainty',
        descriptions: [
          'SAMAA identifies patterns across furniture conversations: reassurance on durability or fit, hesitation around materials or pricing, and moments that strengthen comfort confidence.',
        ],
        imageAlt: 'SAMAA device illustration',
      },
      {
        number: 3,
        title: 'Managers coach with clarity',
        descriptions: [
          'SAMAA turns daily interactions into clear signals of purchase intent, repeatable trust-building behaviors, and calmer, more confident selling support.',
          'Customers feel confident; not rushed.',
        ],
        imageAlt: 'Manager reviewing analytics dashboard',
      },
    ],
    benefits: [
      'Understand style and space concerns',
      'Reveal budget versus value conversations',
      'Identify confidence-building sales behaviors',
    ],
    ctaImageAlt: 'Couple in a furniture showroom',
  },
  {
    slug: 'auto-sales',
    name: 'Auto Sales',
    icon: Car,
    heroTitle: 'See What Moves Buyers Forward',
    heroDescription: 'Major purchases involve questions, concerns, and careful evaluation. SAMAA highlights the moments that accelerate—or delay—the buying journey.',
    heroImageAlt: 'Salesperson and customer in car at a dealership',
    heroImage: heroDefault,
    benefitImage: benefitDefault,
    brands: ['Spinny', 'Ola'],
    decisionFactors: [
      {
        icon: Calendar,
        title: 'Lifestyle & Timing',
        question: 'Does this vehicle fit my daily life, or is this just a momentary impulse?',
      },
      {
        icon: Shield,
        title: 'Trust & Verification',
        question: 'Do I trust the brand, the dealer, and the guidance I\'m receiving?',
      },
      {
        icon: UserCheck,
        title: 'Suitability & Feel',
        question: 'Does this vehicle feel right for me, my driving needs, and expectations?',
      },
      {
        icon: Wallet,
        title: 'Affordability',
        question: 'Is this purchase financially comfortable, both now and over time?',
      },
      {
        icon: TrendingUp,
        title: 'Long Term Value',
        question: 'Will this vehicle hold value and meet my needs long term?',
      },
    ],
    howItWorks: [
      {
        number: 1,
        title: 'Conversations happen as they always have',
        descriptions: [
          'Your sales advisors continue guiding buyers understanding needs and explaining ownership decisions.',
          'No scripts. No interruptions. No added steps for staff.',
        ],
        imageAlt: 'Sales associate assisting a customer at a dealership',
      },
      {
        number: 2,
        title: 'SAMAA captures what drives purchase confidence',
        descriptions: [
          'SAMAA identifies patterns across showroom conversations:',
          'reassurance on reliability or safety',
          'hesitation around financing or ownership cost',
          'moments that build long-term confidence',
        ],
        imageAlt: 'SAMAA device illustration',
      },
      {
        number: 3,
        title: 'Managers coach with clarity',
        descriptions: [
          'SAMAA turns daily interactions into:',
          'clear signals of buying intent',
          'repeatable confidence building behaviors',
          'calmer, more assured guidance on the floor',
          'Customers feel supported; not pressured.',
        ],
        imageAlt: 'Manager reviewing analytics dashboard',
      },
    ],
    benefits: [
      'Understand financing concerns',
      'Identify purchase readiness signals',
      'Reveal common deal blockers',
    ],
    ctaImageAlt: 'Couple looking at a car in a showroom',
  },
  {
    slug: 'home-improvement',
    name: 'Home Improvement',
    icon: Wrench,
    heroTitle: 'Turn Questions Into Confidence',
    heroDescription: 'Customers need guidance before committing to large projects. SAMAA helps teams understand what information customers need to make decisions.',
    heroImageAlt: 'Consultant discussing renovation plans with a customer',
    heroImage: heroDefault,
    benefitImage: benefitDefault,
    brands: [],
    decisionFactors: [
      {
        icon: Shield,
        title: 'Trust & Credibility',
        question: 'Can I trust this contractor to deliver on their promises?',
      },
      {
        icon: Wallet,
        title: 'Budget Confidence',
        question: 'Will the final cost match the estimate?',
      },
      {
        icon: HardHat,
        title: 'Quality Assurance',
        question: 'Will the workmanship stand the test of time?',
      },
      {
        icon: Maximize,
        title: 'Timeline Certainty',
        question: 'Will the project be completed when promised?',
      },
      {
        icon: Star,
        title: 'Long Term Satisfaction',
        question: 'Will I love the result years from now?',
      },
    ],
    howItWorks: [
      {
        number: 1,
        title: 'Consultations happen as they always have',
        descriptions: ['Your teams conduct assessments, share recommendations, and discuss timelines — naturally.'],
        imageAlt: 'Home improvement consultation in progress',
      },
      {
        number: 2,
        title: 'SAMAA captures what drives decisions',
        descriptions: ['Identify where customers hesitate on pricing, timelines, or scope — and what messages convert consultations into signed contracts.'],
        imageAlt: 'SAMAA device illustration',
      },
      {
        number: 3,
        title: 'Operations leaders optimize with data',
        descriptions: ['Standardize winning consultation techniques, reduce sales cycles, and improve close rates across every branch.'],
        imageAlt: 'Manager reviewing analytics dashboard',
      },
    ],
    benefits: [
      'Identify project planning concerns',
      'Surface budget-related objections',
      'Understand decision-making barriers',
    ],
    ctaImageAlt: 'Renovated kitchen showcase',
  },
  {
    slug: 'apparels',
    name: 'Apparels',
    icon: Shirt,
    heroTitle: 'Understand What Makes Customers Commit',
    heroDescription: 'Buying decisions are driven by fit, confidence, and personal preference. SAMAA reveals the interactions that influence purchase decisions.',
    heroImageAlt: 'Fashion consultant helping a customer choose clothes',
    heroImage: heroDefault,
    benefitImage: benefitDefault,
    brands: [],
    decisionFactors: [
      {
        icon: UserCheck,
        title: 'Fit & Style Confidence',
        question: 'Does this truly look good on me or am I being too optimistic?',
      },
      {
        icon: Heart,
        title: 'Emotional Connection',
        question: 'Does this piece make me feel the way I want to feel?',
      },
      {
        icon: Target,
        title: 'Versatility',
        question: 'Will this work with my existing wardrobe?',
      },
      {
        icon: DollarSign,
        title: 'Value Perception',
        question: 'Is the price justified by the quality and style?',
      },
      {
        icon: Star,
        title: 'Purchase Satisfaction',
        question: 'Will I still love wearing this after the first wash?',
      },
    ],
    howItWorks: [
      {
        number: 1,
        title: 'Styling conversations happen naturally',
        descriptions: ['Your stylists help customers discover their style, try pieces, and build outfits — just as they always have.'],
        imageAlt: 'Fashion consultant with customer at clothing rack',
      },
      {
        number: 2,
        title: 'SAMAA captures what closes the sale',
        descriptions: ['Identify where customers hesitate on fit or price, and what styling advice consistently leads to purchases.'],
        imageAlt: 'SAMAA device illustration',
      },
      {
        number: 3,
        title: 'Store leaders coach with insight',
        descriptions: ['Turn every interaction into data that improves styling techniques, increases basket size, and builds customer loyalty.'],
        imageAlt: 'Manager reviewing analytics dashboard',
      },
    ],
    benefits: [
      'Identify sizing and fit concerns',
      'Understand style preferences',
      'Discover missed upsell opportunities',
    ],
    ctaImageAlt: 'Customer smiling with shopping bags',
  },
  {
    slug: 'electronics',
    name: 'Electronics',
    icon: Tv,
    heroTitle: 'Understand What Drives Purchase Confidence',
    heroDescription: 'Customers compare features, value, and alternatives before buying. SAMAA uncovers the conversations that influence their final decision.',
    heroImageAlt: 'Sales associate explaining a TV features to a customer',
    heroImage: heroDefault,
    benefitImage: benefitDefault,
    brands: [],
    decisionFactors: [
      {
        icon: HardHat,
        title: 'Technical Confidence',
        question: 'Do I understand what I\'m buying and will it meet my needs?',
      },
      {
        icon: Shield,
        title: 'Reliability',
        question: 'Will this product last or will I face issues soon?',
      },
      {
        icon: DollarSign,
        title: 'Value Comparison',
        question: 'Am I getting the best features for my budget?',
      },
      {
        icon: Star,
        title: 'Brand Trust',
        question: 'Is this brand known for quality and support?',
      },
      {
        icon: Target,
        title: 'Future Proofing',
        question: 'Will this still be good enough a year from now?',
      },
    ],
    howItWorks: [
      {
        number: 1,
        title: 'Product conversations unfold naturally',
        descriptions: ['Your team explains features, compares models, and helps customers find the perfect fit — just as they always have.'],
        imageAlt: 'Customer exploring electronics with sales associate',
      },
      {
        number: 2,
        title: 'SAMAA captures what influences decisions',
        descriptions: ['Detect where technical jargon creates confusion, what features drive purchase decisions, and which explanations build confidence.'],
        imageAlt: 'SAMAA device illustration',
      },
      {
        number: 3,
        title: 'Store managers optimize with data',
        descriptions: ['Improve product knowledge training, reduce showrooming, and increase attachment rates for accessories and warranties.'],
        imageAlt: 'Manager reviewing analytics dashboard',
      },
    ],
    benefits: [
      'Track product comparison discussions',
      'Surface feature and pricing objections',
      'Discover drivers of conversion',
    ],
    ctaImageAlt: 'Customer leaving with electronics purchase',
  },
  {
    slug: 'hospitality',
    name: 'Hospitality',
    icon: Coffee,
    heroTitle: 'Improve Hospitality experiences by making guest conversations visible',
    heroDescription: 'Hospitality decisions are built on experience, service quality, and emotional connection.\n\nSAMAA captures the front-desk and service conversations that define guest satisfaction.',
    heroImageAlt: 'Hotel front desk associate welcoming a guest',
    heroImage: heroDefault,
    benefitImage: benefitDefault,
    brands: [],
    decisionFactors: [
      {
        icon: Heart,
        title: 'Service Quality',
        question: 'Am I being truly cared for or just processed through a system?',
      },
      {
        icon: Shield,
        title: 'Trust & Safety',
        question: 'Is this establishment trustworthy and well-managed?',
      },
      {
        icon: UserCheck,
        title: 'Personalization',
        question: 'Do they understand my preferences and needs?',
      },
      {
        icon: Star,
        title: 'Experience Value',
        question: 'Is this experience worth what I\'m paying?',
      },
      {
        icon: TrendingUp,
        title: 'Loyalty & Return',
        question: 'Will I want to come back or recommend this place?',
      },
    ],
    howItWorks: [
      {
        number: 1,
        title: 'Guest interactions happen naturally',
        descriptions: ['Your team welcomes, serves, and supports guests — delivering hospitality as they always have.'],
        imageAlt: 'Hotel staff assisting a guest at the front desk',
      },
      {
        number: 2,
        title: 'SAMAA captures service excellence',
        descriptions: ['Identify what makes guests feel valued, where service gaps occur, and which interactions drive repeat visits.'],
        imageAlt: 'SAMAA device illustration',
      },
      {
        number: 3,
        title: 'Hospitality leaders optimize experiences',
        descriptions: ['Standardize service excellence across properties, improve guest satisfaction scores, and build brand loyalty.'],
        imageAlt: 'Manager reviewing analytics dashboard',
      },
    ],
    benefits: [
      'Improve guest satisfaction scores',
      'Increase repeat visit rates',
      'Standardize service excellence',
      'Drive positive online reviews',
    ],
    ctaImageAlt: 'Happy guests at a hotel lobby',
  },
];

export const industriesNavLinks = industries.map((ind) => ({
  label: ind.name,
  path: `/industries/${ind.slug}`,
}));

export function getIndustryBySlug(slug: string): Industry | undefined {
  return industries.find((ind) => ind.slug === slug);
}
