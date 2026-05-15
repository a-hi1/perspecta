"use client";

import { useState, useEffect } from "react";
import { listDrafts } from "@/lib/api";
import { formatDate, truncate } from "@/lib/utils";
import { cn } from "@/lib/utils";

interface Draft {
  id: string;
  title: string;
  content: string;
  draft_type: string;
  hook: string | null;
  cta: string | null;
  style_match_score: number;
  status: string;
  version: number;
  created_at: string;
}

const TYPE_LABELS: Record<string, string> = {
  professional: "专业型",
  story: "故事型",
  controversial: "争议型",
};

export default function DraftStudioPage() {
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDraft, setSelectedDraft] = useState<Draft | null>(null);
  const [editedContent, setEditedContent] = useState("");
  const [saveMessage, setSaveMessage] = useState("");

  useEffect(() => {
    loadDrafts();
  }, []);

  async function loadDrafts() {
    try {
      const result = await listDrafts();
      setDrafts(result.drafts);
    } catch (err) {
      console.error("Failed to load drafts:", err);
    } finally {
      setLoading(false);
    }
  }

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(editedContent);
      setSaveMessage("已复制到剪贴板！");
      setTimeout(() => setSaveMessage(""), 2000);
    } catch {
      setSaveMessage("复制失败");
    }
  }

  async function handleSave() {
    if (!selectedDraft) return;
    try {
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const res = await fetch(`${API_BASE}/drafts/${selectedDraft.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: editedContent }),
      });
      if (!res.ok) throw new Error("保存失败");
      setSaveMessage("已保存！");
      setTimeout(() => setSaveMessage(""), 2000);
    } catch (err: any) {
      setSaveMessage(err.message || "保存失败");
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">草稿编辑</h1>
        <p className="text-gray-500 mt-1">查看和编辑生成的内容草稿</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Draft List */}
        <div className="lg:col-span-1 space-y-3">
          <h2 className="text-sm font-medium text-gray-500 uppercase">草稿 ({drafts.length})</h2>
          {loading ? (
            <p className="text-gray-500 text-sm">加载中...</p>
          ) : drafts.length === 0 ? (
            <div className="p-4 bg-white rounded-lg border border-gray-200 text-center text-gray-500 text-sm">
              暂无草稿。启动工作流来生成内容。
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
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs px-2 py-0.5 bg-gray-100 rounded">{TYPE_LABELS[draft.draft_type] || draft.draft_type}</span>
                  <span className="text-xs text-gray-400">v{draft.version}</span>
                </div>
                <p className="text-sm font-medium text-gray-900">{truncate(draft.title, 40)}</p>
                <p className="text-xs text-gray-500 mt-1">{formatDate(draft.created_at)}</p>
              </button>
            ))
          )}
        </div>

        {/* Draft Editor */}
        <div className="lg:col-span-2">
          {selectedDraft ? (
            <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">{selectedDraft.title}</h2>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs px-2 py-1 bg-gray-100 rounded">{TYPE_LABELS[selectedDraft.draft_type]}</span>
                    <span className="text-xs text-gray-500">风格匹配: {(selectedDraft.style_match_score * 100).toFixed(0)}%</span>
                    <span className="text-xs text-gray-500">版本 {selectedDraft.version}</span>
                  </div>
                </div>
              </div>

              {selectedDraft.hook && (
                <div className="p-3 bg-amber-50 rounded-lg">
                  <p className="text-xs font-medium text-amber-700 mb-1">开头吸引</p>
                  <p className="text-sm text-amber-900">{selectedDraft.hook}</p>
                </div>
              )}

              <div>
                <label className="text-sm font-medium text-gray-700 mb-2 block">正文内容</label>
                <textarea
                  value={editedContent}
                  onChange={(e) => setEditedContent(e.target.value)}
                  rows={16}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                />
              </div>

              {selectedDraft.cta && (
                <div className="p-3 bg-green-50 rounded-lg">
                  <p className="text-xs font-medium text-green-700 mb-1">行动号召</p>
                  <p className="text-sm text-green-900">{selectedDraft.cta}</p>
                </div>
              )}

              {saveMessage && (
                <p className="text-sm text-green-600">{saveMessage}</p>
              )}

              <div className="flex gap-3">
                <button
                  onClick={handleCopy}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium"
                >
                  复制到剪贴板
                </button>
                <button
                  onClick={handleSave}
                  className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm font-medium"
                >
                  保存修改
                </button>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-lg border border-gray-200 p-12 text-center text-gray-500">
              选择一份草稿进行查看和编辑
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
