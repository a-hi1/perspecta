"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { startWorkflow, getWorkflowState, listWorkflows, type WorkflowState } from "@/lib/api";
import { AgentStatus, WorkflowTimeline } from "@/components/agent/agent-status";
import { cn } from "@/lib/utils";

export default function DashboardPage() {
  const [workflow, setWorkflow] = useState<WorkflowState | null>(null);
  const [workflowHistory, setWorkflowHistory] = useState<WorkflowState[]>([]);
  const [loading, setLoading] = useState(false);
  const [polling, setPolling] = useState(false);
  const [topicQuery, setTopicQuery] = useState("");
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setPolling(false);
  }, []);

  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  // Load history on mount
  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const history = await listWorkflows();
      setWorkflowHistory(history);
    } catch (err) {
      console.error("加载历史失败:", err);
    }
  };

  const startPolling = useCallback((workflowId: string) => {
    stopPolling();
    setPolling(true);
    let failCount = 0;
    intervalRef.current = setInterval(async () => {
      try {
        const state = await getWorkflowState(workflowId);
        failCount = 0;
        setWorkflow(state);
        if (
          state.status === "waiting_approval" ||
          state.status === "failed" ||
          state.status === "completed"
        ) {
          stopPolling();
        }
      } catch (err) {
        failCount++;
        console.error(`轮询失败 (${failCount}/5):`, err);
        if (failCount >= 5) {
          stopPolling();
        }
      }
    }, 2000);
  }, [stopPolling]);

  const handleStartWorkflow = async () => {
    setLoading(true);
    try {
      const state = await startWorkflow(topicQuery);
      setWorkflow(state);
      if (state.workflow_id) {
        startPolling(state.workflow_id);
      }
      // Refresh history after starting
      loadHistory();
    } catch (err) {
      console.error("启动失败:", err);
    } finally {
      setLoading(false);
    }
  };

  const loadWorkflowDetail = async (wf: WorkflowState) => {
    setWorkflow(wf);
    if (wf.status === "running") {
      startPolling(wf.workflow_id);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">工作台</h1>
        <p className="text-gray-500 mt-1">发现观点并生成内容</p>
      </div>

      {/* Start Workflow */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">启动内容生成</h2>
        <div className="flex gap-3">
          <input
            type="text"
            placeholder="输入话题或留空自动发现..."
            value={topicQuery}
            onChange={(e) => setTopicQuery(e.target.value)}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <button
            onClick={handleStartWorkflow}
            disabled={loading || polling}
            className={cn(
              "px-6 py-2 rounded-lg font-medium transition-colors",
              loading || polling
                ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                : "bg-blue-600 text-white hover:bg-blue-700"
            )}
          >
            {loading ? "启动中..." : polling ? "运行中..." : "开始"}
          </button>
        </div>
      </div>

      {/* Workflow Status */}
      {workflow && (
        <>
          <AgentStatus currentNode={workflow.current_node} status={workflow.status} />
          <WorkflowTimeline currentNode={workflow.current_node} />

          {polling && (
            <div className="flex items-center gap-2 text-sm text-blue-600">
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
              <span>正在执行中，每 2 秒自动刷新...</span>
            </div>
          )}

          {/* Hot Topics */}
          {workflow.hot_topics.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">发现的热点话题</h2>
              <div className="space-y-3">
                {workflow.hot_topics.map((topic, i) => (
                  <div key={i} className="p-4 bg-gray-50 rounded-lg">
                    <h3 className="font-medium text-gray-900">{topic.title}</h3>
                    <p className="text-sm text-gray-600 mt-1">{topic.summary}</p>
                    <div className="flex gap-2 mt-2">
                      <span className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded">{topic.source}</span>
                      <span className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded">评分: {topic.composite_score?.toFixed(2)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Perspectives */}
          {workflow.perspectives.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">发现的观点</h2>
              <div className="space-y-3">
                {workflow.perspectives.map((p, i) => (
                  <div key={i} className="p-4 bg-amber-50 rounded-lg border border-amber-200">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-xs px-2 py-1 bg-amber-100 text-amber-700 rounded font-medium">{p.perspective_type}</span>
                      <span className="text-xs text-gray-500">置信度: {p.confidence?.toFixed(2)}</span>
                    </div>
                    <p className="text-gray-800">{p.perspective_text}</p>
                    {p.source_quotes?.length > 0 && (
                      <div className="mt-2 pl-3 border-l-2 border-amber-300">
                        <p className="text-xs text-gray-500 italic">"{p.source_quotes[0]}"</p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Draft Preview */}
          {workflow.adapted_draft && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">生成的草稿</h2>
              <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded font-medium">{workflow.adapted_draft.draft_type}</span>
                  <span className="text-xs text-gray-500">风格匹配: {workflow.adapted_draft.style_match_score?.toFixed(2)}</span>
                </div>
                <div className="whitespace-pre-wrap text-gray-800 text-sm">{workflow.adapted_draft.content}</div>
              </div>
            </div>
          )}

          {/* Citations */}
          {workflow.citations.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">来源引用</h2>
              <div className="space-y-2">
                {workflow.citations.map((c, i) => (
                  <div key={i} className="p-3 bg-gray-50 rounded text-sm">
                    <p className="text-gray-800">"{c.cited_text}"</p>
                    <p className="text-xs text-gray-500 mt-1">来源: {c.source_file}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Evaluation */}
          {workflow.evaluation && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">质量评估</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <MetricCard label="检索相关性" value={workflow.evaluation.retrieval_relevance} />
                <MetricCard label="观点质量" value={workflow.evaluation.perspective_quality} />
                <MetricCard label="幻觉分数" value={workflow.evaluation.hallucination_score} invert />
                <MetricCard label="综合评分" value={workflow.evaluation.overall_score} />
              </div>
            </div>
          )}

          {/* Review Entry */}
          {workflow.status === "waiting_approval" && (
            <div className="bg-amber-50 rounded-lg border border-amber-200 p-6">
              <h2 className="text-lg font-semibold text-amber-900 mb-2">等待审核</h2>
              <p className="text-amber-700 mb-4">草稿已生成完毕，请前往审核页面进行审核。</p>
              <a
                href={`/review-queue?workflow_id=${workflow.workflow_id}`}
                className="inline-block px-6 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 font-medium"
              >
                前往审核
              </a>
            </div>
          )}

          {/* Completed */}
          {workflow.status === "completed" && workflow.exported_content && (
            <div className="bg-green-50 rounded-lg border border-green-200 p-6">
              <h2 className="text-lg font-semibold text-green-900 mb-2">已完成</h2>
              <p className="text-green-700 mb-4">内容已导出，可以复制使用。</p>
              <a
                href={`/review-queue?workflow_id=${workflow.workflow_id}`}
                className="inline-block px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium"
              >
                查看结果
              </a>
            </div>
          )}

          {/* Error */}
          {workflow.error && (
            <div className="bg-red-50 rounded-lg border border-red-200 p-6">
              <h2 className="text-lg font-semibold text-red-900 mb-2">错误</h2>
              <p className="text-red-700">{workflow.error}</p>
            </div>
          )}
        </>
      )}

      {/* History */}
      {workflowHistory.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">历史记录</h2>
            <button
              onClick={loadHistory}
              className="text-sm text-blue-600 hover:text-blue-700"
            >
              刷新
            </button>
          </div>
          <div className="space-y-3">
            {workflowHistory.map((wf) => (
              <div
                key={wf.workflow_id}
                onClick={() => loadWorkflowDetail(wf)}
                className={cn(
                  "p-4 border rounded-lg cursor-pointer transition-colors",
                  workflow?.workflow_id === wf.workflow_id
                    ? "border-blue-500 bg-blue-50"
                    : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"
                )}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span
                      className={cn(
                        "w-2 h-2 rounded-full",
                        wf.status === "completed"
                          ? "bg-green-500"
                          : wf.status === "waiting_approval"
                          ? "bg-amber-500"
                          : wf.status === "failed"
                          ? "bg-red-500"
                          : "bg-blue-500"
                      )}
                    />
                    <span className="font-medium text-gray-900">
                      {wf.topic_query || "自动发现"}
                    </span>
                  </div>
                  <span className="text-sm text-gray-500">
                    {new Date(wf.created_at).toLocaleString("zh-CN")}
                  </span>
                </div>
                <div className="mt-1 flex items-center gap-2 text-sm text-gray-600">
                  <StatusBadge status={wf.status} />
                  {wf.current_node && <span>当前: {wf.current_node}</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; className: string }> = {
    pending: { label: "待处理", className: "bg-gray-100 text-gray-700" },
    running: { label: "运行中", className: "bg-blue-100 text-blue-700" },
    waiting_approval: { label: "等待审核", className: "bg-amber-100 text-amber-700" },
    approved: { label: "已批准", className: "bg-green-100 text-green-700" },
    rejected: { label: "已拒绝", className: "bg-red-100 text-red-700" },
    completed: { label: "已完成", className: "bg-green-100 text-green-700" },
    failed: { label: "失败", className: "bg-red-100 text-red-700" },
  };

  const { label, className } = map[status] || map.pending;
  return <span className={cn("px-2 py-1 rounded text-xs font-medium", className)}>{label}</span>;
}

function MetricCard({ label, value, invert = false }: { label: string; value: number; invert?: boolean }) {
  const color = invert
    ? value <= 0.3 ? "text-green-600" : value <= 0.6 ? "text-amber-600" : "text-red-600"
    : value >= 0.7 ? "text-green-600" : value >= 0.4 ? "text-amber-600" : "text-red-600";

  return (
    <div className="p-4 bg-gray-50 rounded-lg text-center">
      <p className={cn("text-2xl font-bold", color)}>{(value * 100).toFixed(0)}%</p>
      <p className="text-xs text-gray-500 mt-1">{label}</p>
    </div>
  );
}
