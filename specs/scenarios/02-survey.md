# Scenario: Survey (Phase 2 — Profile Enrichment)

## Goal
Registered user optionally enriches profile with name, birthdate, and children data. Unlocks fuller discount card.

## Actors
- User (registered, FSM state = REGISTERED)
- Bot
- Database

## Trigger
User clicks "Заполнить анкету" on survey offer message (payload `survey:start`)

## Preconditions
- Customer exists in DB (phase 1 complete)
- FSM state = REGISTERED (or user already registered, detected by DB lookup)

## Main flow

| Step | State | Bot action | User action |
|------|-------|-----------|-------------|
| 1 | REGISTERED | Delete survey offer message. Set state = AWAITING_FIRST_NAME. Send "Как вас зовут?" + [← Назад] | Types name |
| 2 | AWAITING_FIRST_NAME | Store `first_name`. Set state = AWAITING_CUSTOMER_BIRTHDATE. Send "Ваша дата рождения? (ДД.ММ.ГГГГ)" | Types date |
| 3 | AWAITING_CUSTOMER_BIRTHDATE | Parse date (any non-digit separator). Store `customer_birthdate` as ISO string. Set state = AWAITING_CHILD_NAME. Send child prompt | Types child name |
| 4 | AWAITING_CHILD_NAME | Store `current_child_name`. Set state = AWAITING_CHILD_GENDER. Send gender keyboard | Clicks Мальчик/Девочка |
| 5 | AWAITING_CHILD_GENDER | Store `current_child_gender`. Set state = AWAITING_CHILD_BIRTHDATE. Send child DOB prompt | Types child date |
| 6 | AWAITING_CHILD_BIRTHDATE | Parse date. Store `current_child_birthdate`. Set state = AWAITING_MORE_CHILDREN. Send "Добавить ещё?" | Clicks Да/Нет |
| 7 | AWAITING_MORE_CHILDREN | Commit child to `children` list. If Да → step 4. If Нет → complete | |
| 8 | — | `update_survey_data` + `child_model.create` × N in single transaction. Set state = REGISTERED. Send confirmation | |

## Back navigation (payload `back`)

| Current state | Navigates to | Bot message |
|--------------|-------------|-------------|
| AWAITING_FIRST_NAME | REGISTERED | "Анкета отменена." + `registered_keyboard` |
| AWAITING_CUSTOMER_BIRTHDATE | AWAITING_FIRST_NAME | Re-ask name |
| AWAITING_CHILD_NAME (0 children committed) | AWAITING_CUSTOMER_BIRTHDATE | Re-ask customer DOB |
| AWAITING_CHILD_NAME (≥1 child committed) | AWAITING_MORE_CHILDREN | Re-ask "Добавить ещё?" |
| AWAITING_CHILD_GENDER | AWAITING_CHILD_NAME | Re-ask child name |
| AWAITING_CHILD_BIRTHDATE | AWAITING_CHILD_GENDER | Re-ask gender |
| AWAITING_MORE_CHILDREN | AWAITING_CHILD_BIRTHDATE | Re-ask child DOB |

## Alternative flows

### A1: Invalid date input (steps 2 or 6)
- Bot: "Не понял дату. Введите в формате ДД.ММ.ГГГГ (разделитель любой):"
- State unchanged, user retries

### A2: User clicks "Пропустить" (payload `survey:skip`)
- Survey offer message deleted
- State stays REGISTERED, no data collected, no DB changes

### A3: DB write fails at step 8
- Transaction rolled back (no partial data)
- User sees: "Ошибка при сохранении. Попробуйте /start снова." + `registered_keyboard`
- FSM not cleared

## MemoryContext keys during survey

| Key | Set when |
|-----|----------|
| max_user_id | Phase 1 |
| max_username | Phase 1 |
| children | `[]` at phase 1; appended per child |
| survey_offer_mid | After phase 1 (for deletion) |
| first_name | Step 2 |
| customer_birthdate | Step 3 (ISO string) |
| current_child_name | Step 4 |
| current_child_gender | Step 5 |
| current_child_birthdate | Step 6 |

## Postconditions
- Customer.first_name and Customer.birthdate updated in DB
- 1..N Child rows created, linked to Customer
- FSM state = REGISTERED
- Bot sends "Анкета заполнена! Спасибо 🎉"

## NFR refs
- pii.md: child birthdate and name handling

## Open questions
- [ ] Completion message says "скидка увеличена" — discount_percent not incremented in code. Fix copy or implement +2%.
- [ ] MemoryContext lost on bot restart mid-survey — user must restart. Acceptable for MVP?
- [ ] No length validation on first_name or child name. Add min/max?
- [ ] No range validation on child birthdate (should be in past, age 0–18). Add?
- [ ] Re-running survey overwrites first_name and birthdate, adds more children (duplicates possible). Desired behavior?
