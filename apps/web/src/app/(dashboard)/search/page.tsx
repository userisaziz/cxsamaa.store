"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { Conversation, ConversationAnalysis, Recording, TranscriptSegment } from "@samaa/shared";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Search as SearchIcon, MessageSquare, FileAudio } from "lucide-react";
import Link from "next/link";

interface SearchResult {
  conversation: Conversation;
  analysis: ConversationAnalysis | null;
  recording: Recording | null;
  relevant_segments: TranscriptSegment[];
  similarity_score: number;
}

const OUTCOME_COLORS: Record<string, string> = {
  SALE_MADE: "border-brand-green/30 text-brand-green-deep bg-brand-green-soft",
  LOST: "border-destructive/20 text-destructive bg-destructive/10",
  FOLLOW_UP_NEEDED: "border-amber-200 text-amber-700 bg-amber-50",
};

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [outcomeFilter, setOutcomeFilter] = useState("");

  const params = new URLSearchParams();
  if (searchTerm) params.set("q", searchTerm);
  if (outcomeFilter) params.set("outcome", outcomeFilter);

  const { data, isLoading } = useQuery({
    queryKey: ["search", searchTerm, outcomeFilter],
    queryFn: () =>
      api.get<{ results: SearchResult[]; total: number }>(`/search?${params.toString()}`),
    enabled: !!searchTerm,
  });

  const results = data?.results ?? [];

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setSearchTerm(query);
  }

  return (
    <div className="space-y-8 p-8">
      <div>
        <h1 className="text-[28px] font-semibold tracking-tight text-ink leading-tight">Semantic Search</h1>
        <p className="mt-1 text-sm text-steel">
          Search across all conversation transcripts using natural language
        </p>
      </div>

      {/* Search Bar */}
      <form onSubmit={handleSearch} className="flex gap-3">
        <div className="relative flex-1">
          <SearchIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search conversations... e.g. &quot;customer asking about warranty&quot;"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        <Button type="submit" disabled={!query.trim()}>
          Search
        </Button>
      </form>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <Select value={outcomeFilter} onValueChange={(v) => { setOutcomeFilter(v || ""); if (v !== undefined) setSearchTerm(query); }}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="All Outcomes" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ALL">All Outcomes</SelectItem>
            <SelectItem value="SALE_MADE">Sale Made</SelectItem>
            <SelectItem value="LOST">Lost</SelectItem>
            <SelectItem value="FOLLOW_UP_NEEDED">Follow-up Needed</SelectItem>
          </SelectContent>
        </Select>
        {data && (
          <span className="text-sm text-muted-foreground">
            {data.total} result{data.total !== 1 ? "s" : ""} found
          </span>
        )}
      </div>

      {/* Results */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="h-6 w-6 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      )}

      {!isLoading && searchTerm && results.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center text-steel">
            No results found for &quot;{searchTerm}&quot;
          </CardContent>
        </Card>
      )}

      <div className="space-y-4">
        {results.map((result, idx) => (
          <Card key={idx} className="hover:shadow-md transition-shadow">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <MessageSquare className="h-4 w-4 text-muted-foreground" />
                  <CardTitle className="text-sm">
                    Conversation · {formatTime(result.conversation.start_time)} –{" "}
                    {formatTime(result.conversation.end_time)}
                  </CardTitle>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="text-xs">
                    {(result.similarity_score * 100).toFixed(0)}% match
                  </Badge>
                  {result.analysis?.outcome && (
                    <Badge
                      variant="outline"
                      className={`text-xs ${OUTCOME_COLORS[result.analysis.outcome] || ""}`}
                    >
                      {result.analysis.outcome.replace(/_/g, " ")}
                    </Badge>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {/* Relevant Transcript Snippets */}
              {result.relevant_segments.length > 0 && (
                <div className="space-y-1 rounded-md bg-muted/50 p-3">
                  {result.relevant_segments.slice(0, 3).map((seg) => (
                    <div key={seg.id} className="flex gap-2 text-sm">
                      <span className="shrink-0 font-mono text-xs text-muted-foreground">
                        {formatTime(seg.start_time)}
                      </span>
                      <span className="shrink-0 text-xs font-semibold text-blue-600">
                        {seg.speaker_label.replace("SPEAKER_", "S")}
                      </span>
                      <span className="text-muted-foreground">{seg.text}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Analysis Summary */}
              {result.analysis?.summary && (
                <p className="text-sm text-muted-foreground">{result.analysis.summary}</p>
              )}

              {/* Products & Intent */}
              <div className="flex flex-wrap items-center gap-2">
                {result.analysis?.intent && (
                  <Badge variant="secondary" className="text-xs">
                    {result.analysis.intent}
                  </Badge>
                )}
                {result.analysis?.products?.map((p, i) => (
                  <Badge key={i} variant="outline" className="text-xs">
                    {p}
                  </Badge>
                ))}
              </div>

              {/* Link to recording */}
              {result.recording && (
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <FileAudio className="h-3 w-3" />
                  <Link
                    href={`/recordings/${result.recording.id}`}
                    className="text-primary hover:underline"
                  >
                    View Recording
                  </Link>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}
