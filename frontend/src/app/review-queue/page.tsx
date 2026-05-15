"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { getWorkflowState, approveWorkflow, rejectWorkflow, type WorkflowState } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function ReviewQueuePage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-gray-500">加载中...</div>}>
      <ReviewQueueContent />
    </Suspense>
  );
}

function ReviewQueueContent() {
  const searchParams = useSearchParams();
  const workflowId = searchParams.get("workflow_id");

  const [workflow, setWorkflow] = useState<WorkflowState | null>(null);
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState("");
  const [editedContent, setEditedContent] = useState("");
  const [actionLoading, setActionLoading] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (workflowId) {
      loadWorkflow(workflowId);
    } else {
      setLoading(false);
    }
  }, [workflowId]);

  async function loadWorkflow(id: string) {
    try {
      const state = await getWorkflowState(id);
      setWorkflow(state);
      const draft = state.adapted_draft || state.selected_draft;
      if (draft) {
        setEditedContent(draft.content);
      }
    } catch (err) {
      console.error("Failed to load workflow:", err);
    } finally {
      setLoading(false);
    }
  }

  async function handleApprove() {
    if (!workflowId) return;
    setActionLoading(true);
    setMessage("");
    try {
      const state = await approveWorkflow(workflowId, editedContent);
      setWorkflow(state);
      setMessage("已批准并导出！");
    } catch (err: any) {
      setMessage(`批准失败: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  }

  async function handleReject() {
    if (!workflowId || !feedback.trim()) return;
    setActionLoading(true);
    setMessage("");
    try {
      const state = await rejectWorkflow(workflowId, feedback);
      setWorkflow(state);
      setFeedback("");
      setMessage("已拒绝，正在重新生成...");
    } catch (err: any) {
      setMessage(`拒绝失败: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  }

  if (loading) {
    return <div className="p-8 text-center text-gray-500">加载中...</div>;
  }

  if (!workflowId || !workflow) {
    return (
      <div className="space-y-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">审核队列</h1>
          <p className="text-gray-500 mt-1">审核、批准或要求修改生成的内容</p>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-12 text-center text-gray-500">
          <p className="mb-4">暂无待审核的工作流。</p>
          <p className="text-sm">请从工作台启动内容生成流程，到达审核阶段后会自动跳转到此页面。</p>
          <a href="/dashboard" className="inline-block mt-4 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            前往工作台
          </a>
        </div>
      </div>
    );
  }

  const draft = workflow.adapted_draft || workflow.selected_draft;
  const isWaiting = workflow.status === "waiting_approval";
  const isCompleted = workflow.status === "completed";
  const isRejected = workflow.status === "rejected";

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">审核队列</h1>
        <p className="text-gray-500 mt-1">
          工作流: {workflowId.slice(0, 8)}...
          <span className={cn(
            "ml-2 px-2 py-0.5 rounded text-xs font-medium",
            isWaiting && "bg-amber-100 text-amber-700",
            isCompleted && "bg-green-100 text-green-700",
            isRejected && "bg-red-100 text-red-700",
          )}>
            {workflow.status}
          </span>
        </p>
      </div>

      {message && (
        <div className={cn(
          "p-4 rounded-lg text-sm",
          message.includes("失败") ? "bg-red-50 text-red-700" : "bg-green-50 text-green-700"
        )}>
          {message}
        </div>
      )}

      {draft ? (
        <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-6">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">{draft.title}</h2>
            <p className="text-sm text-gray-500 mt-1">
              {draft.draft_type} | 风格匹配: {draft.style_match_score?.toFixed(2)}
              {workflow.revision_count > 0 && ` | 修订次数: ${workflow.revision_count}`}
            </p>
          </div>

          {/* Content Editor */}
          <div>
            <label className="text-sm font-medium text-gray-700 mb-2 block">正文内容</label>
            <textarea
              value={editedContent}
              onChange={(e) => setEditedContent(e.target.value)}
              rows={12}
              disabled={!isWaiting}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm disabled:bg-gray-50"
            />
          </div>

          {/* Citations */}
          {workflow.citations?.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-2">来源引用</h3>
              <div className="space-y-2">
                {workflow.citations.map((c: any, i: number) => (
                  <div key={i} className="p-3 bg-gray-50 rounded text-sm">
                    <p className="text-gray-800">"{c.cited_text}"</p>
                    <p className="text-xs text-gray-500 mt-1">来源: {c.source_file}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Feedback */}
          {isWaiting && (
            <div>
              <label className="text-sm font-medium text-gray-700 mb-2 block">修改反馈（拒绝时填写）</label>
              <textarea
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                placeholder="说明需要修改的内容..."
                rows={3}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
              />
            </div>
          )}

          {/* Actions */}
          {isWaiting && (
            <div className="flex gap-3">
              <button
                onClick={handleApprove}
                disabled={actionLoading}
                className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium disabled:opacity-50"
              >
                {actionLoading ? "处理中..." : "批准并导出"}
              </button>
              <button
                onClick={handleReject}
                disabled={actionLoading || !feedback.trim()}
                className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium disabled:opacity-50"
              >
                {actionLoading ? "处理中..." : "要求修改"}
              </button>
            </div>
          )}

          {/* Exported Content */}
          {isCompleted && workflow.exported_content && (
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-2">导出内容</h3>
              <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                <pre className="whitespace-pre-wrap text-sm text-gray-800">{workflow.exported_content}</pre>
                <button
                  onClick={() => navigator.clipboard.writeText(workflow.exported_content)}
                  className="mt-3 px-4 py-1.5 bg-green-600 text-white text-sm rounded hover:bg-green-700"
                >
                  复制到剪贴板
                </button>
              </div>
            </div>
          )}

          {/* Human Feedback */}
          {isRejected && workflow.human_feedback && (
            <div className="p-4 bg-red-50 rounded-lg border border-red-200">
              <h3 className="text-sm font-medium text-red-700 mb-1">拒绝反馈</h3>
              <p className="text-sm text-red-600">{workflow.human_feedback}</p>
            </div>
          )}
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 p-12 text-center text-gray-500">
          工作流尚未生成草稿
        </div>
      )}
    </div>
  );
}
