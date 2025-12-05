import Link from "next/link";
import { serverFetch } from "@/lib/api";
import { TranscriptRecord } from "@/lib/types";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

function formatDate(value?: string) {
  if (!value) return "Unknown";
  const date = new Date(value);
  return isNaN(date.getTime())
    ? value
    : date.toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short"
      });
}

export default async function TranscriptsPage() {
  let transcripts: TranscriptRecord[] = [];

  try {
    transcripts = await serverFetch<TranscriptRecord[]>("/transcripts/");
  } catch (error) {
    console.error(error);
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Transcripts</h1>
        <p className="text-sm text-muted-foreground">
          Browse every stored hearing and jump into summaries or chat.
        </p>
      </div>
      {transcripts.length === 0 ? (
        <Card className="border border-dashed border-slate-800/70">
          <CardHeader>
            <CardTitle>No transcripts yet</CardTitle>
            <CardDescription>
              Upload audio or video on the home page to create your first transcript.
            </CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {transcripts.map((item) => (
            <Card key={item._id} className="border border-slate-800/80 flex flex-col">
              <CardHeader className="flex flex-col gap-1">
                <div className="flex items-center justify-between gap-2">
                  <CardTitle>{item.original_file ?? "Untitled file"}</CardTitle>
                  <Badge variant="secondary" className="shrink-0">
                    {item.transcription?.length ?? 0} segments
                  </Badge>
                </div>
                <CardDescription>{formatDate(item.created_at)}</CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col gap-3 text-sm text-muted-foreground flex-1">
                <p className="line-clamp-3">{item.text ?? "No transcript text."}</p>
                <Link
                  href={`/transcripts/${item._id}`}
                  className="text-primary text-xs uppercase tracking-wide hover:underline mt-auto inline-flex"
                >
                  Open transcript →
                </Link>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

