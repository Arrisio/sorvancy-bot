---
allowed-tools: Bash(git add:*), Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git commit:*)
description: Stage all modified/new files and create a commit in project style
---

## Context

- Working tree status: !`git status`
- Full diff of all changes (staged + unstaged): !`git diff HEAD`
- Recent commits (style reference): !`git log --format="%H%n%s%n%b%n---" -6`
- Current branch: !`git branch --show-current`

## Your task

### 1. Identify files to stage

**Do NOT run `git add -A`.**

Instead:

1. Look at the list of modified/new/deleted files from `git status`.
2. Cross-reference that list against files you **actually read, edited, or created in this conversation**.
3. Stage **only** the intersection — files you touched in this conversation.
4. If `git status` shows files you did NOT touch in this conversation, **skip them** and warn the user:
   > "Skipped (modified outside this conversation): <file list>"
5. Never stage `.env`, `*.pem`, `*.key`, or any file that looks like credentials — warn the user if spotted.

Stage each qualifying file explicitly:
```bash
git add path/to/file1 path/to/file2 ...
```

### 2. Compose the commit message

Follow the style of recent commits **exactly**:

**Subject line** (`type(scope): subject`):
- Conventional Commits type: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`
- Scope: the primary subsystem changed (e.g. `staff`, `coupon`, `keyboards`, `specs`, `db`)
- Subject ≤ 50 chars, imperative mood, lowercase after colon, no trailing period
- Focus on WHAT changed at a high level

**Body** (omit if subject fully explains the change):
- Blank line after subject
- Bullet list: `- component: concise explanation of what and why`
- Group bullets by file/module, not by line
- Mention migration scripts if any DB changes

**Trailer** (always present):
```
Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

### 3. Commit

Use HEREDOC to preserve formatting:

```bash
git commit -m "$(cat <<'EOF'
type(scope): subject

- module: explanation

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

Do not push. Do not open a PR. Stage and commit only.
