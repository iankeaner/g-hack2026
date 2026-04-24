/**
 * OpenQuestionsBadge
 * ==================
 * Tiny pill on the team detail page that shows how many auto-filed
 * prompts are waiting on this team, linking to /submit pre-filtered.
 *
 * Save to: artifacts/gridhack/src/components/open-questions-badge.tsx
 */

import { Link } from "wouter";
import { Lightbulb } from "lucide-react";
import { useListPromptSubmissions } from "@workspace/api-client-react";

export default function OpenQuestionsBadge({ teamId }: { teamId: number }) {
  const { data: prompts } = useListPromptSubmissions();

  // Auto-grader-filed prompts for this team only.
  const open = (prompts ?? []).filter(
    (p: any) => p.teamId === teamId && p.memberName === "Auto-Grader"
  );

  if (open.length === 0) return null;

  const label =
    open.length === 1
      ? "1 open question for your team"
      : `${open.length} open questions for your team`;

  return (
    <Link href={`/submit?team=${teamId}`}>
      <span
        role="button"
        title="Non-tech teammates: the auto-grader filed these when a recent submission scored low. Click to help."
        data-testid={`open-questions-badge-${teamId}`}
        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full
                   text-xs font-semibold
                   bg-amber-500/15 text-amber-300 border border-amber-400/40
                   hover:bg-amber-500/25 hover:text-amber-200
                   transition-colors cursor-pointer animate-in fade-in slide-in-from-bottom-1"
      >
        <Lightbulb className="w-3 h-3" />
        {label}
      </span>
    </Link>
  );
}
