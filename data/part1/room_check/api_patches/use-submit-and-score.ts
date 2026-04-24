/**
 * useSubmitAndScore
 * =================
 * Thin wrapper around POST /api/submissions that returns the full new
 * response shape ({ submission, grade, teamScore, autoPromptId, ... }).
 *
 * We bypass the Orval-generated useCreateSubmission because its response
 * type is locked to the pre-grader schema. This keeps the OpenAPI spec
 * untouched until the team decides to regen.
 *
 * Save to: artifacts/gridhack/src/hooks/use-submit-and-score.ts
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getListSubmissionsQueryKey,
  getListTeamsQueryKey,
  getGetTeamQueryKey,
  getListPromptSubmissionsQueryKey,
} from "@workspace/api-client-react";

export type GradeResult = {
  team_id: number;
  filename: string;
  score: number;
  max_score: number;
  passed: string[];
  failed: { test: string; reason: string; trace?: string }[];
  log: string;
};

export type SubmitAndScoreResponse = {
  submission: {
    id: number;
    teamId: number;
    teamName: string;
    filename: string;
    code: string;
    score: number | null;
    feedback: string | null;
    submittedAt: string;
  };
  grade: GradeResult | null;
  teamScore: number;
  autoPromptId: number | null;
  autoPromptThreshold: number;
  error?: string;
};

type Args = { teamId: number; filename: string; code: string };

const API_BASE = (import.meta as any).env?.VITE_API_BASE ?? "";

async function submitAndScore(args: Args): Promise<SubmitAndScoreResponse> {
  const res = await fetch(`${API_BASE}/api/submissions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(args),
  });
  if (!res.ok && res.status !== 200 && res.status !== 201) {
    throw new Error(`Submit failed: ${res.status}`);
  }
  return res.json();
}

export function useSubmitAndScore() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: submitAndScore,
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: getListSubmissionsQueryKey() });
      qc.invalidateQueries({ queryKey: getListTeamsQueryKey() });
      qc.invalidateQueries({ queryKey: getGetTeamQueryKey(vars.teamId) });
      qc.invalidateQueries({ queryKey: getListPromptSubmissionsQueryKey() });
    },
  });
}
