# Scenario: Create and Schedule Broadcast

## Goal
Superuser creates mass message delivery to selected customers and sets start time.

## Actors
- Superuser (Staff with `is_owner = true`)
- Bot

## Trigger
Superuser clicks «Запустить рассылку» button.

## Preconditions
- Acting user has `is_owner = true` in Staff table

## Main flow

1. Superuser clicks «Запустить рассылку»
2. Bot sends: «Пришлите сообщение для рассылки»
3. Superuser sends message with broadcast content — any message type is accepted: text, photo, file, video, audio, sticker, or any other supported attachment; the original message is saved by reference
4. Bot saves reference to original message (will be forwarded to each recipient via Forward — not re-sent as new message; attachments preserved automatically); sends: «Пришлите номера клиентов для рассылки» + inline button [Отмена]
5. Superuser sends recipient list — either:
   - Text message containing Customer IDs
   - Excel or CSV file (same format as Excel export scenario; rows hidden by filter treated as excluded)
6. Bot resolves recipient list: deduplicates customer IDs in-memory (owner may submit same ID twice); excludes customers with `opt_out_marketing = true`
7. Bot sends: «Создана рассылка на {количество} получателей. Когда её начать?» + buttons [Начать сейчас] [Отмена]
8. Superuser responds with start time choice:
   - Clicks [Начать сейчас] → `scheduled_at = now()`; Broadcast status → `running`; delivery begins immediately
   - Sends date only (e.g. «25.06») → `scheduled_at = that date at 11:00`; Broadcast status → `pending`
   - Sends date + time (e.g. «25.06 14:30») → `scheduled_at = that datetime`; Broadcast status → `pending`
   - Clicks [Отмена] → scenario ends; no Broadcast record created

## Alternative flows

### A1: Superuser clicks [Отмена] at step 4
- Scenario ends; no Broadcast record created.

## Postconditions
- Broadcast record created in DB with recipient list size, scheduled start time, status
- If immediate: delivery begins; see nfr/broadcast-delivery.md for delivery mechanics
- On delivery completion: bot sends superuser: «Рассылка {id} завершена. Отправлено успешно: {sent_count}. Не удалось доставить: {failed_count}.»

## NFR refs
- broadcast-delivery.md

## Open questions
- [ ] Excel/CSV recipient parsing: which column contains Customer ID? Must match Excel export scenario column name.
- [ ] Excel filtered rows: bot reads only visible (non-hidden) rows — confirm that this is expected behavior.
- [ ] Text message with IDs: exact delimiter format? (space-separated, one per line, comma-separated?)
- [ ] Date parsing timezone: which timezone applies to `scheduled_at` when user sends date without offset?
- [ ] Can a `running` broadcast be cancelled via scenario 12, or only `pending` ones?
