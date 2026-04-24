/**
 * Replacement for artifacts/api-server/src/routes/submissions.ts
 *
 * Adds:
 *  - dynamic auto-scoring via the Python grader
 *  - teams.score updates to best-ever grade
 *  - AUTO-PROMPT-ON-LOW-SCORE: when a submission scores below a configurable
 *    threshold (default 30% of max), a prompt_submission row is inserted so
 *    non-tech teammates can help the team redirect without the coder asking.
 *
 * Drop-in: replace artifacts/api-server/src/routes/submissions.ts, commit,
 *          restart API.
 */

import { Router } from "express";
import { spawn } from "node:child_process";
import { mkdtempSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { db, teamsTable, submissionsTable, promptSubmissionsTable } from "@workspace/db";
import { desc, eq } from "drizzle-orm";

const router = Router();

const GRADER_PATH =
  process.env.GRADER_PATH ??
  join(process.cwd(), "room_check", "grading", "auto_grade.py");

const CONFIG_PATH =
  process.env.GRADER_CONFIG ??
  join(process.cwd(), "room_check", "thresholds.json");

const PYTHON = process.env.PYTHON_BIN ?? "python3";
const GRADER_TIMEOUT_MS = 15_000;

// Anything below this fraction of max_score files an auto-prompt.
const AUTO_PROMPT_BELOW = Number(process.env.AUTO_PROMPT_BELOW ?? "0.3");

type GradeResult = {
  team_id: number;
  filename: string;
  score: number;
  max_score: number;
  passed: string[];
  failed: { test: string; reason: string; trace?: string }[];
  log: string;
};

// ─────────────────────── grader shell ─────────────────────────────────
function runGrader(teamId: number, filename: string, code: string): Promise<GradeResult> {
  return new Promise((resolve, reject) => {
    const dir = mkdtempSync(join(tmpdir(), "submission-"));
    const file = join(dir, filename);
    writeFileSync(file, code);

    const proc = spawn(PYTHON, [
      GRADER_PATH,
      "--team", String(teamId),
      "--file", file,
      "--config", CONFIG_PATH,
      "--json",
    ], { stdio: ["ignore", "pipe", "pipe"] });

    let stdout = "";
    let stderr = "";
    proc.stdout.on("data", (d) => (stdout += d));
    proc.stderr.on("data", (d) => (stderr += d));

    const timer = setTimeout(() => {
      proc.kill("SIGKILL");
      reject(new Error(`Grader timed out after ${GRADER_TIMEOUT_MS}ms`));
    }, GRADER_TIMEOUT_MS);

    proc.on("close", (code) => {
      clearTimeout(timer);
      rmSync(dir, { recursive: true, force: true });
      if (!stdout) {
        return reject(new Error(`Grader produced no output (exit ${code}). stderr: ${stderr}`));
      }
      try {
        resolve(JSON.parse(stdout.trim().split("\n").pop()!));
      } catch {
        reject(new Error(`Grader output was not JSON: ${stdout}`));
      }
    });
  });
}

// ─────────────── auto-prompt on low score ─────────────────────────────
/**
 * When a team's submission scores below AUTO_PROMPT_BELOW of max, file a
 * friendly prompt_submission so non-tech members can see what's stuck and
 * write help. Deduplicates against the last auto-prompt for the same team
 * + first-failed-test so we don't spam the page on repeated low scores.
 */
async function maybeFileAutoPrompt(
  teamId: number,
  teamName: string,
  filename: string,
  grade: GradeResult,
): Promise<number | null> {
  if (grade.max_score === 0) return null;
  const ratio = grade.score / grade.max_score;
  if (ratio >= AUTO_PROMPT_BELOW) return null;
  if (grade.failed.length === 0) return null;

  const firstFail = grade.failed[0];
  const failTag = `[auto:${firstFail.test}]`;

  // Dedupe: look for an existing auto-prompt on this team with the same tag.
  const existing = await db
    .select()
    .from(promptSubmissionsTable)
    .where(eq(promptSubmissionsTable.teamId, teamId));
  if (existing.some((r) => (r.context ?? "").includes(failTag))) return null;

  const promptText = buildAutoPromptText(teamName, filename, grade);
  const context = [
    failTag,
    `auto-generated after submission scored ${grade.score}/${grade.max_score}`,
    `first failing test: ${firstFail.test} — ${firstFail.reason}`,
  ].join(" | ");

  const [row] = await db.insert(promptSubmissionsTable).values({
    teamId,
    teamName,
    memberName: "Auto-Grader",
    promptType: "question",
    prompt: promptText,
    context,
  }).returning();

  return row.id;
}

function buildAutoPromptText(teamName: string, filename: string, grade: GradeResult): string {
  const failed = grade.failed.slice(0, 3).map((f) => `• ${f.test}: ${f.reason}`).join("\n");
  const passed = grade.passed.length
    ? `Already working: ${grade.passed.join(", ")}.`
    : `Nothing passing yet.`;
  return [
    `Team ${teamName}'s last submission of ${filename} scored ${grade.score}/${grade.max_score}.`,
    ``,
    `${passed}`,
    ``,
    `These tests are failing:`,
    failed,
    ``,
    `Non-technical teammates: can you talk this through in plain language?`,
    `• What is this file supposed to do in the library?`,
    `• What would a librarian *need* to see in the output?`,
    `• Is there a real scenario (smoke event, heat wave, weekend) the code is ignoring?`,
    ``,
    `Write a concrete, 2-4 sentence description the coder can use as their next target.`,
  ].join("\n");
}

// ─────────────────────── routes ───────────────────────────────────────

// GET /api/submissions  — list all
router.get("/", async (_req, res, next) => {
  try {
    const rows = await db.select().from(submissionsTable).orderBy(desc(submissionsTable.submittedAt));
    res.json(rows);
  } catch (err) {
    next(err);
  }
});

// POST /api/submissions
router.post("/", async (req, res, next) => {
  try {
    const { teamId, filename, code } = req.body ?? {};
    if (!teamId || !filename || !code) {
      return res.status(400).json({ error: "teamId, filename, and code are required" });
    }

    const [team] = await db.select().from(teamsTable).where(eq(teamsTable.id, teamId));
    if (!team) return res.status(404).json({ error: "Team not found" });

    let grade: GradeResult;
    try {
      grade = await runGrader(team.teamNumber, filename, code);
    } catch (err: any) {
      const [saved] = await db.insert(submissionsTable).values({
        teamId,
        teamName: team.name,
        filename,
        code,
        score: null,
        feedback: `Grader error: ${err.message}`,
      }).returning();
      return res.status(200).json({ submission: saved, grade: null, error: err.message });
    }

    const feedback = JSON.stringify({ passed: grade.passed, failed: grade.failed });

    const [saved] = await db.insert(submissionsTable).values({
      teamId, teamName: team.name, filename, code,
      score: grade.score, feedback,
    }).returning();

    // Keep team.score = best grade so far.
    const best = Math.max(team.score ?? 0, grade.score);
    if (best !== team.score) {
      await db.update(teamsTable).set({ score: best }).where(eq(teamsTable.id, teamId));
    }

    // Fire-and-forget auto-prompt creation. We do wait for the id so we can
    // return it in the response for the UI to link to /submit.
    let autoPromptId: number | null = null;
    try {
      autoPromptId = await maybeFileAutoPrompt(teamId, team.name, filename, grade);
    } catch (err: any) {
      console.error("auto-prompt failed:", err);
    }

    res.status(201).json({
      submission: saved,
      grade,
      teamScore: best,
      autoPromptId,                                // null unless one was filed
      autoPromptThreshold: AUTO_PROMPT_BELOW,
    });
  } catch (err) {
    next(err);
  }
});

// GET /api/submissions/:id — with parsed feedback
router.get("/:id", async (req, res, next) => {
  try {
    const id = Number(req.params.id);
    const [row] = await db.select().from(submissionsTable).where(eq(submissionsTable.id, id));
    if (!row) return res.status(404).json({ error: "not found" });
    const parsed = row.feedback ? (() => { try { return JSON.parse(row.feedback!); } catch { return row.feedback; } })() : null;
    res.json({ ...row, feedback: parsed });
  } catch (err) {
    next(err);
  }
});

// POST /api/submissions/regrade/:id — judges only
router.post("/regrade/:id", async (req, res, next) => {
  try {
    const id = Number(req.params.id);
    const [sub] = await db.select().from(submissionsTable).where(eq(submissionsTable.id, id));
    if (!sub) return res.status(404).json({ error: "submission not found" });

    const [team] = await db.select().from(teamsTable).where(eq(teamsTable.id, sub.teamId));
    if (!team) return res.status(404).json({ error: "team not found" });

    const grade = await runGrader(team.teamNumber, sub.filename, sub.code);

    await db.update(submissionsTable).set({
      score: grade.score,
      feedback: JSON.stringify({ passed: grade.passed, failed: grade.failed }),
    }).where(eq(submissionsTable.id, id));

    const best = Math.max(team.score ?? 0, grade.score);
    if (best !== team.score) {
      await db.update(teamsTable).set({ score: best }).where(eq(teamsTable.id, team.id));
    }

    const autoPromptId = await maybeFileAutoPrompt(team.id, team.name, sub.filename, grade).catch(() => null);
    res.json({ grade, teamScore: best, autoPromptId });
  } catch (err) {
    next(err);
  }
});

export default router;
