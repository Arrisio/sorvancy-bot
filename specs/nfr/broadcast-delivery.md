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

### Scheduler
- Delivery triggered by hourly scheduled job polling for Broadcasts where status=`pending` AND `scheduled_at ≤ now()`
- Immediate broadcasts (status=`running` at creation): picked up on next job tick (≤1 hour delay) or triggered inline — developer chooses simpler option
- See scenario 18 for full delivery flow

## Open questions
- [ ] Retry count limit: max retries per recipient before marking as permanently failed?
- [ ] Error classification: which Max API error codes count as permanent vs transient?
