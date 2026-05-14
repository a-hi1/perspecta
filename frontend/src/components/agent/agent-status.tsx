"use client";

import { cn } from "@/lib/utils";

interface AgentStatusProps {
  currentNode: string | null;
  status: string;
}

const NODE_LABELS: Record<string, { label: string; icon: string }> = {
  hot_topic: { label: "Discovering Hot Topics", icon: " " },
  topic_filter: { label: "Filtering Topics", icon: " " },
  knowledge_retriever: { label: "Retrieving Knowledge", icon: " " },
  perspective_discovery: { label: "Discovering Perspectives", icon: " " },
  angle_planner: { label: "Planning Content Angles", icon: " " },
  draft_generator: { label: "Generating Draft", icon: " " },
  style_adapter: { label: "Adapting Style", icon: " " },
  citation_verifier: { label: "Verifying Citations", icon: " " },
  human_review: { label: "Awaiting Your Review", icon: " " },
  export: { label: "Exporting Content", icon: " " },
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

  return (
    <div className="flex items-center gap-3 p-4 bg-white rounded-lg border border-gray-200">
      <div className={cn("px-3 py-1 rounded-full text-xs font-medium", statusStyle)}>
        {status.replace("_", " ").toUpperCase()}
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
