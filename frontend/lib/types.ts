export interface TranscriptSegment {
  speaker: number;
  text: string;
  start_time: number;
  end_time: number;
}

export interface TranscriptRecord {
  _id: string;
  original_file?: string;
  audio_path?: string;
  created_at?: string;
  transcription?: TranscriptSegment[];
  text?: string;
  summary_brief?: string;
  summary_detailed?: string;
  summary_key_points?: string;
  [key: `summary_${string}`]: string | undefined;
}

export interface TranscriptionResponse {
  message: string;
  transcript_id: string;
  transcription: string;
  transcription_segments: TranscriptSegment[];
  original_file: string;
  audio_url?: string;
  youtube_url?: string;
  youtube_video_id?: string;
}

export type SummaryType = "brief" | "detailed" | "key_points";

export interface ConversationMessage {
  role: "user" | "assistant";
  content: string;
}

