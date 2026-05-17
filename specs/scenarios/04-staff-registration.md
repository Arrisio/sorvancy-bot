# Scenario: Staff Registration via Contact Card

## Goal
Superuser registers new seller in bot by forwarding their Max contact card.

## Actors
- Seller (prospective)
- Superuser (Staff with `is_owner = true`)
- Bot

## Trigger
Superuser forwards message containing contact card to bot.

## Preconditions
- Forwarding user has `is_owner = true` in Staff table
- Contact card message contains `max_user_id` and at least some of: `phone`, `first_name`, `last_name`, `username`

## Main flow

1. Superuser forwards contact card to bot
2. Bot extracts `max_user_id`, `phone`, `first_name`, `last_name`, `username` from card/message attributes
3. Bot asks superuser: «Добавить [first_name last_name] как нового продавца?»
4. Superuser confirms
5. Bot creates Staff record with extracted fields, `is_owner = false`
6. Bot notifies superuser: «Продавец [first_name last_name] успешно добавлен.»

## Alternative flows

### A1: Seller already registered
- After step 2: Staff row with that `max_user_id` already exists → bot notifies superuser, scenario ends without creating duplicate

## Negative scenarios

### N1: Superuser declines at step 4
- Bot: «Регистрация отменена.» Scenario ends.

## Postconditions
- New Staff row exists with `is_owner = false` and fields populated from contact card
- Superuser received success notification

## NFR refs
- pii.md

## Open questions
- [ ] Confirmation UI: free-text reply or inline buttons (Да/Нет)?
- [ ] Which contact card fields are required for registration to proceed? If `first_name` or `max_user_id` missing — fail or proceed with nulls?
- [ ] Does bot notify new seller after successful registration? Previous spec version included seller notification — intentionally removed?
