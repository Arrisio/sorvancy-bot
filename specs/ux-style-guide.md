# Bot UX Style Guide

Rules for consistent user experience across all scenarios. Read before writing scenario specs or implementing handlers.

---

## 1. Message Lifecycle

### 1.1 Send new message when

- Starting a scenario or switching context
- Bot responds to user action (user turn → bot turn)
- Terminal/completion message (success confirmation, saved data summary)
- Restoring keyboard after terminal action
- Validation error feedback

### 1.2 Edit existing message when

- Inline entity card is updated (profile, broadcast card — same card, fields change)
- Replacing a placeholder with real content
- Updating object status in-place (e.g. broadcast `pending` → `sent`)

> **Decision rule:** same logical message, only data changed → edit. Context changed → new message.

### 1.3 Delete message

**Delete:**
- All FSM prompt messages on scenario completion or cancellation (`step_mids`)
- Offer message that launched the scenario (once the user acted on it)
- Intermediate service prompts that have served their purpose

**Do NOT delete:**
- Final success messages («Анкета заполнена 🎉», «Рассылка запланирована»)
- Messages containing persistent user data (QR code, discount card)
- Error messages (user must be able to re-read them)
- Messages sent by the user

---

## 2. Keyboards

**Rule:** every terminal action of a scenario restores the actor-appropriate keyboard.

| Actor | Keyboard |
|---|---|
| Customer | `registered_keyboard` |
| Staff | `registered_keyboard` (staff mode) |
| Superuser | `superuser_keyboard` |

**[Отмена] button:**
- Required on any FSM prompt awaiting free-text input
- Not required on button-choice steps (user is not blocked — they just choose a button)

**Destructive action rule:** destructive actions (delete, reset) require an explicit confirm button. Never trigger destructive action from free-text input alone.

---

## 3. Multi-step FSM Flows

- Every prompt includes a progress indicator: «Шаг N из M» or «Объект · шаг N из M»
- Every prompt saves its `mid` to `step_mids` in MemoryContext
- On completion (success) or cancellation: delete all `step_mids`, restore keyboard
- **Back navigation:** re-send previous step prompt as new message; do not delete the current prompt (it becomes the new last message)
- **Cancel at step 1:** no confirmation needed — nothing to lose yet
- **Cancel at step N ≥ 4:** show confirm card «Данные не сохранятся. Отменить?» with [Да, отменить] / [Продолжить]

---

## 4. Confirmations and Feedback

- **Confirmation card** before saving ≥ 3 fields: user must review before commit
- **Success messages:** specific, not generic
  - ✅ Good: «Рассылка #42 запланирована на 25.06 14:00. Получателей: 138»
  - ❌ Bad: «Операция выполнена»
- **Emoji as status markers** (not decoration): ✅ success · ❌ error · ⚠️ warning · ⏳ pending/waiting · 🎁 reward

---

## 5. Validation and Errors

- Validation is **inline**: error appears in the same step, prompt repeats with explanation
  - Example: «Неверный формат. Введите дату: ДД.ММ.ГГГГ»
- After **3 failed attempts** on a step: explicitly offer [Отмена] even if it wasn't there before
- API/system errors: log server-side + send neutral user message («Что-то пошло не так, попробуйте позже»). Never expose stack traces or internal IDs.

---

## 6. Button Idempotency

After a button is pressed, immediately remove or replace the message containing the buttons to prevent double-tap. Alternative: check FSM state in callback handler and silently ignore duplicate calls. Choose one approach and apply it consistently within a scenario.

---

## 7. Notifications vs Interactive Messages

- **Notification** (passive info): no inline buttons, or only [Закрыть]. Does not block FSM.
- **Interactive** (requires choice): inline buttons, FSM awaits response.

Never mix: do not add action buttons to a notification message. A message is one or the other.

---

## 8. Content Formatting

- FSM prompts: ≤ 5 lines
- Confirmation/summary cards: ≤ 10 lines
- Lists (recipients, children): show max 20 items inline; truncate remainder as «…и ещё N»
- Plain text unless the API guarantees Markdown/HTML rendering; do not embed formatting characters speculatively
