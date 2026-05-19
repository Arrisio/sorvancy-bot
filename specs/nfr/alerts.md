# NFR: Error Alerting

## Scope
Unhandled exceptions in the bot process sent as Max messages to a designated support account.

## Rules

### Configuration
- `SUPPORT_ID` — Max account ID of the alert recipient; optional
- If absent: alerting silently disabled, bot runs normally

### Delivery
- Transport: `bot.send_message(user_id=SUPPORT_ID, text=...)` — same Max API used by all bot messages
- Message format: timestamp, optional context string, full traceback (last 3 500 chars)

### Deduplication and rate limiting
- Error signature: MD5 of last 3 traceback frames
- Cooldown: 300 seconds per signature — same error not re-sent within 5 minutes
- Goal: suppress error storms without losing distinct errors

### Failure isolation
- Alert send failure logged at WARNING but never re-raised — alerting must never crash the bot
- Global asyncio exception handler fires for all unhandled coroutine exceptions

### Secrets
- `SUPPORT_ID` stored in `.env`, never logged
