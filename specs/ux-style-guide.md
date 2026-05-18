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

### 2.1 Persistent keyboards by actor role

Middleware detects actor on every message — see `nfr/middleware-routing.md`. Every terminal action of a scenario restores the actor-appropriate keyboard.

**Customer** — `registered_keyboard`
Shown to: registered Customer; Staff with `customer_mode = true`

| Row | Button | Scenario |
|-----|--------|----------|
| 1 | «🎁 Скидка и купоны» | → 03 Discount QR |
| 2 | «Мой профиль» | → 05 Profile Editing |
| 2 | «Связаться с продавцом» | → 17 Contact Seller |

**Staff** (`is_owner = false`, `customer_mode = false`) — `staff_keyboard`

| Button | Scenario |
|--------|----------|
| «Найти профиль» | → 10 Find Customer Profile by ID |

Note: Staff triggers scenario 06 (Show Customer Profile) via deeplink — no keyboard button needed.

**Superuser** (`is_owner = true`, `customer_mode = false`) — `superuser_keyboard`

| Button | Scenario |
|--------|----------|
| «Найти профиль» | → 10 Find Customer Profile by ID |
| «Excel» | → 13 Excel Export |
| «Показать продавцов» | → 09 Staff List Management |
| «Запустить рассылку» | → 11 Create and Schedule Broadcast |
| «Запланированные рассылки» | → 12 Show Scheduled Broadcasts |
| «Финансовые настройки» | → 22 Edit Financial Parameters |

Note: Superuser registers sellers via contact card forwarding — no keyboard button; out-of-band onboarding by design.

`/mode` command available to Superuser at any time regardless of `customer_mode` — see scenario 14.

### 2.2 Transient keyboards

Mid-flow keyboards shown during specific scenarios. Defined in their owning scenario spec. Named in `specs/glossary.md` for cross-reference only.

### 2.3 [Отмена] button

- Required on any FSM prompt awaiting free-text input
- Not required on button-choice steps (user is not blocked — they just choose a button)

### 2.4 Destructive actions

Destructive actions (delete, reset) require explicit confirm button. Never trigger destructive action from free-text input alone.

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
