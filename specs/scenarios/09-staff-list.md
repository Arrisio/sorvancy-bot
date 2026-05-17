# Scenario: Staff List Management

## Goal
Superuser views all registered sellers and can delete any of them.

## Actors
- Superuser (Staff with `is_owner = true`)
- Bot

## Trigger
Superuser clicks «Показать список продавцов» button.

## Preconditions
- Acting user has `is_owner = true` in Staff table

## Main flow

1. Superuser clicks «Показать список продавцов»
2. Bot sends one message per seller; each message contains: seller's `first_name last_name` and `phone`, with inline button «Удалить»
3. Superuser clicks «Удалить» on a seller's message
4. Bot sends confirmation prompt to superuser
5. Superuser confirms deletion
6. Bot deletes Staff record from DB; bot sends success message (wording TBD — see Open questions); bot sends `superuser_keyboard`

## Alternative flows

*(none)*

## Negative scenarios

### N1: Superuser declines deletion at step 5
- No DB write; scenario ends.

## Postconditions
- Target Staff row removed from DB

## NFR refs
- pii.md

## Open questions
- [ ] Empty list: what does bot send if no sellers are registered?
- [ ] Success message after deletion: required? If yes — wording?
- [ ] Deleted seller notification: does bot message the removed seller?
- [ ] Confirmation prompt wording at step 4?
- [ ] Does bot exclude the superuser themselves from the list, or list all Staff with `is_owner = false`?
