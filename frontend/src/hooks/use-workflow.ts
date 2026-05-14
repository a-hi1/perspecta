"use client";

import { useState, useCallback } from "react";
import {
  startWorkflow as apiStartWorkflow,
  getWorkflowState,
  approveWorkflow as apiApprove,
  rejectWorkflow as apiReject,
  type WorkflowState,
} from "@/lib/api";

export function useWorkflow() {
  const [workflow, setWorkflow] = useState<WorkflowState | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const start = useCallback(async (topicQuery: string = "") => {
    setLoading(true);
    setError(null);
    try {
      const state = await apiStartWorkflow(topicQuery);
      setWorkflow(state);
      return state;
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const refresh = useCallback(async (workflowId: string) => {
    try {
      const state = await getWorkflowState(workflowId);
      setWorkflow(state);
      return state;
    } catch (err: any) {
      setError(err.message);
      throw err;
    }
  }, []);

  const approve = useCallback(async (workflowId: string, editedContent?: string) => {
    setLoading(true);
    setError(null);
    try {
      const state = await apiApprove(workflowId, editedContent);
      setWorkflow(state);
      return state;
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const reject = useCallback(async (workflowId: string, feedback: string) => {
    setLoading(true);
    setError(null);
    try {
      const state = await apiReject(workflowId, feedback);
      setWorkflow(state);
      return state;
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return { workflow, loading, error, start, refresh, approve, reject };
}
