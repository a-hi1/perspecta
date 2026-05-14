/** Shared types for the PEA frontend. */

export interface WorkflowState {
  workflow_id: string;
  user_id: string;
  status: WorkflowStatus;
  current_node: string | null;
  hot_topics: HotTopic[];
  selected_topic: HotTopic | null;
  retrieval_count: number;
  perspectives: Perspective[];
  selected_perspective: Perspective | null;
  angles: Angle[];
  selected_angle: Angle | null;
  drafts: Draft[];
  selected_draft: Draft | null;
  adapted_draft: Draft | null;
  citations: Citation[];
  verification_score: number;
  hallucination_flags: HallucinationFlag[];
  human_approved: boolean;
  human_feedback: string;
  revision_count: number;
  exported_content: string;
  evaluation: Evaluation | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export type WorkflowStatus =
  | "pending"
  | "running"
  | "waiting_approval"
  | "approved"
  | "rejected"
  | "completed"
  | "failed";

export interface HotTopic {
  title: string;
  summary: string;
  source: string;
  source_url: string;
  relevance_score: number;
  engagement_score: number;
  freshness_score: number;
  composite_score: number;
  tags: string[];
  category: string;
}

export interface Perspective {
  perspective_text: string;
  perspective_type: "judgment" | "reflection" | "lesson" | "controversy" | "summary";
  source_chunk_ids: string[];
  source_quotes: string[];
  confidence: number;
  novelty: number;
  engagement_potential: number;
  reasoning: string;
}

export interface Angle {
  style: "professional" | "story" | "controversial";
  hook: string;
  angle_description: string;
  structure: { section: string; purpose: string }[];
  tone_notes: string;
  estimated_length: "short" | "medium" | "long";
  engagement_prediction: number;
}

export interface Draft {
  id: string;
  title: string;
  content: string;
  draft_type: string;
  hook: string;
  cta: string;
  structure_notes: Record<string, any>;
  citation_markers: { position: string; chunk_id: string; source_quote: string }[];
  style_match_score: number;
}

export interface Citation {
  cited_text: string;
  source_quote: string;
  source_file: string;
  source_section: string;
  status: "pending" | "verified" | "failed";
  verification_score: number;
}

export interface HallucinationFlag {
  text: string;
  reason: string;
  severity: "high" | "medium" | "low";
}

export interface Evaluation {
  retrieval_relevance: number;
  perspective_quality: number;
  hallucination_score: number;
  overall_score: number;
  recommendations: string[];
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
