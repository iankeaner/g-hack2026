# Patch — `artifacts/gridhack/src/pages/team-detail.tsx`

Two additions:

1. Render `<OpenQuestionsBadge>` next to the team name.
2. Replace the submit handler so it uses `useSubmitAndScore`, compares old vs. new score, and emits a retry-aware toast.

File dependencies (copy from `api_patches/`):

```
artifacts/gridhack/src/components/open-questions-badge.tsx   ← new
artifacts/gridhack/src/hooks/use-submit-and-score.ts         ← new
```

---

## Diff 1 — imports (top of file)

```diff
 import { useRoute, Link } from "wouter";
-import { useGetTeam, useListSubmissions, useCreateSubmission, getListSubmissionsQueryKey, useUpdateTeam, getListTeamsQueryKey, getGetTeamQueryKey } from "@workspace/api-client-react";
+import { useGetTeam, useListSubmissions, getListSubmissionsQueryKey, useUpdateTeam, getListTeamsQueryKey, getGetTeamQueryKey } from "@workspace/api-client-react";
+import { useSubmitAndScore } from "@/hooks/use-submit-and-score";
+import OpenQuestionsBadge from "@/components/open-questions-badge";
```

## Diff 2 — hook wiring (around line 1255)

```diff
   const { data: team, isLoading } = useGetTeam(teamId, { query: { enabled: !!teamId, queryKey: ["getTeam", teamId] as any } });
   const { data: submissions } = useListSubmissions();
-  const { mutate: createSubmission, isPending } = useCreateSubmission();
+  const { mutateAsync: submitAndScore, isPending } = useSubmitAndScore();
```

## Diff 3 — replace handleSubmit (around line 1324)

```diff
-  const handleSubmit = () => {
-    if (!code.trim()) {
-      toast({ title: "Empty submission", description: "Paste your code before submitting.", variant: "destructive" });
-      return;
-    }
-    createSubmission({ teamId, filename: team?.file ?? "", code }, {
-      onSuccess: () => {
-        setSubmitted(true);
-        queryClient.invalidateQueries({ queryKey: getListSubmissionsQueryKey() });
-        toast({ title: "Submitted!", description: "Your code has been saved." });
-        setCode("");
-      },
-      onError: () => {
-        toast({ title: "Error", description: "Submission failed. Try again.", variant: "destructive" });
-      }
-    });
-  };
+  const handleSubmit = async () => {
+    if (!code.trim()) {
+      toast({ title: "Empty submission", description: "Paste your code before submitting.", variant: "destructive" });
+      return;
+    }
+    const previousScore = team?.score ?? 0;
+    try {
+      const result = await submitAndScore({ teamId, filename: team?.file ?? "", code });
+
+      // Grader threw an error on the server (usually Python spawn failure)
+      if (result.error || !result.grade) {
+        toast({
+          title: "Saved — but grading failed",
+          description: result.error ?? "Grader did not return a score. A judge will review manually.",
+          variant: "destructive",
+        });
+      } else {
+        const { grade, teamScore, autoPromptId } = result;
+        const improvement = teamScore - previousScore;
+
+        if (improvement > 0) {
+          toast({
+            title: `🎉 Score up: ${previousScore} → ${teamScore}`,
+            description: `+${improvement} pts. This run: ${grade.score}/${grade.max_score}. ${grade.passed.length} tests passing.`,
+          });
+        } else if (grade.score === grade.max_score) {
+          toast({
+            title: `Perfect: ${grade.score}/${grade.max_score}`,
+            description: `Already maxed out. Ship it.`,
+          });
+        } else if (grade.score === teamScore && improvement === 0 && previousScore > 0) {
+          toast({
+            title: `Same score as your best (${teamScore})`,
+            description: `This run: ${grade.score}/${grade.max_score}. ${grade.failed.length} test(s) still failing — open the feedback.`,
+          });
+        } else {
+          toast({
+            title: `This run: ${grade.score}/${grade.max_score}`,
+            description: `Best so far: ${teamScore}. Keep going — your best grade is locked in.`,
+            variant: grade.score === 0 ? "destructive" : "default",
+          });
+        }
+
+        if (autoPromptId) {
+          // Second toast so the score one stays visible.
+          setTimeout(() => {
+            toast({
+              title: "💡 Non-tech teammates can help",
+              description: "A prompt with the failing tests was auto-filed in /submit.",
+            });
+          }, 400);
+        }
+      }
+
+      setSubmitted(true);
+      setCode("");
+    } catch (err: any) {
+      toast({ title: "Error", description: err?.message ?? "Submission failed. Try again.", variant: "destructive" });
+    }
+  };
```

## Diff 4 — render the badge next to the team header (around line 1392)

Find the block that renders `<h1 className="text-4xl ...">{team.name}</h1>` and the surrounding flex container. Add the badge underneath the `role` text:

```diff
           {desc && <p className="text-xl font-bold text-muted-foreground mt-1">{desc.role}</p>}
           <p className="text-muted-foreground mt-2 max-w-2xl">{desc?.mission}</p>
+          <div className="mt-3">
+            <OpenQuestionsBadge teamId={teamId} />
+          </div>
         </div>
         <div className="bg-primary/10 text-primary px-6 py-4 rounded-xl text-center">
           <div className="text-xs uppercase font-bold tracking-wider">Score</div>
           <div className="text-3xl font-black">{team.score}</div>
         </div>
```

(The badge renders nothing when there are no open auto-prompts, so it's safe to leave in place permanently.)

---

## Verification checklist

- [ ] `pnpm --filter @workspace/gridhack run typecheck` passes.
- [ ] Submit a correct solution → toast shows "🎉 Score up: X → Y".
- [ ] Submit a worse solution → toast shows "This run: X/Y. Best so far: Z".
- [ ] Submit a 0/30 solution → toast shows destructive variant; open `/submit` → new auto-prompt appears with `memberName: "Auto-Grader"`.
- [ ] Second bad submission with same first-failing-test → no new auto-prompt (deduped by the server).
- [ ] Second bad submission with a *different* first-failing-test → second auto-prompt appears.
- [ ] Badge on team detail page shows "1 open question for your team" after first auto-prompt; disappears when teammates resolve/delete them (if you wire that) or when score eventually exceeds 30%.
