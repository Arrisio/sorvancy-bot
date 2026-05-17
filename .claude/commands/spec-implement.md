Implement code changes for the last N spec commits. N = $ARGUMENTS (default: 1 if empty).

## Your workflow

### Step 1 — Parse N
If `$ARGUMENTS` is empty or blank, use N=1. Otherwise parse N from `$ARGUMENTS`.

### Step 2 — Find spec commits
Run: `git log --oneline -- specs/`
Take the first N results. These are the candidate commits (most recent first).

If fewer than N commits touch `specs/`, process what exists and note the shortfall.

### Step 3 — Validate each commit (STOP ON CODE CHANGES)

For each candidate commit hash, run:
```
git diff-tree --no-commit-id -r --name-only <hash>
```

Classify every changed file:
- **spec file**: path starts with `specs/`
- **code file**: anything else (`src/`, `main.py`, `config.py`, `scripts/`, `*.toml`, `*.sql`, etc.)

**If any code file appears in a commit:**
STOP immediately. Do not process any further commits. Report exactly:
```
STOP: commit <short-hash> "<commit message>" contains code changes:
  <list of non-spec files>

Cannot auto-implement. Options:
1. Skip this commit, process remaining N-1
2. Abort entirely
3. Proceed anyway (treat code changes as intentional context)

Which?
```
Wait for user instruction before continuing.

### Step 4 — Collect spec diffs
For each validated (spec-only) commit, run:
```
git show <hash> -- specs/
```
Collect all added/modified/deleted spec content.

### Step 5 — Read affected spec files
Read current content of every spec file that was changed across all collected commits. Use the Read tool. This gives you the final intended state.

### Step 6 — Read existing code
Before touching any code, read:
- `AGENTS.md` (always)
- Every `src/` file relevant to the changed specs
- `docs/max-botapi.md` if handlers/keyboards/API calls involved

### Step 7 — Implement
Apply changes to make code match specs. Follow all rules in `AGENTS.md`:
- Async everywhere
- Config only via `config.py`
- DB via SQLAlchemy ORM (`src/db/orm.py`)
- States in `MemoryContext`
- Models: ORM queries only, no business logic
- No hardcoded values

If spec describes new DB fields → update `src/db/migrations.sql` and ORM models.
If spec describes new scenario → add handler in `src/handlers/`.
If spec describes new keyboard → update `src/keyboards.py`.

### Step 8 — Report
```
Processed commits: <N>
  <short-hash> — <commit message>

Files changed:
  <list of src files touched>

Spec changes implemented:
  <bullet per logical change>

Skipped / open questions:
  <anything not implemented + why>
```

## Rules

- Never edit spec files — only read them
- If two commits contradict each other, use the newer commit (first in git log order) and flag the contradiction
- If spec has open questions (`[ ]`), do not implement those parts — note them in report
- Bot user-facing strings: Russian. Code, comments, reports: English
