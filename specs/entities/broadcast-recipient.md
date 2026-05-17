# Entity: BroadcastRecipient

## Purpose
Per-recipient delivery record for a Broadcast; prevents duplicate sends on bot restart and tracks individual delivery outcome.

## Fields

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | int | PK, auto | |
| broadcast_id | int | not null, FK → broadcast(id) | |
| customer_id | int | not null, FK → customer(id) | |
| status | enum | not null, default `pending` | `pending` \| `sent` \| `failed` |
| sent_at | timestamptz | nullable | Set on successful forward |
| error | text | nullable | Error description on permanent failure |

## Invariants

- Unique constraint on (broadcast_id, customer_id) — one row per recipient per broadcast
- Delivery worker skips row if `status = sent` — idempotent on bot restart
- `status = sent` ↔ `sent_at IS NOT NULL`
- `status = failed` → permanent error (bot blocked, account deleted); no further retry
- Broadcast.sent_count = COUNT(*) WHERE status = sent for that broadcast
- Broadcast.failed_count = COUNT(*) WHERE status = failed for that broadcast

## Relations

- belongs_to: Broadcast
- belongs_to: Customer

## Open questions

- [ ] `error` field: store raw API error code, human-readable string, or both?
