"use client";

import { useState } from "react";
import Link from "next/link";
import { Upload, FileText, Waves, Loader2 } from "lucide-react";

import { API_BASE_URL, clientFetch } from "@/lib/api";
import { TranscriptionResponse } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<"idle" | "uploading" | "success" | "error">(
    "idle"
  );
  const [error, setError] = useState("");
  const [result, setResult] = useState<TranscriptionResponse | null>(null);

  async function handleUpload(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!file) {
      setError("Please choose an audio or video file.");
      return;
    }

    setStatus("uploading");
    setError("");
    setResult(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const data = await clientFetch<TranscriptionResponse>("/transcribe/", {
        method: "POST",
        body: formData
      });
      setResult(data);
      setStatus("success");
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "Upload failed");
    }
  }

  return (
    <div className="space-y-6">
      <section className="grid gap-6 lg:grid-cols-[2fr,1fr]">
        <Card className="border border-slate-800/80">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="h-11 w-11 rounded-xl bg-primary/20 flex items-center justify-center text-primary">
                <Upload className="h-5 w-5" />
              </div>
              <div>
                <CardTitle className="text-lg">Upload hearing media</CardTitle>
                <p className="text-xs text-muted-foreground">
                  Send audio or video to AssemblyAI, save results in MongoDB and enable
                  Gemini-powered insights.
                </p>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleUpload} className="space-y-4">
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-wide text-muted-foreground">
                  Audio / video file
                </label>
                <Input
                  type="file"
                  accept=".mp3,.wav,.ogg,.flac,.mp4,.avi,.mov,.mkv,.webm"
                  onChange={(event) => {
                    const nextFile = event.target.files?.[0] ?? null;
                    setFile(nextFile);
                  }}
                />
              </div>
              {error && (
                <p className="text-sm text-red-400 bg-red-400/10 border border-red-500/40 px-3 py-2 rounded-md">
                  {error}
                </p>
              )}
              <div className="flex items-center gap-3">
                <Button type="submit" disabled={status === "uploading"}>
                  {status === "uploading" ? (
                    <span className="flex items-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Uploading…
                    </span>
                  ) : (
                    "Upload Court Hearing"
                  )}
                </Button>
                {result?.transcript_id && (
                  <Button variant="ghost" asChild>
                    <Link href={`/transcripts/${result.transcript_id}`}>
                      View transcript detail
                    </Link>
                  </Button>
                )}
              </div>
              <p className="text-xs text-muted-foreground">
                Files are temporarily stored in `uploads/`, pushed to Cloudinary, and
                deleted after processing.
              </p>
            </form>
          </CardContent>
        </Card>

        <div className="grid gap-4">
          <Card className="border border-slate-800/80">
            <CardHeader className="items-start gap-2">
              <div className="h-10 w-10 rounded-xl bg-secondary/20 flex items-center justify-center text-secondary">
                <FileText className="h-5 w-5" />
              </div>
              <CardTitle>AssemblyAI transcript</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Transcript of the court hearing is stored in MongoDB .
            </CardContent>
          </Card>
          <Card className="border border-slate-800/80">
            <CardHeader className="items-start gap-2">
              <div className="h-10 w-10 rounded-xl bg-accent/20 flex items-center justify-center text-accent-foreground">
                <Waves className="h-5 w-5" />
              </div>
              <CardTitle>Gemini AI</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Summaries (brief, detailed, key points) and a transcript-aware chat are
              powered by AI.
            </CardContent>
          </Card>
        </div>
      </section>

      {result && (
        <Card className="border border-primary/30">
          <CardHeader>
            <div className="flex flex-wrap items-center gap-3">
              <CardTitle className="text-lg flex-1">
                Latest transcript for {result.original_file}
              </CardTitle>
              <Badge variant="primary">Transcript #{result.transcript_id}</Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-xs uppercase text-muted-foreground mb-1">
                Combined transcript
              </p>
              <p className="text-sm leading-relaxed">{result.transcription}</p>
            </div>
            <div className="grid gap-3">
              <p className="text-xs uppercase text-muted-foreground">
                Speaker segments
              </p>
              <div className="grid gap-3 max-h-[360px] overflow-y-auto pr-1">
                {result.transcription_segments.map((segment, idx) => (
                  <div key={`${segment.speaker}-${segment.start_time}-${idx}`} className="border border-slate-800/80 rounded-lg p-3 bg-slate-900/70">
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>Speaker {segment.speaker}</span>
                      <span>
                        {segment.start_time.toFixed(2)}s → {segment.end_time.toFixed(2)}s
                      </span>
                    </div>
                    <p className="text-sm mt-1">{segment.text}</p>
                  </div>
                ))}
              </div>
            </div>
            <div className="flex flex-wrap gap-3">
              <Button asChild variant="outline">
                <a
                  href={`${API_BASE_URL}/generate-pdf/${result.transcript_id}`}
                  target="_blank"
                  rel="noreferrer"
                >
                  Download PDF report
                </a>
              </Button>
              <Button asChild variant="secondary">
                <Link href={`/transcripts/${result.transcript_id}`}>
                  Continue in dashboard
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

