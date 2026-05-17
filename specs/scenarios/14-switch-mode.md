# Scenario: Switch Customer Mode

## Goal
Superuser toggles their own `customer_mode` flag to test customer-facing bot flows.

## Actors
- Superuser (Staff with `is_owner = true`)
- Bot

## Trigger
Superuser sends `/mode` command.

## Preconditions
- Acting user has `is_owner = true` in Staff table
- Command processed before middleware routing — `/mode` is intercepted regardless of current `customer_mode` value

## Main flow

1. Superuser sends `/mode`
2. Bot toggles `Staff.customer_mode`: `false → true` or `true → false`
3. Bot saves updated flag to DB
4. Bot responds with current state:
   - If `customer_mode` now `true`: «Режим клиента включён. Ваши сообщения обрабатываются как от покупателя.»
   - If `customer_mode` now `false`: «Режим суперпользователя восстановлен.»

## Postconditions
- `Staff.customer_mode` updated in DB
- Subsequent messages from superuser routed per new mode (see nfr/middleware-routing.md)
- On toggle to `false` (superuser mode restored): FSM state reset to REGISTERED; no state restoration

## Invariants
- `/mode` toggles only the sending superuser's own flag; cannot target other Staff members

## Open questions
- (none)
