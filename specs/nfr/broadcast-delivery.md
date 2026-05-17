# NFR: Broadcast Delivery

## Scope
Delivery phase of scenario 11 (Create and Schedule Broadcast).

## Rules

### Message format
- Each recipient receives a forward of the original message (not reconstructed text copy)

### Throttling
- Delay between consecutive sends configurable via env var `BROADCAST_SEND_DELAY_SECONDS`
- Default: 15 seconds

### Retry
- On transient send error: retry delivery to that recipient
- On permanent error (bot blocked by user, user account deleted): no retry; increment `failed_count`

### Opt-out
- Customers with `opt_out_marketing = true` excluded from recipient list at broadcast creation time; never sent to during delivery

### Completion notification
- After all recipients processed: bot notifies the creating superuser: «Рассылка {id} завершена. Отправлено успешно: {sent_count}. Не удалось доставить: {failed_count}.»

## Open questions
- [ ] Retry count limit: max retries per recipient before marking as permanently failed?
- [ ] Error classification: which Max API error codes count as permanent vs transient?
- [ ] Scheduled broadcasts: what mechanism triggers delivery at `scheduled_at` — cron job, APScheduler, or other?
