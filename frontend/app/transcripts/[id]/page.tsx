import Link from "next/link";

import { serverFetch } from "@/lib/api";
import { TranscriptRecord } from "@/lib/types";
import TranscriptDetailClient from "./transcript-detail-client";

interface TranscriptPageProps {
  params: { id: string };
}

export default async function TranscriptPage({ params }: TranscriptPageProps) {
  let transcript: TranscriptRecord | null = null;
  try {
    transcript = await serverFetch<TranscriptRecord>(
      `/transcript/${params.id}`
    );
  } catch (error) {
    console.error(error);
  }

  if (!transcript) {
    return (
      <div className="space-y-4">
        <p className="text-sm text-red-400">
          Transcript not found. Return to{" "}
          <Link href="/transcripts" className="text-primary underline">
            the list view
          </Link>
          .
        </p>
      </div>
    );
  }

  return <TranscriptDetailClient transcript={transcript} />;
}

