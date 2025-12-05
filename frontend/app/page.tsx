"use client";

import { useState } from "react";
import Link from "next/link";
import { Upload, FileText, Waves, Loader2, Youtube } from "lucide-react";

import { API_BASE_URL, clientFetch } from "@/lib/api";
import { TranscriptionResponse } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

type UploadMode = "file" | "youtube";

export default function UploadPage() {
  const [uploadMode, setUploadMode] = useState<UploadMode>("file");
  const [file, setFile] = useState<File | null>(null);
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [status, setStatus] = useState<"idle" | "uploading" | "success" | "error">(
    "idle"
  );
  const [error, setError] = useState("");
  const [result, setResult] = useState<TranscriptionResponse | null>(null);

  async function handleUpload(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    
    if (uploadMode === "file") {
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
    } else {
      // YouTube URL mode
      if (!youtubeUrl.trim()) {
        setError("Please enter a YouTube URL.");
        return;
      }

      setStatus("uploading");
      setError("");
      setResult(null);

      try {
        const data = await clientFetch<TranscriptionResponse>("/transcribe-youtube/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ youtube_url: youtubeUrl.trim() })
        });
        setResult(data);
        setStatus("success");
      } catch (err) {
        setStatus("error");
        setError(err instanceof Error ? err.message : "YouTube transcription failed");
      }
    }
  }

  return (
    <div className="space-y-6">
      <section className="grid gap-6 lg:grid-cols-[2fr,1fr]">
        <Card className="border border-slate-800/80">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="h-11 w-11 rounded-xl bg-primary/20 flex items-center justify-center text-primary">
                {uploadMode === "file" ? (
                  <Upload className="h-5 w-5" />
                ) : (
                  <Youtube className="h-5 w-5" />
                )}
              </div>
              <div>
                <CardTitle className="text-lg">
                  {uploadMode === "file" ? "Upload hearing media" : "YouTube video transcript"}
                </CardTitle>
                <p className="text-xs text-muted-foreground">
                  {uploadMode === "file"
                    ? "Send audio or video to AssemblyAI, save results in MongoDB and enable Gemini-powered insights."
                    : "Enter a YouTube URL to fetch and transcribe the video's captions."}
                </p>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleUpload} className="space-y-4">
              {/* Mode toggle */}
              <div className="flex gap-2 p-1 bg-slate-900/50 rounded-lg border border-slate-800/80">
                <button
                  type="button"
                  onClick={() => {
                    setUploadMode("file");
                    setError("");
                    setFile(null);
                    setYoutubeUrl("");
                  }}
                  className={`flex-1 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    uploadMode === "file"
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <span className="flex items-center justify-center gap-2">
                    <Upload className="h-4 w-4" />
                    File Upload
                  </span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setUploadMode("youtube");
                    setError("");
                    setFile(null);
                    setYoutubeUrl("");
                  }}
                  className={`flex-1 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    uploadMode === "youtube"
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <span className="flex items-center justify-center gap-2">
                    <Youtube className="h-4 w-4" />
                    YouTube URL
                  </span>
                </button>
              </div>

              {uploadMode === "file" ? (
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
              ) : (
                <div className="space-y-2">
                  <label className="text-xs uppercase tracking-wide text-muted-foreground">
                    YouTube URL
                  </label>
                  <Input
                    type="url"
                    placeholder="https://www.youtube.com/watch?v=..."
                    value={youtubeUrl}
                    onChange={(e) => setYoutubeUrl(e.target.value)}
                  />
                  <p className="text-xs text-muted-foreground">
                    Supports full URLs (youtube.com/watch?v=...) or short URLs (youtu.be/...)
                  </p>
                </div>
              )}
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
                      {uploadMode === "file" ? "Uploading…" : "Processing…"}
                    </span>
                  ) : (
                    uploadMode === "file" ? "Upload Court Hearing" : "Transcribe YouTube Video"
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
                {uploadMode === "file"
                  ? "Files are temporarily stored in `uploads/`, pushed to Cloudinary, and deleted after processing."
                  : "YouTube transcripts are fetched directly from the video's captions and stored in MongoDB."}
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

