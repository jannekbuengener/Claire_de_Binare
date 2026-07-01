#!/usr/bin/env node
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { Agent, CursorAgentError, type SettingSource } from "@cursor/sdk";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const TOOL_DIR = path.resolve(__dirname, "..");
const REPO_ROOT = path.resolve(TOOL_DIR, "../..");
const STATE_PATH = path.join(TOOL_DIR, ".state.json");

const DEFAULT_TRIAGE_PROMPT = `Du bist im CDB-Repo (Claire_de_Binare). Führe eine GitHub-Triage durch — NUR LESEN, keine Writes (kein Merge, kein Kommentar, kein Push).

Schritte:
1. Lies CURRENT_STATUS.md für Repo-Kontext.
2. Nutze gh pr list und gh issue list für offene PRs/Issues.
3. Ordne PRs ein: merge-reif vs. blockiert (required checks, Konflikte, Review-Status).
4. Nenne die Top-3 nächsten Aktionen mit Issue/PR-Nummern.
5. Kurzbericht auf Deutsch, kompakt und action-oriented.

Policy: github_writes_via gh_cli_only — nur gh view/list/status, keine Mutationen.`;

type CliOptions = {
  prompt: string;
  fresh: boolean;
  followUp: string | null;
};

type AgentState = {
  agentId?: string;
  lastRunId?: string;
};

function parseArgs(argv: string[]): CliOptions {
  let prompt = DEFAULT_TRIAGE_PROMPT;
  let fresh = false;
  let followUp: string | null = null;

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--fresh") {
      fresh = true;
    } else if (arg === "--prompt" && argv[i + 1]) {
      prompt = argv[++i];
    } else if (arg === "--follow-up" && argv[i + 1]) {
      followUp = argv[++i];
    } else if (arg === "--help" || arg === "-h") {
      printHelp();
      process.exit(0);
    } else if (!arg.startsWith("-")) {
      // Allow trailing free-text as custom prompt.
      prompt = argv.slice(i).join(" ").trim();
      break;
    }
  }

  return { prompt, fresh, followUp };
}

function printHelp(): void {
  console.log(`CDB GitHub Triage (Cursor SDK local agent)

Usage:
  npm run triage
  npm run triage -- --prompt "Fokus: #3612 und offene Dependabot-PRs"
  npm run triage -- --follow-up "Welche blockierten PRs brauchen nur Rebase?"
  npm run triage -- --fresh

Options:
  --prompt <text>     Override default triage prompt
  --follow-up <text>  Resume prior agent and send follow-up
  --fresh             Ignore saved agent state and start new agent
  -h, --help          Show this help

Env:
  CURSOR_API_KEY      Required. From Cursor Dashboard → Integrations.

Exit codes:
  0  Run finished successfully
  1  Startup failure (auth/config/network)
  2  Run executed but ended with error status
`);
}

async function readState(): Promise<AgentState> {
  try {
    return JSON.parse(await readFile(STATE_PATH, "utf-8")) as AgentState;
  } catch {
    return {};
  }
}

async function writeState(state: AgentState): Promise<void> {
  await writeFile(STATE_PATH, JSON.stringify(state, null, 2) + "\n", "utf-8");
}

function resolveApiKey(): string {
  const apiKey = process.env.CURSOR_API_KEY?.trim();
  if (!apiKey) {
    console.error(
      "Missing CURSOR_API_KEY. Copy .env.example to .env or export the variable.",
    );
    process.exit(1);
  }
  return apiKey;
}

function agentOptions(apiKey: string) {
  return {
    apiKey,
    model: { id: "composer-2.5" as const },
    local: {
      cwd: REPO_ROOT,
      settingSources: [] as SettingSource[],
    },
  };
}

async function streamRun(run: Awaited<ReturnType<Awaited<ReturnType<typeof Agent.create>>["send"]>>): Promise<void> {
  for await (const event of run.stream()) {
    if (event.type === "status") {
      console.error(`[triage] status: ${event.status}`);
    }
    if (event.type === "assistant") {
      for (const block of event.message.content) {
        if (block.type === "text") {
          process.stdout.write(block.text);
        }
      }
    }
    if (event.type === "tool_call" && event.status !== "running") {
      console.error(`[triage] tool ${event.name}: ${event.status}`);
    }
  }
}

async function loadDotEnv(): Promise<void> {
  const envPath = path.join(TOOL_DIR, ".env");
  try {
    const content = await readFile(envPath, "utf-8");
    for (const line of content.split("\n")) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#")) continue;
      const eq = trimmed.indexOf("=");
      if (eq === -1) continue;
      const key = trimmed.slice(0, eq).trim();
      const value = trimmed.slice(eq + 1).trim();
      if (!process.env[key]) {
        process.env[key] = value;
      }
    }
  } catch {
    // .env is optional
  }
}

async function main(): Promise<void> {
  await loadDotEnv();
  const options = parseArgs(process.argv.slice(2));
  const apiKey = resolveApiKey();
  const state = options.fresh ? {} : await readState();
  const message = options.followUp ?? options.prompt;

  const opts = agentOptions(apiKey);
  const useResume = !options.fresh && Boolean(state.agentId);

  await using agent = useResume && state.agentId
    ? await Agent.resume(state.agentId, opts)
    : await Agent.create(opts);

  if (options.followUp && !state.agentId && !options.fresh) {
    console.error("[triage] no saved agent; starting fresh for follow-up");
  } else if (useResume && state.agentId) {
    console.error(`[triage] resumed agent=${agent.agentId}`);
  } else {
    console.error(`[triage] created agent=${agent.agentId}`);
  }

  try {
    const run = await agent.send(message);
    console.error(`[triage] run=${run.id}`);

    await streamRun(run);
    const result = await run.wait();

    await writeState({ agentId: agent.agentId, lastRunId: result.id });

    if (result.status === "finished") {
      if (!process.stdout.writableEnded) {
        process.stdout.write("\n");
      }
      console.error(`[triage] done in ${result.durationMs ?? "?"}ms`);
      process.exit(0);
    }

    console.error(`[triage] run ${result.id} ended as ${result.status}`);
    process.exit(2);
  } catch (err) {
    if (err instanceof CursorAgentError) {
      console.error(
        `[triage] startup failed: ${err.message} (retryable=${err.isRetryable})`,
      );
      process.exit(err.isRetryable ? 75 : 1);
    }
    throw err;
  }
}

main().catch((err: unknown) => {
  console.error(err);
  process.exit(1);
});
