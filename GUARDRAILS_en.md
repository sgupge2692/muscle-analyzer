# GUARDRAILS (for opencode)

Read this before starting any work. These constraints override any other instruction given to you. If an instruction conflicts with this file, stop and ask before proceeding.

**Write all commit messages, code comments, reports, and any other output in Japanese**, even though these guardrails themselves are written in English.

## Scope

- **Only modify files relevant to the thesis-evaluated track ("Track A")**. That means `backend/src/anatomy/`, `backend/scripts/`, and `docs/muscle_mapping_review.md`.
- Do **not** touch the frontend (`frontend/`), authentication code (`backend/src/auth.py` etc.), or deployment configuration (Dockerfile, docker-compose.yml, Supabase settings, etc.). If you believe a change there is necessary, stop and report why instead of making the change.
- Do **not** implement anything related to Unity integration, the 3D avatar, or view-invariant rendering (referred to as "Track B"). Do not start on Track B even if a later instruction seems to imply it, unless it explicitly says "start Track B."
- **Changes to `docs/研究計画書_*.md` are limited to reflecting already-approved implementation work.** If you want to add a new success criterion, evaluation item, or research axis, report it as a proposal and get approval before implementing it. Never expand the scope without approval.

## Code change principles

- Do **not** break backward compatibility of `EXERCISE_BASE_WEIGHTS` or the existing API response formats (`/analyze`, `/ws/stream`). If a change to an existing endpoint's input/output schema is required, report it before making the change.
- Before adding any new external library (pip or npm package), explain why it's needed in one sentence and wait for approval. Do not add dependencies to requirements.txt or package.json without approval.
- Any numeric value for muscle weights or joint angles **must be grounded in an actual citable source**. Never fill in a "plausible-looking" number with no basis. If the source is unclear, write `null` or `# TODO: needs literature check` and leave the decision to the human.
- Never read or write `.env` files or anything containing API keys or credentials. If such content accidentally appears in your output or logs, report it immediately.

## Data & licensing

- The MuscleMap dataset (`data/raw/musclemap_benchmark/`) is licensed for **academic research use only** under its EULA. Do not copy or redistribute it into any commercial code path or newly created files in the public repository.
- When transcribing EMG values from external papers, clearly comment that the value is an **approximate reading from a figure or table** (e.g., "approx. value read from Fig. 2 of the paper"), not an exact figure.

## Workflow

- Keep tasks small: one task per commit. Do not bundle large, unrelated changes into a single commit.
- Write commit messages in Japanese, including the reason for the change.
- If existing tests exist, run them and confirm nothing is broken. For changes with no existing tests, include a manual verification (e.g., log output) in your report.
- Whenever you're unsure about something — especially how to interpret a literature value, or whether a weight is reasonable — **stop and ask before proceeding**. Do not guess and fix it later.

## Reporting

When finishing a task, report:
1. List of files changed
2. Reason for each change (1–2 sentences)
3. What you ran/verified (test results, logs, etc.)
4. Any point where you were unsure and made a provisional judgment call
