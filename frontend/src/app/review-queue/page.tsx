"use client";

import { useState, useEffect } from "react";
import { listDrafts, approveWorkflow, rejectWorkflow } from "@/lib/api";
import { formatDate, truncate } from "@/lib/utils";
import { cn } from "@/lib/utils";

export default function ReviewQueuePage() {
  const [drafts, setDrafts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDraft, setSelectedDraft] = useState<any | null>(null);
  const [feedback, setFeedback] = useState("");
  const [editedContent, setEditedContent] = useState("");
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    loadDrafts();
  }, []);

  async function loadDrafts() {
    try {
      const result = await listDrafts("review");
      setDrafts(result.drafts);
    } catch (err) {
      console.error("Failed to load drafts:", err);
    } finally {
      setLoading(false);
    }
  }

  async function handleApprove() {
    if (!selectedDraft) return;
    setActionLoading(true);
    try {
      // In real app, would call approveWorkflow with the workflow_id
      // For MVP, just update status
      setSelectedDraft(null);
      await loadDrafts();
    } catch (err) {
      console.error("Approval failed:", err);
    } finally {
      setActionLoading(false);
    }
  }

  async function handleReject() {
    if (!selectedDraft || !feedback.trim()) return;
    setActionLoading(true);
    try {
      setSelectedDraft(null);
      setFeedback("");
      await loadDrafts();
    } catch (err) {
      console.error("Rejection failed:", err);
    } finally {
      setActionLoading(false);
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Review Queue</h1>
        <p className="text-gray-500 mt-1">Review, approve, or request revisions on generated content</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Queue */}
        <div className="lg:col-span-1 space-y-3">
          <h2 className="text-sm font-medium text-gray-500 uppercase">Pending Review ({drafts.length})</h2>
          {loading ? (
            <p className="text-gray-500 text-sm">Loading...</p>
          ) : drafts.length === 0 ? (
            <div className="p-4 bg-white rounded-lg border border-gray-200 text-center text-gray-500 text-sm">
              No drafts pending review.
            </div>
          ) : (
            drafts.map((draft) => (
              <button
                key={draft.id}
                onClick={() => {
                  setSelectedDraft(draft);
                  setEditedContent(draft.content);
                }}
                className={cn(
                  "w-full text-left p-4 rounded-lg border transition-colors",
                  selectedDraft?.id === draft.id
                    ? "border-blue-500 bg-blue-50"
                    : "border-gray-200 bg-white hover:border-gray-300"
                )}
              >
                <p className="text-sm font-medium text-gray-900">{truncate(draft.title, 40)}</p>
                <p className="text-xs text-gray-500 mt-1">{draft.draft_type} | {formatDate(draft.created_at)}</p>
              </button>
            ))
          )}
        </div>

        {/* Review Panel */}
        <div className="lg:col-span-2">
          {selectedDraft ? (
            <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-6">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">{selectedDraft.title}</h2>
                <p className="text-sm text-gray-500 mt-1">{selectedDraft.draft_type} | Version {selectedDraft.version}</p>
              </div>

              {/* Content Preview */}
              <div>
                <label className="text-sm font-medium text-gray-700 mb-2 block">Content</label>
                <textarea
                  value={editedContent}
                  onChange={(e) => setEditedContent(e.target.value)}
                  rows={12}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                />
              </div>

              {/* Citations */}
              {selectedDraft.citations?.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-gray-700 mb-2">Source Citations</h3>
                  <div className="space-y-2">
                    {selectedDraft.citations.map((c: any, i: number) => (
                      <div key={i} className="p-3 bg-gray-50 rounded text-sm">
                        <p className="text-gray-800">"{c.cited_text}"</p>
                        <p className="text-xs text-gray-500 mt-1">Source: {c.source_file}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Feedback */}
              <div>
                <label className="text-sm font-medium text-gray-700 mb-2 block">Revision Feedback (if rejecting)</label>
                <textarea
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value)}
                  placeholder="Explain what needs to change..."
                  rows={3}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                />
              </div>

              {/* Actions */}
              <div className="flex gap-3">
                <button
                  onClick={handleApprove}
                  disabled={actionLoading}
                  className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium disabled:opacity-50"
                >
                  Approve & Export
                </button>
                <button
                  onClick={handleReject}
                  disabled={actionLoading || !feedback.trim()}
                  className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium disabled:opacity-50"
                >
                  Request Revision
                </button>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-lg border border-gray-200 p-12 text-center text-gray-500">
              Select a draft to review
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
