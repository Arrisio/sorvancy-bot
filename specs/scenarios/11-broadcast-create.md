# Scenario: Create and Schedule Broadcast

## Goal
Superuser creates mass message delivery to selected customers and sets start time within allowed broadcast window.

## Actors
- Superuser (Staff with `is_owner = true`)
- Bot

## Trigger
Superuser clicks «Запустить рассылку» button.

## Preconditions
- Acting user has `is_owner = true` in Staff table

## Main flow

Bot records message ID of each prompt in `step_mids` (MemoryContext); all deleted on confirmation (step 10) or any [Отмена] branch.

1. Superuser clicks «Запустить рассылку»
2. Bot sends: «Пришлите сообщение для рассылки» + button [Отмена]
3. Superuser sends message with broadcast content — any message type is accepted: text, photo, file, video, audio, sticker, or any other supported attachment; the original message is saved by reference
4. Bot saves reference to original message (will be forwarded to each recipient via Forward — not re-sent as new message; attachments preserved automatically); sends: «Добавить купон к рассылке?» + buttons [Добавить] [Пропустить]
   - Superuser clicks [Добавить] → Bot runs sub-scenario 21 (Coupon Input); stores `coupon_draft = {value, validity_days, min_purchase_amount, display_name}` in broadcast context; proceeds to step 5.
   - Superuser clicks [Пропустить] → proceeds to step 5 with no coupon attached.
5. Bot sends: «Пришлите номера клиентов для рассылки» + button [Отмена]
6. Superuser sends recipient list as text — Customer IDs separated by any delimiter (whitespace, comma, semicolon); split on any non-digit character
7. Bot resolves recipient list: deduplicates customer IDs in-memory (owner may submit same ID twice); excludes customers with `opt_out_marketing = true`
8. Bot sends: «Создана рассылка на {количество} получателей. Когда её начать? Окно рассылки: {BROADCAST_WINDOW_START_HOUR}:00–{BROADCAST_WINDOW_END_HOUR}:00.» + buttons [Начать в ближайшее время] [Завтра] [Отмена]
9. Superuser responds with start time choice:
   - Clicks [Начать в ближайшее время] → `scheduled_at` = nearest available window slot (see nfr/broadcast-delivery.md §Broadcast window); Broadcast status → `pending`
   - Clicks [Завтра] → `scheduled_at` = tomorrow at `BROADCAST_WINDOW_START_HOUR:00`; Broadcast status → `pending`
   - Sends date only (e.g. «25.06») → `scheduled_at = that date at BROADCAST_WINDOW_START_HOUR:00`; if date already passed in current year → advance to next year; Broadcast status → `pending`
   - Sends date + time (e.g. «25.06 14:30») → applies same year auto-advance rule; validates time falls within broadcast window; if valid: `scheduled_at = that datetime`, Broadcast status → `pending`; if invalid: → N1
   - Clicks [Отмена] → scenario ends; no Broadcast record created; bot deletes `step_mids`; bot sends `superuser_keyboard`
10. Bot sends: «Добавьте комментарий к рассылке (виден только вам) или пропустите:» + buttons [Пропустить] [Отмена]
    - Superuser types text → `broadcast.comment = typed_text`; proceeds to step 11.
    - Superuser clicks [Пропустить] → `broadcast.comment = null`; proceeds to step 11.
    - Superuser clicks [Отмена] → scenario ends; no Broadcast record created; bot deletes `step_mids`; bot sends `superuser_keyboard`.
11. Bot confirms: «Рассылка #{id} запланирована на {DD.MM.YYYY HH:MM}. Получателей: {count}.»; bot deletes FSM prompt messages (`step_mids`); bot sends `superuser_keyboard`

## Alternative flows

### A1: Superuser clicks [Отмена] at step 2
- Scenario ends; no Broadcast record created; bot deletes `step_mids`; bot sends `superuser_keyboard`.

### A2: Sub-scenario 21 signals cancellation (at step 4)
- Scenario ends; no Broadcast record created; bot deletes `step_mids`; bot sends `superuser_keyboard`.

### A3: Superuser clicks [Отмена] at step 5
- Scenario ends; no Broadcast record created; bot deletes `step_mids`; bot sends `superuser_keyboard`.

## Negative scenarios

### N1: Scheduled time outside broadcast window
- Superuser sends date+time (step 9) where time falls outside `[BROADCAST_WINDOW_START_HOUR:00, BROADCAST_WINDOW_END_HOUR:00)` interval
- Bot sends: «Время {HH:MM} недоступно. Укажите с {BROADCAST_WINDOW_START_HOUR}:00 до {BROADCAST_WINDOW_END_HOUR}:00:»
- Superuser can retry — re-enter date+time, click [Начать в ближайшее время], [Завтра], or [Отмена]

## Postconditions
- Broadcast record created in DB with recipient list size, scheduled start time, status `pending`, coupon template (if provided), and comment (if provided)
- Confirmation message sent to superuser includes exact scheduled datetime (`DD.MM.YYYY HH:MM`)
- Scheduler picks up broadcast when `scheduled_at ≤ now()` and triggers delivery; see nfr/broadcast-delivery.md
- Pending broadcasts can be cancelled via scenario 12

## NFR refs
- broadcast-delivery.md

## Open questions
- [x] Date parsing timezone: Asia/Yekaterinburg — confirmed intentional.
- [x] Confirmation message (step 11): mentions coupon when attached: «+ купон на {value} ₽». RESOLVED.
- ~~comment: optional (nullable), no length limit. RESOLVED.~~
