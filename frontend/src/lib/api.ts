/**
 * API client for the PEA backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export interface WorkflowState {
  workflow_id: string;
  user_id: string;
  status: string;
  current_node: string | null;
  hot_topics: any[];
  selected_topic: any | null;
  retrieval_count: number;
  perspectives: any[];
  selected_perspective: any | null;
  angles: any[];
  selected_angle: any | null;
  drafts: any[];
  selected_draft: any | null;
  adapted_draft: any | null;
  citations: any[];
  verification_score: number;
  hallucination_flags: any[];
  human_approved: boolean;
  human_feedback: string;
  revision_count: number;
  exported_content: string;
  evaluation: any | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface Document {
  id: string;
  title: string;
  file_type: string;
  file_size_bytes: number;
  chunk_count: number;
  status: string;
  error_message: string | null;
  created_at: string;
  processed_at: string | null;
}

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `请求错误: ${res.status}`);
  }
  return res.json();
}

// --- Workflow API ---

export async function startWorkflow(topicQuery: string = ""): Promise<WorkflowState> {
  return fetchAPI("/workflow/start", {
    method: "POST",
    body: JSON.stringify({ topic_query: topicQuery }),
  });
}

export async function getWorkflowState(workflowId: string): Promise<WorkflowState> {
  return fetchAPI(`/workflow/${workflowId}`);
}

export async function approveWorkflow(
  workflowId: string,
  editedContent?: string
): Promise<WorkflowState> {
  return fetchAPI(`/workflow/${workflowId}/approve`, {
    method: "POST",
    body: JSON.stringify({
      approved: true,
      edited_content: editedContent,
    }),
  });
}

export async function rejectWorkflow(
  workflowId: string,
  feedback: string
): Promise<WorkflowState> {
  return fetchAPI(`/workflow/${workflowId}/reject`, {
    method: "POST",
    body: JSON.stringify({ feedback }),
  });
}

// --- Documents API ---

export async function uploadDocument(file: File): Promise<Document> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/documents/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `上传错误: ${res.status}`);
  }
  return res.json();
}

export async function listDocuments(): Promise<{ documents: Document[]; total: number }> {
  return fetchAPI("/documents/");
}

export async function deleteDocument(documentId: string): Promise<void> {
  await fetchAPI(`/documents/${documentId}`, { method: "DELETE" });
}

// --- Perspectives API ---

export async function listPerspectives(type?: string): Promise<{ perspectives: any[]; total: number }> {
  const params = type ? `?perspective_type=${type}` : "";
  return fetchAPI(`/perspectives${params}`);
}

// --- Drafts API ---

export async function listDrafts(status?: string): Promise<{ drafts: any[]; total: number }> {
  const params = status ? `?status=${status}` : "";
  return fetchAPI(`/drafts${params}`);
}
