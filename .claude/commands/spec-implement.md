Implement code changes for spec commits identified by `$ARGUMENTS`.

`$ARGUMENTS` can be:
- empty → last 1 spec commit
- integer N → last N spec commits
- one or more commit hashes (short or full, space-separated)
- one or more commit message substrings (space-separated; each treated as independent search term)

## Your workflow

### Step 1 — Parse arguments

Examine `$ARGUMENTS`:

| Case | Detection | Action |
|---|---|---|
| Empty / blank | — | mode=last-n, N=1 |
| Single integer | token matches `^\d+$` | mode=last-n, N=that integer |
| Hash(es) | every token matches `^[0-9a-f]{7,40}$` | mode=by-hash, collect hashes |
| Message pattern(s) | anything else | mode=by-message, collect tokens as patterns |

Mixed hashes + messages in one call are not supported — treat as mode=by-message in that case.

### Step 2 — Find spec commits

**mode=last-n:**
```
git log --oneline -- specs/
```
Take the first N results (most recent first). Note shortfall if fewer than N exist.

**mode=by-hash:**
For each provided hash run:
```
git show --no-patch --format="%h %s" <hash>
```
Verify the hash exists. Collect as candidate commits in the order provided.

**mode=by-message:**
For each pattern run:
```
git log --oneline --grep="<pattern>" -- specs/
```
Collect all matching commits. Deduplicate by hash. Preserve chronological order (most recent first).

If no commits found for a pattern, report it and continue with remaining patterns.

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
