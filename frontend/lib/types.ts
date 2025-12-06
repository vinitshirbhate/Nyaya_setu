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
  related_cases?: RelatedCase[];
  legal_queries_used?: string[];
  constitution_sections?: string[];
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

// Related Case Law Types
export interface RelatedCase {
  title: string;
  snippet: string;
  url: string;
  similarity_score?: number;
}

// Document RAG API Types
export interface DocumentRecord {
  id: string;
  filename: string;
  case_id?: string;
  uploaded_at: string;
  summary_brief?: string;
  summary_detailed?: string;
  summary_key_points?: string;
}

export interface DocumentListResponse {
  documents: DocumentRecord[];
  total: number;
}

export interface DocumentUploadResponse {
  id: string;
  filename: string;
  message: string;
}

export interface DocumentSummaryResponse {
  doc_id: string;
  summary_type: "brief" | "detailed" | "key_points";
  summary: string;
}

export interface DocumentChatResponse {
  answer: string;
  doc_id: string;
}

export interface CombinedSummaryRequest {
  doc_ids: string[];
  summary_type: DocumentSummaryType;
}

export interface CombinedSummaryResponse {
  doc_ids: string[];
  summary_type: string;
  summary: string;
}

export interface DocumentDeleteResponse {
  message: string;
  doc_id: string;
}

export type DocumentSummaryType = "brief" | "detailed" | "key_points";

