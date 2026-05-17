# Scenario: Survey (Phase 2 — Profile Enrichment)

## Goal
User fills in profile with personal data and children; receives 300-ruble coupon on first successful completion.

## Actors
- User (registered)
- Bot
- Database

## Trigger
User clicks «Заполнить анкету» button (payload `survey:start`).

## Preconditions
- Customer record exists in DB (scenario 01 complete)
- Customer.survey_completed = false
- FSM state = REGISTERED

## Draft model

All answers accumulated in MemoryContext (`draft.*` keys) during survey. At each FSM state transition, full context (FSM state + all `draft.*` keys) written to `customer.survey_draft` (JSONB) in DB — survives bot restart. Final profile data written to Customer fields in single transaction at step 10. `survey_draft` cleared (set null) on completion or cancellation. Children exist only in draft until step 10 → save.

## Main flow

Progress shown in each message: «Шаг N из 4» for customer steps; «Ребёнок N · шаг M из 3» for child steps.

Bot records message ID of each question in `step_mids` (MemoryContext) as steps progress; all deleted on completion or cancellation.

| Step | State | Bot sends | User action |
|------|-------|----------|-------------|
| 1 | REGISTERED | Delete survey offer message. Set AWAITING_NAME. «Шаг 1 из 4 · Как вас зовут? Введите имя или имя и отчество:» + [Отмена] | Types name or clicks Отмена |
| 2 | AWAITING_NAME | Store `draft.first_name`. Set AWAITING_LAST_NAME. «Шаг 2 из 4 · Расскажите свою фамилию — поможет при официальном обращении. Можно пропустить 😊» + [Пропустить] [← Назад] | Types or skips |
| 3 | AWAITING_LAST_NAME | Store `draft.last_name` (null if skipped). Set AWAITING_CUSTOMER_BIRTHDATE. «Шаг 3 из 4 · Когда ваш день рождения? Обязательно поздравим! 🎂 (ДД.ММ.ГГГГ)» + [Пропустить] [← Назад] | Types or skips |
| 4 | AWAITING_CUSTOMER_BIRTHDATE | Store `draft.birthdate` (null if skipped). Set AWAITING_CHILD_NAME. «Шаг 4 из 4 · Как зовут вашего ребёнка?» + (if 0 children in draft: [Купить для себя]) + [← Назад] | Types name or clicks Купить для себя |
| 5 | AWAITING_CHILD_NAME | Append child draft entry `{name}`. Set AWAITING_CHILD_GENDER. «Ребёнок N · шаг 1 из 3 · Ваш ребёнок — мальчик или девочка? Подберём подходящие предложения:» + [Мальчик] [Девочка] [← Назад] | Clicks button |
| 6 | AWAITING_CHILD_GENDER | Store `gender` into current child draft. Set AWAITING_CHILD_BIRTHDATE. «Ребёнок N · шаг 2 из 3 · Когда день рождения у ребёнка? Будем поздравлять! 🎉 (ДД.ММ.ГГГГ)» + [Пропустить] [← Назад] | Types or skips |
| 7 | AWAITING_CHILD_BIRTHDATE | Store `birthdate` into current child draft (null if skipped). Set AWAITING_MORE_CHILDREN. «Ребёнок N · шаг 3 из 3 · Хотите добавить ещё одного ребёнка?» + [Да] [Нет] | Clicks button |
| 8 | AWAITING_MORE_CHILDREN | **Да** → new child draft entry, set AWAITING_CHILD_NAME, go to step 5. **Нет** → set AWAITING_CONFIRMATION, send confirmation card (see section below). | Clicks button on confirmation card |
| 9 | AWAITING_CONFIRMATION | User reviews draft. May edit fields inline (see section below). On [✅ Сохранить] → set AWAITING_CONTACT, send contact prompt. | Clicks Сохранить or edits |
| 10 | AWAITING_CONTACT | **Path A — contact shared:** bot receives contact event from Max API → extract phone → store `draft.phone` → write all draft data to Customer fields in single transaction (including phone). **Path B — [Завершить]:** write all draft data to DB (phone = null). Both paths: set `survey_completed = True`; clear `customer.survey_draft`; set REGISTERED; send «Анкета заполнена! Спасибо 🎉» + `registered_keyboard`; delete all FSM question messages (`step_mids`); if False → True trigger scenario 15 (Add Coupon). | Clicks [📞 Запрос контактов] and shares phone, or clicks [Завершить] |

## Confirmation card (step 8 → AWAITING_CONFIRMATION)

Bot sends one message with draft summary:

```
📋 Проверьте данные перед сохранением:

👤 [Имя] [Фамилия]
🎂 [дата] / не указана

👧 Дети:
  1. [Имя] · [Пол] · [д.р. / не указана]
  2. …
```

Inline keyboard:
```
[✏️ Имя]            [✏️ Фамилия]
[✏️ Дата рождения]  [👶 Дети]
[✅ Сохранить]
```

If 0 children in draft: no «Дети» section and no [👶 Дети] button.

### Inline editing from confirmation card

Pressing any [✏️ X] button while in AWAITING_CONFIRMATION:
- State stays AWAITING_CONFIRMATION (bot tracks `draft.editing_field` in session)
- Bot sends single re-ask message for that field (same wording as original step, without step counter)
- User answers → draft updated → bot edits confirmation card message in place → clears `draft.editing_field`

Pressing [👶 Дети]:
- Bot sends children draft list (see Children management section below)
- State stays AWAITING_CONFIRMATION; sub-navigation tracked via session
- After any change: bot re-sends updated confirmation card

### Children management within AWAITING_CONFIRMATION

Children list message:
```
👶 Дети в анкете:
  1. Маша · Девочка · 12.06.2018
  2. Артём · Мальчик · —

[✏️ Маша]  [✏️ Артём]
[➕ Добавить ребёнка]
[← Назад к сводке]
```

[✏️ Child] → child draft card:
```
👧 Маша · Девочка · 12.06.2018

[✏️ Имя]   [✏️ Пол]   [✏️ Дата р.]
[🗑 Удалить из анкеты]
[← Назад к списку]
```

Editing child field: bot asks one question → draft updated → re-show child card.
[🗑 Удалить] → confirm prompt → remove from `draft.children` → re-show children list.
[➕ Добавить ребёнка] → 3-step child sub-form (same as steps 5–7) → add to `draft.children` → re-show children list.
[← Назад к сводке] → re-show confirmation card.

## Contact prompt (step 9 → AWAITING_CONTACT)

«Последний шаг — поделитесь контактом как запасным каналом связи. Если что-то случится с ботом, мы не потеряем вас! Это необязательно.»

Buttons:
- [📞 Запрос контактов] — Max API contact-request button (type `request_contact`); triggers native contact sharing dialog in Max messenger
- [Завершить заполнение анкеты] — regular button; completes without phone
- [← Назад]

On contact received (Max API contact event):
1. Extract `phone` from contact payload
2. Store as `draft.phone`
3. Proceed to DB write + completion (same as Path A in step 10)

[← Назад] from contact prompt → re-show confirmation card (back to AWAITING_CONFIRMATION).

## Back navigation

Child draft data is NOT deleted on back — stays in `draft.children`. Children can only be deleted via explicit [🗑] action on confirmation card.

| Current state | Back navigates to |
|--------------|------------------|
| AWAITING_NAME | **[Отмена]** — delete all FSM question messages (`step_mids`), discard draft, clear `customer.survey_draft`, set REGISTERED; send `registered_keyboard`. No confirmation prompt. |
| AWAITING_LAST_NAME | AWAITING_NAME — re-ask name |
| AWAITING_CUSTOMER_BIRTHDATE | AWAITING_LAST_NAME — re-ask last name |
| AWAITING_CHILD_NAME (child index=1) | AWAITING_CUSTOMER_BIRTHDATE |
| AWAITING_CHILD_NAME (child index=N, N>1) | AWAITING_MORE_CHILDREN — re-ask «Хотите добавить ещё?» (not child N−1 data) |
| AWAITING_CHILD_GENDER | AWAITING_CHILD_NAME — re-ask child name |
| AWAITING_CHILD_BIRTHDATE | AWAITING_CHILD_GENDER — re-ask child gender |
| AWAITING_MORE_CHILDREN | AWAITING_CHILD_BIRTHDATE — re-ask child DOB |
| AWAITING_CONFIRMATION | AWAITING_MORE_CHILDREN (if children in draft) / AWAITING_CUSTOMER_BIRTHDATE (if no children) |
| AWAITING_CONTACT | AWAITING_CONFIRMATION — re-show confirmation card |

**Pre-fill hint on back:** when re-asking a step that already has a draft value, bot adds inline button:
`[Оставить «[current value]»]` — pressing it keeps the draft value and advances to next step.

## Alternative flows

### A1: Invalid date input
- Bot: «Не понял дату. Введите в формате ДД.ММ.ГГГГ (разделитель любой):»
- State unchanged, user retries

### A2: Resume interrupted survey
- Trigger: user clicks «Заполнить анкету» (payload `survey:start`) OR «Продолжить заполнение анкеты» (payload `survey:resume`) when `customer.survey_draft IS NOT NULL` and `survey_completed = false`
- Bot restores draft from `customer.survey_draft` into MemoryContext
- Bot sends:
  ```
  👋 Вы уже начали заполнять анкету!

  ✅ Имя: Анна
  ✅ Фамилия: Смирнова
  ⏳ Осталось: дата рождения, данные детей

  [▶️ Продолжить]  [🔄 Начать заново]
  ```
- [▶️ Продолжить] → set FSM to state stored in `survey_draft`, resume from that step
- [🔄 Начать заново] → clear draft, clear `customer.survey_draft`, set AWAITING_NAME, go to step 1

### A3: «Купить для себя» (step 4, 0 children in draft)
- Append `draft.bought_for_self = true`
- Skip steps 5–8; set AWAITING_CONFIRMATION
- Confirmation card shows no children section
- survey_completed will be True regardless of children

### A4: DB write fails at step 10
- Bot: «Ошибка при сохранении. Попробуйте ещё раз.»
- State stays AWAITING_CONTACT; draft preserved; retry possible

## MemoryContext keys during survey

| Key | Content |
|-----|---------|
| `max_user_id` | Customer identifier |
| `survey_offer_mid` | Message ID of survey offer (deleted at step 1) |
| `draft.first_name` | Q1 answer |
| `draft.last_name` | Q2 answer (null if skipped) |
| `draft.birthdate` | Q3 answer (null if skipped) |
| `draft.bought_for_self` | True if «Купить для себя» taken |
| `draft.children` | List of `{name, gender, birthdate}` dicts |
| `draft.current_child_index` | 1-based index of child being filled |
| `draft.editing_field` | Field being edited from confirmation card (cleared after update) |
| `draft.phone` | Phone from contact event (null if user skipped via Завершить) |
| `step_mids` | List of message IDs of FSM question messages; deleted on completion or cancellation |

## Postconditions
- Single DB transaction at step 10:
  - Customer.first_name, last_name, birthdate, phone updated
  - Customer.survey_completed set (see rule below)
  - 0..N Child records created, linked to Customer
- survey_completed = True upon successful completion of step 10 (Path A or Path B), regardless of children or birthdate
- Scenario 15 (Add Coupon) triggered if survey_completed changes False → True; coupon parameters and customer notification defined there
- FSM state = REGISTERED

## NFR refs
- pii.md: child birthdate, name, phone handling

## Open questions
- [x] Draft persistence across bot restarts: resolved — full context persisted to `customer.survey_draft` (JSONB) at each step; restored to MemoryContext on resume.
- [ ] Confirmation card editing: Max messenger API supports `editMessageText`? If not, bot must send new card message on each edit.
- [x] Re-running survey after survey_completed = True: resolved — redirect to scenario 05 (profile editing).
