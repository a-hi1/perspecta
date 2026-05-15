"use client";

import { useState, useEffect } from "react";
import { startWorkflow, getWorkflowState, type WorkflowState } from "@/lib/api";
import { AgentStatus, WorkflowTimeline } from "@/components/agent/agent-status";
import { cn } from "@/lib/utils";

export default function DashboardPage() {
  const [workflow, setWorkflow] = useState<WorkflowState | null>(null);
  const [loading, setLoading] = useState(false);
  const [topicQuery, setTopicQuery] = useState("");

  const handleStartWorkflow = async () => {
    setLoading(true);
    try {
      const state = await startWorkflow(topicQuery);
      setWorkflow(state);
    } catch (err) {
      console.error("Failed to start workflow:", err);
    } finally {
      setLoading(false);
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
            disabled={loading}
            className={cn(
              "px-6 py-2 rounded-lg font-medium transition-colors",
              loading
                ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                : "bg-blue-600 text-white hover:bg-blue-700"
            )}
          >
            {loading ? "启动中..." : "开始"}
          </button>
        </div>
      </div>

      {/* Workflow Status */}
      {workflow && (
        <>
          <AgentStatus currentNode={workflow.current_node} status={workflow.status} />
          <WorkflowTimeline currentNode={workflow.current_node} />

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

          {/* Error */}
          {workflow.error && (
            <div className="bg-red-50 rounded-lg border border-red-200 p-6">
              <h2 className="text-lg font-semibold text-red-900 mb-2">错误</h2>
              <p className="text-red-700">{workflow.error}</p>
            </div>
          )}
        </>
      )}
    </div>
  );
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
