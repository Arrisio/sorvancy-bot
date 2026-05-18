# Scenario: Staff List Management

## Goal
Superuser views all registered staff, assigns or revokes owner flag for any staff member, or deletes a staff member.

## Actors
- Superuser (Staff with `is_owner = true`)
- Bot

## Trigger
Superuser clicks «Показать продавцов» button.

## Preconditions
- Acting user has `is_owner = true` in Staff table

## Main flow

1. Superuser clicks «Показать продавцов»
2. Bot sends one message per Staff row that is NOT the acting superuser; each message contains:
   - `first_name last_name`, `phone`
   - Status label: «Владелец» if `is_owner = true`; «Продавец» if `is_owner = false`
   - Inline buttons:
     - «Удалить» always present
     - «Назначить владельцем» if `is_owner = false`
     - «Снять флаг владельца» if `is_owner = true` AND `max_user_id ≠ config.OWNER_ID`
     - No owner-toggle button if `is_owner = true` AND `max_user_id = config.OWNER_ID`
3. Superuser takes one of the available actions → see A1, A2, A3

## Alternative flows

### A1: Delete staff member
1. Superuser clicks «Удалить» on a staff card
2. Bot sends confirmation: «Удалить [name]? Это действие нельзя отменить.» with [Удалить] / [Отмена]
3. Superuser confirms
4. Bot deletes Staff row; sends success message; sends `superuser_keyboard`

### A2: Assign owner flag
1. Superuser clicks «Назначить владельцем» on a staff card with `is_owner = false`
2. Bot sends confirmation: «Назначить [name] владельцем?» with [Назначить] / [Отмена]
3. Superuser confirms
4. Bot sets `is_owner = true` for target Staff row; sends «[name] назначен владельцем.»; sends `superuser_keyboard`

### A3: Revoke owner flag
1. Superuser clicks «Снять флаг владельца» on a staff card with `is_owner = true` and `max_user_id ≠ config.OWNER_ID`
2. Bot sends confirmation: «Снять права владельца у [name]?» with [Снять] / [Отмена]
3. Superuser confirms
4. Bot sets `is_owner = false` for target Staff row; sends «Права владельца сняты у [name].»; sends `superuser_keyboard`

## Negative scenarios

### N1: Superuser cancels at A1 step 2
- No DB write; scenario ends.

### N2: Superuser cancels at A2 step 2
- No DB write; scenario ends.

### N3: Superuser cancels at A3 step 2
- No DB write; scenario ends.

### N4: Server-side guard — revoke on OWNER_ID-protected staff
- Condition: `seller:revoke_owner:<id>` callback received where target `max_user_id = config.OWNER_ID`
- Button is absent from UI in normal flow (step 2 main flow); this guard handles crafted callbacks
- Bot responds: «Нельзя снять флаг владельца у основного владельца.»; no DB write.

## Postconditions

- A1: Target Staff row removed from DB
- A2: Target Staff row has `is_owner = true`
- A3: Target Staff row has `is_owner = false`

## NFR refs
- pii.md

## Open questions
- [ ] Empty list: what does bot send if no other Staff registered (acting superuser is alone)?
- [ ] Final wording for confirmation prompts in A1/A2/A3 — TBD?
- [ ] Should deletion also be blocked for OWNER_ID-seeded staff row?
- [ ] Does bot notify affected staff member when owner flag is assigned or revoked?
- [ ] List filter: current `get_all_sellers()` returns only `is_owner = false` rows — must be changed to return all Staff except acting user to support A3.
