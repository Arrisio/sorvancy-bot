# Entity: Broadcast

## Purpose
Mass message forwarded to a filtered set of customers; may be immediate or scheduled.

## Fields

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | int | PK, auto | Shown in completion notification |
| source_message_id | bigint | not null | Max messenger message ID of original message; forwarded to each recipient |
| created_by | bigint | not null, FK → staff(id) | Superuser who created the broadcast |
| status | enum | not null | `pending` \| `running` \| `completed` \| `cancelled` |
| scheduled_at | timestamptz | not null | Delivery start time; `now()` for immediate |
| created_at | timestamptz | not null, default now() | |
| recipient_count | int | not null | Recipient list size at creation time; excludes opt-out customers |
| sent_count | int | not null, default 0 | Derived: COUNT(BroadcastRecipient WHERE status=sent) |
| failed_count | int | not null, default 0 | Derived: COUNT(BroadcastRecipient WHERE status=failed) |

## Invariants

- `recipient_count` computed at creation time; excludes customers with `opt_out_marketing = true`
- Status transitions: `pending` → `running` → `completed` | `cancelled`
- `cancelled` set by superuser via scenario 12 or [Отмена] at scheduling step in scenario 11
- `sent_count + failed_count ≤ recipient_count`

## Relations

- belongs_to: Staff (created_by)
- has_many: BroadcastRecipient

## Open questions

- [ ] `source_message_id`: also need to store originating `chat_id` for forward API call?
- [ ] Transient retry attempts: counted in `failed_count` only after permanent failure, not per retry?
