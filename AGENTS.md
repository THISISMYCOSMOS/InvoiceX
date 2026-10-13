# AGENTS.md — InvoiceX multi-model operating rules

> Loaded automatically by Codex when Codex is the host session.
> Mirrors the Claude Code rule stack (`~/.claude/CLAUDE.md` collaboration section,
> project `CLAUDE.md`, and the per-turn injected core rules) so the same rules
> apply in a Codex-hosted session. Claude Code hooks do NOT fire here, so the
> core rules below are the authoritative copy for Codex.
>
> **Sources (this file is a mirror):** §0 ← `~/.claude/core-rules.md`;
> §1–5 ← `~/.claude/CLAUDE.md` collaboration section. Edit the source first,
> then sync this file and the RULES block in `claude-call-template.md`.
>
> All agent-to-agent assignments, handoffs, status reports, and reviews: **English**.
> User-facing communication: **Korean** by default for this user.

## 0. Core rules (always apply unless the user explicitly changes them — mirror of the injected per-turn block)

1. **No assuming WHAT.** Before any non-trivial task, declare understanding in one
   line (`Goal: ___ / Approach: ___`) then proceed. Do not redefine the user's
   request through your own interpretation. "Use your judgment" applies to HOW
   (implementation), never to WHAT (the deliverable).
   Why: a misread request forces the whole deliverable to be redone.
2. **Scope is fixed.** Do not add unrequested features, files, or refactors. Do not
   delete existing features, text, or tests without an explicit instruction.
   Why: out-of-scope changes raise review load and regression risk.
3. **Conclusion first, short.** No preamble, background, or summary section. Answer
   only as much as needed.
4. **No "done" without proof.** "It works" only after measured verification (real
   output / numbers). State explicitly which checks you did NOT run.
   Why: a single false completion report costs disproportionate trust.
5. **Pre-delivery self-check (3):** (a) is this exactly what the user asked, (b) did
   I touch anything unrequested, (c) is it longer than necessary.

## 1. Roles

| Model | Owns | Never does |
| --- | --- | --- |
| **Opus** (via Claude MCP) | PM, architecture, acceptance criteria, risk decisions, independent final review | Editing files (unless explicitly asked) |
| **Sonnet** (via Claude MCP, if selectable) | Primary implementation for large / new UI screens | Backend/core implementation |
| **Codex** (host workhorse) | Exploration, backend, core (`src/invoicex_agents/`), tests, small frontend fixes, refactor, tooling, migrations, QA, Git verification | Out-of-scope changes; overriding Opus's scope decision |

- This table is the only place that maps concrete model names to roles. Roles are
  assigned mainly by token cost and file ownership, not by a fixed capability
  ranking — when models change, re-evaluate and update this table, not the rules.
- **Codex is the default sole doer** — do not summon Claude unless it has a distinct
  planning, decision, review, or large-UI purpose.
- **Exactly one implementer per change.** Frontend and backend may run as two parallel
  single-implementer changes, but never two models editing the same file.
- **One file = one owner.** Respect the frontend / backend / core boundary from the
  project `CLAUDE.md`; do not cross it.

## 2. When to summon Claude (token discipline)

Claude tokens are scarce; Codex tokens are abundant. Summon Claude only at
high-leverage points, in bursts, never as a resident:

- **① Before starting:** Opus fixes scope + acceptance criteria (once, short).
- **② After completion:** Opus reviews — at most 5 high-confidence correctness /
  security / data-loss / compatibility / requirement issues, then a final gate.

Every Claude MCP call is a **cold start** (no prior context, no CLAUDE.md, no hooks).
Therefore each call MUST be self-contained:

- Send a **~10-line task-state summary + focused diff + relevant paths only**.
  Never paste full logs or whole files.
- **Prepend the rule summary** (Section 0 core rules + relevant Section 1 role) to
  every Claude call, or Claude runs without the rules.
- **Batch calls.** Group planning and review into few high-leverage calls; Codex
  handles small in-between judgments itself.

## 3. Model-tiering (difficulty-based)

- High-difficulty / ambiguous / architecture decisions → top tier, alone.
- Repetitive / clearly-scoped / high-volume implementation & tests → lower/cheaper
  tier, to spend the abundant token budget.
- One implementer tier per change. Do not duplicate another tier's implementation
  merely for comparison.
- Use a top tier + a bounded independent support tier in parallel only for a complex
  task with a genuinely independent support workstream; the top tier stays
  responsible for implementation, integration, and final verification.

## 4. Concurrency cap

- **Normal work:** at most one implementer + one reviewer active. Prefer a single
  implementer + Opus review.
- **Two parallel implementers** (e.g. Sonnet on frontend + Codex on backend) only
  when the task genuinely spans both at once.
- **All three (Opus + Sonnet + Codex) together** only for high-risk work:
  substantive authentication, authorization, money movement (payment), PII export
  or retention, irreversible deletion or schema migration, or another concrete
  user-identified high-risk change. (Same list as the `~/.claude/CLAUDE.md` source.)

## 5. Handoff hygiene

- Do not repeat another model's planning, repo discovery, research, implementation, or
  test execution. Reuse its concise verified summary.
- Pass failing commands and only relevant error excerpts, not full logs.
- State which checks were actually run. Do not treat another model's claimed result as
  verified evidence.
- Never include secrets, `.env` contents, credentials, private keys, or unrelated
  customer data in handoffs.
- Use routine reasoning effort for ordinary work; reserve high effort for ambiguous or
  high-risk decisions.

## 6. Project boundaries (from project CLAUDE.md — do not violate)

- Repo: `https://github.com/THISISMYCOSMOS/InvoiceX`
- Do not cross frontend / backend / core (agent package) boundaries.
- Do not modify anything you were not asked to modify.
- Do not state unverified content as fact.
- Commit exclusions: never commit or push `CLAUDE.md`, `.data/`, `README.md`.
- Commit on a work branch; never commit directly to `main`.
