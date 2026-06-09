"use client";

import type { Conversation, ConversationAnalysis } from "@samaa/shared";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Target,
  DollarSign,
  AlertTriangle,
  Swords,
  CheckCircle,
  XCircle,
  Clock,
  Brain,
} from "lucide-react";

const OUTCOME_CONFIG: Record<string, { label: string; icon: React.ElementType; className: string }> = {
  SALE_MADE: { label: "Sale Made", icon: CheckCircle, className: "text-brand-green-deep" },
  LOST: { label: "Lost", icon: XCircle, className: "text-destructive" },
  FOLLOW_UP_NEEDED: { label: "Follow-up Needed", icon: Clock, className: "text-amber-600" },
};

interface AIInsightsPanelProps {
  conversations: Conversation[];
  analyses: Map<string, ConversationAnalysis>;
  onConversationClick?: (conversation: Conversation) => void;
  activeConversationId?: string | null;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function AIInsightsPanel({
  conversations,
  analyses,
  onConversationClick,
  activeConversationId,
}: AIInsightsPanelProps) {
  if (conversations.length === 0) {
    return (
      <div className="flex items-center justify-center py-12 text-steel text-sm">
        No AI analysis available yet
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {conversations.map((conv) => {
        const analysis = analyses.get(conv.id);
        const isActive = activeConversationId === conv.id;
        const outcomeConfig = analysis?.outcome ? OUTCOME_CONFIG[analysis.outcome] : null;
        const OutcomeIcon = outcomeConfig?.icon;

        return (
          <Card
            key={conv.id}
            className={`cursor-pointer transition-all ${
              isActive ? "ring-2 ring-brand-green" : ""
            }`}
            onClick={() => onConversationClick?.(conv)}
          >
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm">
                  Conversation · {formatTime(conv.start_time)} – {formatTime(conv.end_time)}
                </CardTitle>
                {analysis?.confidence != null && (
                  <Badge variant="outline" className="text-xs">
                    {analysis.confidence}% conf.
                  </Badge>
                )}
              </div>
            </CardHeader>
            <CardContent className="pb-3 text-sm space-y-3">
              {analysis ? (
                <>
                  {/* Intent & Outcome */}
                  <div className="flex items-center gap-4">
                    {analysis.intent && (
                      <div className="flex items-center gap-1.5">
                        <Target className="h-3.5 w-3.5 text-muted-foreground" />
                        <span className="text-xs">{analysis.intent}</span>
                      </div>
                    )}
                    {outcomeConfig && OutcomeIcon && (
                      <div className={`flex items-center gap-1.5 ${outcomeConfig.className}`}>
                        <OutcomeIcon className="h-3.5 w-3.5" />
                        <span className="text-xs font-medium">{outcomeConfig.label}</span>
                      </div>
                    )}
                  </div>

                  {/* Budget */}
                  {analysis.budget && (
                    <div className="flex items-center gap-1.5">
                      <DollarSign className="h-3.5 w-3.5 text-muted-foreground" />
                      <span className="text-xs">Budget: {analysis.budget}</span>
                    </div>
                  )}

                  {/* Products */}
                  {analysis.products && analysis.products.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {analysis.products.map((p, i) => (
                        <Badge key={i} variant="secondary" className="text-xs">
                          {p}
                        </Badge>
                      ))}
                    </div>
                  )}

                  {/* Objections */}
                  {analysis.objections && analysis.objections.length > 0 && (
                    <div className="space-y-1">
                      <div className="flex items-center gap-1.5">
                        <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
                        <span className="text-xs font-medium">Objections</span>
                      </div>
                      <ul className="ml-5 space-y-0.5">
                        {analysis.objections.map((o, i) => (
                          <li key={i} className="text-xs text-muted-foreground">
                            {o}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Competitors */}
                  {analysis.competitors && analysis.competitors.length > 0 && (
                    <div className="flex items-center gap-1.5">
                      <Swords className="h-3.5 w-3.5 text-muted-foreground" />
                      <span className="text-xs">
                        Competitors: {analysis.competitors.join(", ")}
                      </span>
                    </div>
                  )}

                  {/* Closing */}
                  <div className="flex items-center gap-1.5">
                    <CheckCircle
                      className={`h-3.5 w-3.5 ${
                        analysis.closing_attempt ? "text-brand-green-deep" : "text-steel"
                      }`}
                    />
                    <span className="text-xs">
                      {analysis.closing_attempt ? "Closing attempted" : "No closing attempt"}
                    </span>
                  </div>

                  {/* Summary */}
                  {analysis.summary && (
                    <>
                      <Separator />
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        {analysis.summary}
                      </p>
                    </>
                  )}

                  {/* Coaching Notes */}
                  {analysis.coaching_notes && (
                    <div className="flex items-start gap-1.5 rounded-lg bg-amber-50 p-2 border border-amber-100">
                      <Brain className="h-3.5 w-3.5 text-amber-600 shrink-0 mt-0.5" />
                      <p className="text-xs text-amber-800">{analysis.coaching_notes}</p>
                    </div>
                  )}

                  {/* Score Breakdown */}
                  {analysis.scores && (
                    <>
                      <Separator />
                      <div className="grid grid-cols-5 gap-1 text-center">
                        {Object.entries(analysis.scores).map(([key, val]) => (
                          <div key={key} className="space-y-0.5">
                            <div className="text-xs font-semibold">
                              {typeof val === "number" ? val.toFixed(0) : "—"}
                            </div>
                            <div className="text-[10px] text-muted-foreground capitalize">
                              {key.replace("_score", "").replace("_", " ")}
                            </div>
                          </div>
                        ))}
                      </div>
                    </>
                  )}
                </>
              ) : (
                <p className="text-xs text-muted-foreground">Analysis pending...</p>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
