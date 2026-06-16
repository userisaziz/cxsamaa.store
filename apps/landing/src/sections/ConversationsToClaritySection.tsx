import React from "react";
import {
  Ear,
  EarOff,
  Target,
  Frown,
  Zap,
  TrendingUp,
  XCircle,
  CheckCircle2,
  VolumeX,
} from "lucide-react";
import SectionHeader from "@/components/SectionHeader";
import { useScrollReveal } from "@/hooks/useScrollReveal";
import { BRAND_NAME } from "@/constants/brand";

const beforeItems = [
  {
    icon: EarOff,
    label: "Conversations",
    value: "Unheard",
    description: "No visibility into what happens on the sales floor",
  },
  {
    icon: Frown,
    label: "Objections",
    value: "Missed",
    description: "Customer hesitations go undetected and unaddressed",
  },
  {
    icon: VolumeX,
    label: "Coaching",
    value: "Inconsistent",
    description: "Managers coach blind without conversation data",
  },
  {
    icon: TrendingUp,
    label: "Performance",
    value: "Unpredictable",
    description: "Sales outcomes vary wildly with no clear cause",
  },
];

const afterItems = [
  {
    icon: Ear,
    label: "Conversations",
    value: "Captured",
    description: "Every interaction recorded and analyzed in real time",
  },
  {
    icon: Target,
    label: "Objections",
    value: "Surfaced",
    description: "AI identifies objections the moment they arise",
  },
  {
    icon: Zap,
    label: "Coaching",
    value: "Consistent",
    description: "Data-driven coaching tailored to each salesperson",
  },
  {
    icon: TrendingUp,
    label: "Performance",
    value: "Repeatable",
    description: "Proven playbooks that scale across every store",
  },
];

const ComparisonCard: React.FC<{
  title: string;
  tagline: string;
  items: typeof beforeItems;
  variant: "before" | "after";
}> = ({ title, tagline, items, variant }) => {
  const isBefore = variant === "before";

  return (
    <div
      className={`relative rounded-lg overflow-hidden border ${
        isBefore
          ? "border-hairline bg-surface"
          : "border-brand-green/30 bg-gradient-to-br from-brand-green-soft/10 to-brand-green-soft/5"
      }`}
    >
      {/* Header */}
      <div
        className={`px-6 pt-6 pb-4 ${
          isBefore
            ? "border-b border-hairline"
            : "border-b border-brand-green/15"
        }`}
      >
        <span
          className={`inline-block text-micro-uppercase tracking-wider mb-2 ${
            isBefore ? "text-steel" : "text-brand-green"
          }`}
        >
          {title}
        </span>
        <h3
          className={`text-heading-4 ${isBefore ? "text-slate" : "text-ink"}`}
        >
          {tagline}
        </h3>
      </div>

      {/* Items */}
      <div className="p-6 space-y-4">
        {items.map((item) => (
          <div key={item.label} className="flex items-start gap-3 group">
            {/* Icon */}
            <div
              className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center transition-all duration-200 ${
                isBefore
                  ? "bg-surface/80 text-steel"
                  : "bg-brand-green-soft text-brand-green"
              }`}
            >
              <item.icon className="w-5 h-5" strokeWidth={1.5} />
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span
                  className={`text-body-sm-medium ${
                    isBefore ? "text-slate" : "text-ink"
                  }`}
                >
                  {item.label}:
                </span>
                <span
                  className={`text-body-sm font-semibold ${
                    isBefore
                      ? "text-steel"
                      : "text-brand-green"
                  }`}
                >
                  {item.value}
                </span>
              </div>
              <p className="text-caption text-slate mt-0.5">
                {item.description}
              </p>
            </div>

            {/* Status indicator */}
            <div className="flex-shrink-0 mt-1">
              {isBefore ? (
                <XCircle className="w-4 h-4 text-steel" strokeWidth={1.5} />
              ) : (
                <CheckCircle2
                  className="w-4 h-4 text-brand-green"
                  strokeWidth={1.5}
                />
              )}
            </div>
          </div>
        ))}
      </div>

    </div>
  );
};

const ConversationsToClaritySection: React.FC = () => {
  const gridRef = useScrollReveal<HTMLDivElement>({ stagger: 0.12, y: 30 });

  return (
    <section
      id="conversations-to-clarity"
      className="bg-canvas section-padding overflow-hidden"
    >
      <div className="container-main">
        <SectionHeader
          badge="FROM CONVERSATIONS TO CLARITY"
          heading="The Voice of Your Customer, Transformed"
          description={`How ${BRAND_NAME} captures every in-store conversation and converts it into actionable intelligence — turning what was invisible into your greatest competitive advantage.`}
        />

        {/* Main Comparison Grid */}
        <div
          ref={gridRef}
          className="grid grid-cols-1 lg:grid-cols-2 gap-6 lg:gap-10 mb-8 md:mb-12"
        >
          {/* BEFORE Column */}
          <ComparisonCard
            title={`BEFORE ${BRAND_NAME}`}
            tagline="Operating in the dark"
            items={beforeItems}
            variant="before"
          />

          {/* AFTER Column */}
          <ComparisonCard
            title={`WITH ${BRAND_NAME}`}
            tagline="Every conversation counts"
            items={afterItems}
            variant="after"
          />
        </div>

      </div>
    </section>
  );
};

export default ConversationsToClaritySection;