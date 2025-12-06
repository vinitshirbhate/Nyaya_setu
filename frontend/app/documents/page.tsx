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
  CombinedSummaryResponse,
} from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";

export default function DocumentsPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [caseId, setCaseId] = useState("");
  const [status, setStatus] = useState<"idle" | "uploading" | "success" | "error">("idle");
  const [error, setError] = useState("");
  const [uploadResults, setUploadResults] = useState<DocumentUploadResponse[]>([]);
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [loadingDocuments, setLoadingDocuments] = useState(false);
  const [selectedDocs, setSelectedDocs] = useState<string[]>([]); // Multiple selected document IDs
  const [summaryType, setSummaryType] = useState<DocumentSummaryType>("brief");
  const [summary, setSummary] = useState<string | null>(null);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [chatMessage, setChatMessage] = useState("");
  const [chatAnswer, setChatAnswer] = useState<string | null>(null);
  const [loadingChat, setLoadingChat] = useState(false);

  async function handleUpload(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();

    if (files.length === 0) {
      setError("Please choose at least one document file (PDF, DOCX, or TXT).");
      return;
    }

    setStatus("uploading");
    setError("");
    setUploadResults([]);

    const results: DocumentUploadResponse[] = [];
    const errors: string[] = [];

    // Upload files sequentially to avoid overwhelming the server
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      try {
        const formData = new FormData();
        formData.append("file", file);
        if (caseId.trim()) {
          formData.append("case_id", caseId.trim());
        }

        const data = await documentClientFetch<DocumentUploadResponse>("/documents/", {
          method: "POST",
          body: formData,
        });
        results.push(data);
      } catch (err) {
        errors.push(`${file.name}: ${err instanceof Error ? err.message : "Upload failed"}`);
      }
    }

    if (results.length > 0) {
      setUploadResults(results);
      setStatus("success");
      if (errors.length > 0) {
        setError(`Some files failed: ${errors.join(", ")}`);
      }
      setFiles([]);
      setCaseId("");
      // Refresh document list
      loadDocuments();
    } else {
      setStatus("error");
      setError(errors.join(", ") || "All uploads failed");
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
      // Toggle selection
      if (selectedDocs.includes(docId)) {
        setSelectedDocs(selectedDocs.filter(id => id !== docId));
      } else {
        setSelectedDocs([...selectedDocs, docId]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load document");
    }
  }

  async function generateSummary(type: DocumentSummaryType) {
    if (selectedDocs.length === 0) {
      setError("Please select at least one document to generate a summary.");
      return;
    }

    setLoadingSummary(true);
    setSummary(null);
    setError("");
    try {
      // If multiple documents selected, use combined summary endpoint
      if (selectedDocs.length > 1) {
        const data = await documentClientFetch<CombinedSummaryResponse>(
          "/documents/combined-summary",
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ 
              doc_ids: selectedDocs,
              summary_type: type 
            }),
          }
        );
        setSummary(data.summary);
      } else {
        // Single document summary
        const data = await documentClientFetch<DocumentSummaryResponse>(
          `/documents/${selectedDocs[0]}/summary`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ summary_type: type }),
          }
        );
        setSummary(data.summary);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate summary");
    } finally {
      setLoadingSummary(false);
    }
  }

  async function handleChat(message: string) {
    if (!message.trim()) return;
    
    if (selectedDocs.length === 0) {
      setError("Please select at least one document to chat with.");
      return;
    }

    setLoadingChat(true);
    setChatAnswer(null);
    setError("");
    try {
      // Support both single and multiple document chat
      const data = await documentClientFetch<DocumentChatResponse>("/documents/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          doc_id: selectedDocs.length === 1 ? selectedDocs[0] : undefined,
          doc_ids: selectedDocs.length > 1 ? selectedDocs : undefined,
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
      // Remove from selection if selected
      setSelectedDocs(selectedDocs.filter(id => id !== docId));
      if (selectedDocs.length === 1 && selectedDocs[0] === docId) {
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
                  Document files (multiple selection allowed)
                </label>
                <Input
                  type="file"
                  accept=".pdf,.docx,.doc,.txt"
                  multiple
                  onChange={(event) => {
                    const selectedFiles = Array.from(event.target.files || []);
                    setFiles(selectedFiles);
                  }}
                />
                {files.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-2">
                    {files.map((file, idx) => (
                      <Badge key={idx} variant="secondary" className="text-xs">
                        {file.name}
                      </Badge>
                    ))}
                  </div>
                )}
                <p className="text-xs text-muted-foreground">
                  Supported formats: PDF, DOCX, DOC, TXT. Select multiple files to upload together.
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

              {status === "success" && uploadResults.length > 0 && (
                <div className="flex items-center gap-2 text-sm text-green-400 bg-green-400/10 border border-green-500/40 px-3 py-2 rounded-md">
                  <CheckCircle2 className="h-4 w-4" />
                  {uploadResults.length} document{uploadResults.length !== 1 ? "s" : ""} uploaded successfully!
                </div>
              )}

              <Button type="submit" disabled={status === "uploading" || files.length === 0}>
                {status === "uploading" ? (
                  <span className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Uploading {files.length} document{files.length !== 1 ? "s" : ""}...
                  </span>
                ) : (
                  `Upload ${files.length > 0 ? `${files.length} ` : ""}Document${files.length !== 1 ? "s" : ""}`
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
              onClick={() => loadDocuments()}
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
            <div className="space-y-3">
              {selectedDocs.length > 0 && (
                <div className="mb-4 p-3 bg-primary/10 border border-primary/30 rounded-lg">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground mb-2">
                    {selectedDocs.length} document{selectedDocs.length !== 1 ? "s" : ""} selected
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {selectedDocs.map((docId) => {
                      const doc = documents.find(d => d.id === docId);
                      return doc ? (
                        <Badge key={docId} variant="primary" className="text-xs">
                          {doc.filename}
                        </Badge>
                      ) : null;
                    })}
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setSelectedDocs([])}
                    className="mt-2 text-xs"
                  >
                    Clear selection
                  </Button>
                </div>
              )}
              <div className="grid gap-3">
                {documents.map((doc) => (
                  <div
                    key={doc.id}
                    className={`border rounded-lg p-4 transition-colors cursor-pointer ${
                      selectedDocs.includes(doc.id)
                        ? "border-primary bg-primary/10"
                        : "border-slate-800/80 bg-slate-900/70 hover:bg-slate-900/90"
                    }`}
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
                          {selectedDocs.includes(doc.id) && (
                            <Badge variant="primary" className="text-xs">
                              Selected
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
            </div>
          )}
        </CardContent>
      </Card>

      {/* Combined Summary & Chat Section */}
      {selectedDocs.length > 0 && (
        <Card className="border border-primary/30">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <CardTitle className="text-lg">
                  {selectedDocs.length === 1 
                    ? documents.find(d => d.id === selectedDocs[0])?.filename || "Document"
                    : `Combined Analysis (${selectedDocs.length} documents)`}
                </CardTitle>
                {selectedDocs.length > 1 && (
                  <Badge variant="primary">{selectedDocs.length} selected</Badge>
                )}
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setSelectedDocs([]);
                  setSummary(null);
                  setChatAnswer(null);
                }}
              >
                Clear Selection
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Summary Section */}
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <h3 className="text-sm font-semibold">
                  {selectedDocs.length > 1 ? "Combined Summary" : "Summary"}
                </h3>
                <div className="flex gap-2">
                  {(["brief", "detailed", "key_points"] as DocumentSummaryType[]).map((type) => (
                    <Button
                      key={type}
                      variant={summaryType === type ? "default" : "outline"}
                      size="sm"
                      onClick={() => {
                        setSummaryType(type);
                        generateSummary(type);
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
                  Generating {selectedDocs.length > 1 ? "combined " : ""}summary...
                </div>
              ) : summary ? (
                <div className="border border-slate-800/80 rounded-lg p-4 bg-slate-900/70">
                  <p className="text-sm whitespace-pre-wrap">{summary}</p>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Click a summary type to generate {selectedDocs.length > 1 ? "combined summary" : "summary"}
                </p>
              )}
            </div>

            {/* Chat Section */}
            <div className="space-y-3">
              <h3 className="text-sm font-semibold">
                Chat with {selectedDocs.length > 1 ? "Documents" : "Document"}
              </h3>
              <div className="space-y-2">
                <Textarea
                  placeholder={`Ask a question about ${selectedDocs.length > 1 ? "these documents" : "this document"}...`}
                  value={chatMessage}
                  onChange={(e) => setChatMessage(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && e.ctrlKey) {
                      handleChat(chatMessage);
                    }
                  }}
                  rows={3}
                />
                <div className="flex items-center justify-between">
                  <p className="text-xs text-muted-foreground">
                    Press Ctrl+Enter to send
                  </p>
                  <Button
                    onClick={() => handleChat(chatMessage)}
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
