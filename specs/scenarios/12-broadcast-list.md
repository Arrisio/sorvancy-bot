# Scenario: Show Scheduled Broadcasts

## Goal
Superuser views pending broadcasts and can cancel individual ones.

## Actors
- Superuser (Staff with `is_owner = true`)
- Bot

## Trigger
Superuser clicks «Запланированные рассылки» button.

## Preconditions
- Acting user has `is_owner = true` in Staff table

## Main flow

1. Superuser clicks «Запланированные рассылки»
2. Bot retrieves pending broadcasts
3. Bot sends one message per broadcast; each message contains broadcast details + inline button [Отменить]
4. Superuser clicks [Отменить] on a broadcast
5. Bot sets Broadcast status → `cancelled`; bot sends: «Рассылка отмечена как "Отменена"»; bot sends `superuser_keyboard`

## Negative scenarios

### N1: No pending broadcasts
- Bot response TBD

## Postconditions
- Selected Broadcast `status = cancelled`
- Delivery will not start for cancelled broadcast

## Open questions
- [ ] Broadcast message format: which fields shown per entry? (id, recipient_count, scheduled_at — confirm full list)
- [ ] N1: what does bot send if no pending broadcasts exist?
- [ ] Which statuses shown: only `pending`, or also `running`?
- [ ] Running broadcast cancel: does cancellation mid-delivery stop remaining sends?
