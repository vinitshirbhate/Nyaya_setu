"use client";

import { useMemo, useState } from "react";
import { Loader2, Download, MessageSquare, Sparkles, Scale, ExternalLink } from "lucide-react";
import Link from "next/link";

import { API_BASE_URL, clientFetch } from "@/lib/api";
import {
  ConversationMessage,
  SummaryType,
  TranscriptRecord,
  RelatedCase
} from "@/lib/types";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";

const summaryOptions: { label: string; value: SummaryType; helper: string }[] = [
  { label: "Brief", value: "brief", helper: "2-3 sentences" },
  {
    label: "Detailed",
    value: "detailed",
    helper: "Topics, arguments, outcomes"
  },
  { label: "Key points", value: "key_points", helper: "Bullet list" }
];

interface TranscriptDetailClientProps {
  transcript: TranscriptRecord;
}

export default function TranscriptDetailClient({
  transcript
}: TranscriptDetailClientProps) {
  const [summaryType, setSummaryType] = useState<SummaryType>("detailed");
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [summary, setSummary] = useState<string>(
    transcript[`summary_${summaryType}`] ?? ""
  );
  const [relatedCases, setRelatedCases] = useState<RelatedCase[]>(
    transcript.related_cases ?? []
  );
  const [queriesUsed, setQueriesUsed] = useState<string[]>(
    transcript.legal_queries_used ?? []
  );

  const [question, setQuestion] = useState("");
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [chatHistory, setChatHistory] = useState<ConversationMessage[]>([]);
  const [chatAnswer, setChatAnswer] = useState("");
  const [chatError, setChatError] = useState("");

  const segments = transcript.transcription ?? [];

  const createdAt = useMemo(() => {
    if (!transcript.created_at) return "";
    const date = new Date(transcript.created_at);
    if (isNaN(date.getTime())) return transcript.created_at;
    return date.toLocaleString();
  }, [transcript.created_at]);

  async function handleSummarize() {
    setIsSummarizing(true);
    setChatError("");
    try {
      const res = await clientFetch<{
        summary: string;
        related_cases?: RelatedCase[];
        legal_queries_used?: string[];
      }>("/summarize/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          transcript_id: transcript._id,
          summary_type: summaryType
        })
      });
      setSummary(res.summary);
      setRelatedCases(res.related_cases ?? []);
      setQueriesUsed(res.legal_queries_used ?? []);
    } catch (err) {
      setSummary("");
      setChatError(err instanceof Error ? err.message : "Summary failed");
    } finally {
      setIsSummarizing(false);
    }
  }

  async function handleAsk() {
    if (!question.trim()) return;
    setIsChatLoading(true);
    setChatError("");

    try {
      const response = await clientFetch<{ answer: string }>("/chat/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          transcript_id: transcript._id,
          question,
          conversation_history: chatHistory
        })
      });

      const userMsg: ConversationMessage = { role: "user", content: question };
      const assistantMsg: ConversationMessage = {
        role: "assistant",
        content: response.answer
      };
      setChatHistory((prev) => [...prev, userMsg, assistantMsg]);
      setChatAnswer(response.answer);
      setQuestion("");
    } catch (err) {
      setChatError(err instanceof Error ? err.message : "Chat failed");
    } finally {
      setIsChatLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-4 justify-between">
        <div>
          <p className="text-xs uppercase tracking-wide text-muted-foreground">
            Transcript
          </p>
          <h1 className="text-2xl font-semibold">
            {transcript.original_file ?? "Unknown file"}
          </h1>
          <p className="text-sm text-muted-foreground">Created {createdAt}</p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Button asChild variant="outline">
            <a
              href={`${API_BASE_URL}/generate-pdf/${transcript._id}`}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2"
            >
              <Download className="h-4 w-4" />
              PDF Report
            </a>
          </Button>
          <Button asChild variant="secondary">
            <a
              href={transcript.audio_path ?? "#"}
              target="_blank"
              rel="noreferrer"
            >
              Cloudinary audio
            </a>
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[2fr,1fr]">
        <Card className="border border-slate-800/80">
          <CardHeader>
            <CardTitle>Transcript body</CardTitle>
            <CardDescription>
              Speaker labelled segments merged from AssemblyAI output.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 max-h-[480px] overflow-y-auto pr-2">
              {segments.map((segment, idx) => (
                <div
                  key={`${segment.speaker}-${segment.start_time}-${idx}`}
                  className="rounded-lg border border-slate-800/80 bg-slate-950/40 p-3"
                >
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span className="flex items-center gap-2">
                      <Badge variant="muted">Speaker {segment.speaker}</Badge>
                      <span>
                        {segment.start_time.toFixed(2)}s →{" "}
                        {segment.end_time.toFixed(2)}s
                      </span>
                    </span>
                    <span>#{idx + 1}</span>
                  </div>
                  <p className="text-sm mt-2">{segment.text}</p>
                </div>
              ))}
              {segments.length === 0 && (
                <p className="text-sm text-muted-foreground">
                  No segments were stored for this transcript.
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card className="border border-primary/30">
            <CardHeader>
              <div className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-primary" />
                <div>
                  <CardTitle>Gemini summaries</CardTitle>
                  <CardDescription>
                    Choose a style, then call the `/summarize/` endpoint.
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex gap-2 text-xs">
                {summaryOptions.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => {
                      setSummaryType(option.value);
                      setSummary(transcript[`summary_${option.value}`] ?? "");
                    }}
                    className={`flex-1 rounded-md border px-3 py-2 text-left transition-colors ${
                      summaryType === option.value
                        ? "border-primary bg-primary/10 text-primary"
                        : "border-border bg-slate-900/60 text-muted-foreground hover:border-primary/40"
                    }`}
                  >
                    <span className="block font-semibold text-xs uppercase">
                      {option.label}
                    </span>
                    <span className="text-[11px] text-muted-foreground">
                      {option.helper}
                    </span>
                  </button>
                ))}
              </div>
              <Button
                onClick={handleSummarize}
                disabled={isSummarizing}
                className="w-full"
              >
                {isSummarizing ? (
                  <span className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Generating…
                  </span>
                ) : (
                  "Generate summary"
                )}
              </Button>
              <Textarea
                readOnly
                value={summary}
                placeholder="Your Gemini summary will appear here."
                className="min-h-[180px]"
              />
            </CardContent>
          </Card>

          <Card className="border border-secondary/40">
            <CardHeader>
              <div className="flex items-center gap-2">
                <MessageSquare className="h-5 w-5 text-secondary" />
                <div>
                  <CardTitle>Ask the transcript</CardTitle>
                  <CardDescription>
                    `/chat/` endpoint with optional conversation history.
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <Textarea
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="E.g. What did the judge decide about the adjournment?"
              />
              {chatError && (
                <p className="text-xs text-red-400 bg-red-400/10 px-3 py-2 rounded-md border border-red-500/30">
                  {chatError}
                </p>
              )}
              <Button
                onClick={handleAsk}
                disabled={isChatLoading}
                className="w-full"
              >
                {isChatLoading ? (
                  <span className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Asking Gemini…
                  </span>
                ) : (
                  "Ask question"
                )}
              </Button>
              {chatAnswer && (
                <div className="rounded-lg border border-slate-800/80 bg-slate-950/40 p-3 text-sm space-y-2">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">
                    Latest answer
                  </p>
                  <p>{chatAnswer}</p>
                </div>
              )}
              {chatHistory.length > 0 && (
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted-foreground mb-2">
                    Conversation
                  </p>
                  <div className="space-y-2 max-h-[200px] overflow-y-auto pr-1">
                    {chatHistory.map((entry, idx) => (
                      <div
                        key={`${entry.role}-${idx}`}
                        className="text-xs rounded-md border border-border px-3 py-2 bg-slate-900/50"
                      >
                        <span className="font-semibold text-primary">
                          {entry.role === "user" ? "You" : "Gemini"}:
                        </span>{" "}
                        {entry.content}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Related Case Law Section */}
      {(relatedCases.length > 0 || queriesUsed.length > 0) && (
        <Card className="border border-accent/40">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Scale className="h-5 w-5 text-accent" />
              <div>
                <CardTitle>Related Case Law</CardTitle>
                <CardDescription>
                  Past judgments and precedents related to this transcript
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {queriesUsed.length > 0 && (
              <div>
                <p className="text-xs uppercase tracking-wide text-muted-foreground mb-2">
                  Legal Search Queries Used
                </p>
                <div className="flex flex-wrap gap-2">
                  {queriesUsed.map((query, idx) => (
                    <Badge key={idx} variant="secondary" className="text-xs">
                      {query}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {relatedCases.length > 0 ? (
              <div className="space-y-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">
                  Top {relatedCases.length} Related Cases
                </p>
                <div className="grid gap-3">
                  {relatedCases.map((caseItem, idx) => (
                    <div
                      key={idx}
                      className="rounded-lg border border-slate-800/80 bg-slate-950/40 p-4 space-y-2"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          <h4 className="text-sm font-semibold mb-1 line-clamp-2">
                            {caseItem.title}
                          </h4>
                          {caseItem.snippet && (
                            <p className="text-xs text-muted-foreground line-clamp-2 mb-2">
                              {caseItem.snippet}
                            </p>
                          )}
                          {caseItem.url && (
                            <a
                              href={caseItem.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                            >
                              View on Indian Kanoon
                              <ExternalLink className="h-3 w-3" />
                            </a>
                          )}
                        </div>
                        {caseItem.similarity_score !== undefined && (
                          <Badge
                            variant="outline"
                            className="text-xs whitespace-nowrap"
                          >
                            {(caseItem.similarity_score * 100).toFixed(1)}% match
                          </Badge>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                No related cases found. Generate a summary to search for related case law.
              </p>
            )}
          </CardContent>
        </Card>
      )}

      <Card className="border border-slate-800/80">
        <CardHeader>
          <CardTitle>Raw text</CardTitle>
          <CardDescription>Combined transcript, useful for copy/paste.</CardDescription>
        </CardHeader>
        <CardContent>
          <Textarea readOnly value={transcript.text ?? ""} className="min-h-[220px]" />
        </CardContent>
      </Card>

      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <Link href="/transcripts" className="text-primary hover:underline">
          ← Back to transcripts
        </Link>
        <span>
          Palette: <span className="text-[#C1785A]">C1785A</span>,{" "}
          <span className="text-[#305669]">305669</span>,{" "}
          <span className="text-[#8ABEB9]">8ABEB9</span>
        </span>
      </div>
    </div>
  );
}

