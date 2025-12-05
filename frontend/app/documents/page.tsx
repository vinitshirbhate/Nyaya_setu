"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { Upload, FileText, Loader2, CheckCircle2, XCircle, MessageSquare, Trash2 } from "lucide-react";

import { documentClientFetch } from "@/lib/api";
import {
  DocumentUploadResponse,
  DocumentRecord,
  DocumentListResponse,
  DocumentSummaryResponse,
  DocumentChatResponse,
  DocumentSummaryType,
} from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";

export default function DocumentsPage() {
  const [file, setFile] = useState<File | null>(null);
  const [caseId, setCaseId] = useState("");
  const [status, setStatus] = useState<"idle" | "uploading" | "success" | "error">("idle");
  const [error, setError] = useState("");
  const [uploadResult, setUploadResult] = useState<DocumentUploadResponse | null>(null);
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [loadingDocuments, setLoadingDocuments] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState<DocumentRecord | null>(null);
  const [summaryType, setSummaryType] = useState<DocumentSummaryType>("brief");
  const [summary, setSummary] = useState<string | null>(null);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [chatMessage, setChatMessage] = useState("");
  const [chatAnswer, setChatAnswer] = useState<string | null>(null);
  const [loadingChat, setLoadingChat] = useState(false);

  async function handleUpload(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();

    if (!file) {
      setError("Please choose a document file (PDF, DOCX, or TXT).");
      return;
    }

    setStatus("uploading");
    setError("");
    setUploadResult(null);

    const formData = new FormData();
    formData.append("file", file);
    if (caseId.trim()) {
      formData.append("case_id", caseId.trim());
    }

    try {
      const data = await documentClientFetch<DocumentUploadResponse>("/documents/", {
        method: "POST",
        body: formData,
      });
      setUploadResult(data);
      setStatus("success");
      setFile(null);
      setCaseId("");
      // Refresh document list
      loadDocuments();
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "Upload failed");
    }
  }

  const loadDocuments = useCallback(async (filterCaseId?: string) => {
    setLoadingDocuments(true);
    try {
      const url = filterCaseId?.trim()
        ? `/documents/?case_id=${encodeURIComponent(filterCaseId.trim())}`
        : "/documents/";
      const data = await documentClientFetch<DocumentListResponse>(url);
      setDocuments(data.documents);
    } catch (err) {
      console.error("Failed to load documents:", err);
    } finally {
      setLoadingDocuments(false);
    }
  }, []);

  async function loadDocument(docId: string) {
    try {
      const data = await documentClientFetch<DocumentRecord>(`/documents/${docId}`);
      setSelectedDoc(data);
      setSummary(null);
      setChatAnswer(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load document");
    }
  }

  async function generateSummary(docId: string, type: DocumentSummaryType) {
    setLoadingSummary(true);
    setSummary(null);
    try {
      const data = await documentClientFetch<DocumentSummaryResponse>(
        `/documents/${docId}/summary`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ summary_type: type }),
        }
      );
      setSummary(data.summary);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate summary");
    } finally {
      setLoadingSummary(false);
    }
  }

  async function handleChat(docId: string, message: string) {
    if (!message.trim()) return;

    setLoadingChat(true);
    setChatAnswer(null);
    try {
      const data = await documentClientFetch<DocumentChatResponse>("/documents/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          doc_id: docId,
          message: message.trim(),
        }),
      });
      setChatAnswer(data.answer);
      setChatMessage("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat failed");
    } finally {
      setLoadingChat(false);
    }
  }

  async function deleteDocument(docId: string) {
    if (!confirm("Are you sure you want to delete this document?")) return;

    try {
      await documentClientFetch(`/documents/${docId}`, {
        method: "DELETE",
      });
      // Refresh document list
      loadDocuments();
      if (selectedDoc?.id === docId) {
        setSelectedDoc(null);
        setSummary(null);
        setChatAnswer(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete document");
    }
  }

  // Load documents on mount
  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

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
                <CardTitle className="text-lg">Upload Court Document</CardTitle>
                <p className="text-xs text-muted-foreground">
                  Upload PDF, DOCX, or TXT documents for RAG-powered analysis and chat.
                </p>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleUpload} className="space-y-4">
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-wide text-muted-foreground">
                  Document file
                </label>
                <Input
                  type="file"
                  accept=".pdf,.docx,.doc,.txt"
                  onChange={(event) => {
                    const nextFile = event.target.files?.[0] ?? null;
                    setFile(nextFile);
                  }}
                />
                <p className="text-xs text-muted-foreground">
                  Supported formats: PDF, DOCX, DOC, TXT
                </p>
              </div>

              <div className="space-y-2">
                <label className="text-xs uppercase tracking-wide text-muted-foreground">
                  Case ID (optional)
                </label>
                <Input
                  type="text"
                  placeholder="CASE-123"
                  value={caseId}
                  onChange={(e) => setCaseId(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Group documents by case identifier
                </p>
              </div>

              {error && (
                <div className="flex items-center gap-2 text-sm text-red-400 bg-red-400/10 border border-red-500/40 px-3 py-2 rounded-md">
                  <XCircle className="h-4 w-4" />
                  {error}
                </div>
              )}

              {status === "success" && uploadResult && (
                <div className="flex items-center gap-2 text-sm text-green-400 bg-green-400/10 border border-green-500/40 px-3 py-2 rounded-md">
                  <CheckCircle2 className="h-4 w-4" />
                  Document uploaded successfully! ID: {uploadResult.id}
                </div>
              )}

              <Button type="submit" disabled={status === "uploading"}>
                {status === "uploading" ? (
                  <span className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Uploading and indexing...
                  </span>
                ) : (
                  "Upload Document"
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        <div className="grid gap-4">
          <Card className="border border-slate-800/80">
            <CardHeader className="items-start gap-2">
              <div className="h-10 w-10 rounded-xl bg-secondary/20 flex items-center justify-center text-secondary">
                <FileText className="h-5 w-5" />
              </div>
              <CardTitle>Document RAG</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Documents are indexed with vector embeddings for semantic search and AI-powered chat.
            </CardContent>
          </Card>
          <Card className="border border-slate-800/80">
            <CardHeader className="items-start gap-2">
              <div className="h-10 w-10 rounded-xl bg-accent/20 flex items-center justify-center text-accent-foreground">
                <MessageSquare className="h-5 w-5" />
              </div>
              <CardTitle>AI Summaries</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Generate brief, detailed, or key points summaries using AI.
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Document List */}
      <Card className="border border-slate-800/80">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-xl bg-secondary/20 flex items-center justify-center text-secondary">
                <FileText className="h-5 w-5" />
              </div>
              <div>
                <CardTitle className="text-lg">Documents</CardTitle>
                <p className="text-xs text-muted-foreground">
                  {documents.length} document{documents.length !== 1 ? "s" : ""} uploaded
                </p>
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={loadDocuments}
              disabled={loadingDocuments}
            >
              {loadingDocuments ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                "Refresh"
              )}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {documents.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              No documents uploaded yet. Upload a document to get started.
            </p>
          ) : (
            <div className="grid gap-3">
              {documents.map((doc) => (
                <div
                  key={doc.id}
                  className="border border-slate-800/80 rounded-lg p-4 bg-slate-900/70 hover:bg-slate-900/90 transition-colors cursor-pointer"
                  onClick={() => loadDocument(doc.id)}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h4 className="text-sm font-semibold truncate">{doc.filename}</h4>
                        {doc.case_id && (
                          <Badge variant="secondary" className="text-xs">
                            {doc.case_id}
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Uploaded: {new Date(doc.uploaded_at).toLocaleString()}
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteDocument(doc.id);
                      }}
                      className="text-red-400 hover:text-red-300 hover:bg-red-400/10"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Document Detail */}
      {selectedDoc && (
        <Card className="border border-primary/30">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <CardTitle className="text-lg">{selectedDoc.filename}</CardTitle>
                {selectedDoc.case_id && (
                  <Badge variant="primary">{selectedDoc.case_id}</Badge>
                )}
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setSelectedDoc(null);
                  setSummary(null);
                  setChatAnswer(null);
                }}
              >
                Close
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Summary Section */}
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <h3 className="text-sm font-semibold">Summary</h3>
                <div className="flex gap-2">
                  {(["brief", "detailed", "key_points"] as DocumentSummaryType[]).map((type) => (
                    <Button
                      key={type}
                      variant={summaryType === type ? "default" : "outline"}
                      size="sm"
                      onClick={() => {
                        setSummaryType(type);
                        generateSummary(selectedDoc.id, type);
                      }}
                      disabled={loadingSummary}
                    >
                      {type === "brief"
                        ? "Brief"
                        : type === "detailed"
                        ? "Detailed"
                        : "Key Points"}
                    </Button>
                  ))}
                </div>
              </div>
              {loadingSummary ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Generating summary...
                </div>
              ) : summary ? (
                <div className="border border-slate-800/80 rounded-lg p-4 bg-slate-900/70">
                  <p className="text-sm whitespace-pre-wrap">{summary}</p>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Click a summary type to generate
                </p>
              )}
            </div>

            {/* Chat Section */}
            <div className="space-y-3">
              <h3 className="text-sm font-semibold">Chat with Document</h3>
              <div className="space-y-2">
                <Textarea
                  placeholder="Ask a question about this document..."
                  value={chatMessage}
                  onChange={(e) => setChatMessage(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && e.ctrlKey) {
                      handleChat(selectedDoc.id, chatMessage);
                    }
                  }}
                  rows={3}
                />
                <div className="flex items-center justify-between">
                  <p className="text-xs text-muted-foreground">
                    Press Ctrl+Enter to send
                  </p>
                  <Button
                    onClick={() => handleChat(selectedDoc.id, chatMessage)}
                    disabled={loadingChat || !chatMessage.trim()}
                  >
                    {loadingChat ? (
                      <span className="flex items-center gap-2">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Processing...
                      </span>
                    ) : (
                      "Ask"
                    )}
                  </Button>
                </div>
              </div>
              {chatAnswer && (
                <div className="border border-slate-800/80 rounded-lg p-4 bg-slate-900/70">
                  <p className="text-sm whitespace-pre-wrap">{chatAnswer}</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
