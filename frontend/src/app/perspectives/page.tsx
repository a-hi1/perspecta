"use client";

import { useState, useEffect } from "react";
import { listPerspectives } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Perspective {
  id: string;
  perspective_text: string;
  perspective_type: string;
  confidence: number;
  novelty: number;
  engagement_potential: number;
  source_chunks: any;
  status: string;
  user_feedback: string | null;
}

const TYPE_COLORS: Record<string, string> = {
  judgment: "bg-blue-100 text-blue-700",
  reflection: "bg-purple-100 text-purple-700",
  lesson: "bg-green-100 text-green-700",
  controversy: "bg-red-100 text-red-700",
  summary: "bg-gray-100 text-gray-700",
};

export default function PerspectivesPage() {
  const [perspectives, setPerspectives] = useState<Perspective[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("");

  useEffect(() => {
    loadPerspectives();
  }, [filter]);

  async function loadPerspectives() {
    setLoading(true);
    try {
      const result = await listPerspectives(filter || undefined);
      setPerspectives(result.perspectives);
    } catch (err) {
      console.error("Failed to load perspectives:", err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Perspective Discovery</h1>
        <p className="text-gray-500 mt-1">Your genuine viewpoints extracted from your knowledge base</p>
      </div>

      {/* Filters */}
      <div className="flex gap-2">
        {["", "judgment", "reflection", "lesson", "controversy", "summary"].map((type) => (
          <button
            key={type}
            onClick={() => setFilter(type)}
            className={cn(
              "px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
              filter === type
                ? "bg-blue-600 text-white"
                : "bg-white text-gray-600 border border-gray-300 hover:bg-gray-50"
            )}
          >
            {type || "All"}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading perspectives...</div>
      ) : perspectives.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
          <p className="text-gray-500">No perspectives discovered yet.</p>
          <p className="text-sm text-gray-400 mt-1">Run a content generation workflow to discover your viewpoints.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {perspectives.map((p) => (
            <div key={p.id} className="bg-white rounded-lg border border-gray-200 p-6">
              <div className="flex items-center gap-2 mb-3">
                <span className={cn("text-xs px-2 py-1 rounded-full font-medium", TYPE_COLORS[p.perspective_type] || TYPE_COLORS.summary)}>
                  {p.perspective_type}
                </span>
                <span className="text-xs text-gray-500">Confidence: {(p.confidence * 100).toFixed(0)}%</span>
                <span className="text-xs text-gray-500">Novelty: {(p.novelty * 100).toFixed(0)}%</span>
                <span className="text-xs text-gray-500">Engagement: {(p.engagement_potential * 100).toFixed(0)}%</span>
              </div>
              <p className="text-gray-800 text-lg">{p.perspective_text}</p>
              {p.user_feedback && (
                <div className="mt-3 p-3 bg-blue-50 rounded text-sm text-blue-800">
                  Your feedback: {p.user_feedback}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
