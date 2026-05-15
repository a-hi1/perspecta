"use client";

import { cn } from "@/lib/utils";

interface AgentStatusProps {
  currentNode: string | null;
  status: string;
}

const NODE_LABELS: Record<string, { label: string; icon: string }> = {
  hot_topic: { label: "发现热点话题", icon: " " },
  topic_selection: { label: "选择话题", icon: " " },
  retrieval_and_perspective: { label: "检索与发现观点", icon: " " },
  content_generation: { label: "生成内容", icon: " " },
  citation_verification: { label: "验证引用", icon: " " },
  human_review: { label: "等待审核", icon: " " },
};

const STATUS_LABELS: Record<string, string> = {
  pending: "待处理",
  running: "运行中",
  waiting_approval: "等待审核",
  approved: "已批准",
  rejected: "已拒绝",
  completed: "已完成",
  failed: "失败",
};

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-gray-100 text-gray-600",
  running: "bg-blue-100 text-blue-700 animate-pulse",
  waiting_approval: "bg-amber-100 text-amber-700",
  approved: "bg-green-100 text-green-700",
  rejected: "bg-red-100 text-red-700",
  completed: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

export function AgentStatus({ currentNode, status }: AgentStatusProps) {
  const nodeInfo = currentNode ? NODE_LABELS[currentNode] : null;
  const statusStyle = STATUS_STYLES[status] || STATUS_STYLES.pending;
  const statusLabel = STATUS_LABELS[status] || status;

  return (
    <div className="flex items-center gap-3 p-4 bg-white rounded-lg border border-gray-200">
      <div className={cn("px-3 py-1 rounded-full text-xs font-medium", statusStyle)}>
        {statusLabel}
      </div>
      {nodeInfo && (
        <div className="flex items-center gap-2 text-sm text-gray-700">
          <span className="text-lg">{nodeInfo.icon}</span>
          <span>{nodeInfo.label}</span>
        </div>
      )}
    </div>
  );
}

export function WorkflowTimeline({ currentNode }: { currentNode: string | null }) {
  const nodes = Object.keys(NODE_LABELS);
  const currentIndex = currentNode ? nodes.indexOf(currentNode) : -1;

  return (
    <div className="flex items-center gap-1 overflow-x-auto py-2">
      {nodes.map((node, i) => {
        const info = NODE_LABELS[node];
        const isComplete = i < currentIndex;
        const isCurrent = i === currentIndex;
        const isPending = i > currentIndex;

        return (
          <div key={node} className="flex items-center">
            <div
              className={cn(
                "flex items-center gap-1 px-2 py-1 rounded text-xs whitespace-nowrap",
                isComplete && "bg-green-50 text-green-700",
                isCurrent && "bg-blue-50 text-blue-700 font-medium",
                isPending && "bg-gray-50 text-gray-400"
              )}
            >
              <span>{info.icon}</span>
              <span className="hidden lg:inline">{info.label}</span>
            </div>
            {i < nodes.length - 1 && (
              <div
                className={cn(
                  "w-4 h-px mx-1",
                  isComplete ? "bg-green-300" : "bg-gray-200"
                )}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
