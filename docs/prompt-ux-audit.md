# Prompt: UX Style Guide Audit & Fix

Use this prompt with a general-purpose Claude Code agent. Paste as-is into the agent's initial message.

---

```
You are a code auditor and implementer for the Sorvancy Max Bot project.

<task>
Audit all Python handlers for compliance with the project UX Style Guide, then fix every violation found. Existing functional behavior must not change — only UX delivery layer (message sending, editing, deleting, keyboard restore).
</task>

<mandatory_reading order="first">
Read these files before doing anything else:
1. AGENTS.md — project rules, coding standards, language rules
2. specs/ux-style-guide.md — the authoritative UX rules you are auditing against
3. docs/max-botapi.md — Max Bot API reference; all method calls must match signatures here
</mandatory_reading>

<scope>
Audit and fix only these files:
- src/handlers/start.py
- src/handlers/registration.py
- src/handlers/profile.py
- src/handlers/broadcast.py
- src/handlers/excel.py
- src/handlers/mode.py
- src/handlers/staff.py
- src/handlers/text_router.py
- src/handlers/callback_router.py
- src/handlers/callbacks/_common.py
- src/keyboards.py

Cross-reference scenario specs in specs/scenarios/*.md when handler behavior is ambiguous.
</scope>

<audit_checklist>
Read each file in scope. For every handler function, check all of the following. Record every violation before making any edits.

**Message lifecycle**
- [ ] After a terminal action (scenario complete or cancelled): are all FSM prompt messages deleted (`step_mids` cleared)?
- [ ] After a terminal action: is the actor-appropriate keyboard sent? (customer → registered_keyboard, superuser → superuser_keyboard)
- [ ] Edit used only for entity card updates or status changes — not for replacing prompts with new prompts?
- [ ] Persistent data messages (QR, discount card) never deleted?

**FSM multi-step flows**
- [ ] Every prompt message ID saved to `step_mids` in MemoryContext immediately after send?
- [ ] Every free-text-input prompt includes an [Отмена] inline button?
- [ ] Every prompt includes a progress indicator («Шаг N из M» or «Объект · шаг N из M»)?
- [ ] On cancel at step 1: no confirmation dialog, immediate cleanup?
- [ ] On cancel at step ≥ 4: confirm card shown before discarding data?

**Validation and errors**
- [ ] Validation errors re-send the same step prompt with inline explanation (not a separate error message)?
- [ ] API/system errors caught, logged, and user shown neutral message — no stack traces?

**Button idempotency**
- [ ] After callback button pressed: message with buttons replaced or deleted before (or immediately after) processing, to prevent double-tap?

**Notifications vs interactive**
- [ ] Notification messages carry no action buttons (or only [Закрыть])?
- [ ] No message mixes passive info and action buttons?

**Success message format**
- [ ] Success messages are specific (include IDs, counts, dates) — not generic («Операция выполнена»)?
</audit_checklist>

<work_protocol>
Follow these phases in order. Do not skip phases.

**Phase 1 — Audit**
Read every file in scope. Produce a violation table:

| File | Function | Rule violated | Description |
|------|----------|---------------|-------------|
| ... | ... | ... | ... |

If no violations found in a file, note it explicitly.

**Phase 2 — Plan**
For each violation, describe the exact change needed. One sentence per item. Get confirmation before proceeding if any change is ambiguous or could affect business logic.

**Phase 3 — Fix**
Apply fixes one file at a time. After each file:
- State which violations were fixed
- State which handlers in that file were NOT changed and why

**Phase 4 — Verify**
After all fixes:
1. Grep for any remaining `step_mids` tracking gaps: search for `await bot.send_message` or equivalent send calls inside FSM handlers that are NOT followed by a `step_mids` append.
2. Grep for FSM completion/cancel paths that do NOT call keyboard send.
3. Confirm no new imports, dependencies, or DB calls were introduced — fixes must be UX-layer only.

**Phase 5 — Report**
Output a summary table:

| File | Violations found | Fixed | Skipped (reason) |
|------|-----------------|-------|------------------|

End with: total violation count, total fixed count.
</work_protocol>

<hard_constraints>
- DO NOT change business logic, DB queries, state machine transitions, or API call parameters
- DO NOT add new dependencies or imports beyond what already exists in the file
- DO NOT refactor code structure — minimal targeted edits only
- DO NOT invent API methods — every bot API call must exist in docs/max-botapi.md
- If a fix requires a new keyboard factory, add it to src/keyboards.py only if a similar one does not already exist there
- If a scenario spec and the style guide conflict, the scenario spec wins — note the conflict in the report
- All user-facing strings must remain in Russian
- All code, comments, and variable names must remain in English
</hard_constraints>

<output_language>
Audit report and explanations: English (per AGENTS.md language rules).
User-facing strings in fixed code: Russian.
</output_language>
```
