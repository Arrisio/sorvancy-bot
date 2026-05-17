# Entity: Broadcast

## Purpose
Mass message forwarded to a filtered set of customers; may be immediate or scheduled; optionally issues a coupon to each recipient on delivery.

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
| coupon_value | int | nullable | Coupon template: whole rubles; null means no coupon attached |
| coupon_validity_days | int | nullable | Coupon template: days from delivery time until expiry |
| coupon_max_payment_pct | int | nullable | Coupon template: max % of purchase coverable by coupon (1–100) |

## Invariants

- `recipient_count` computed at creation time; excludes customers with `opt_out_marketing = true`
- Status transitions: `pending` → `running` → `completed` | `cancelled`
- `cancelled` set by superuser via scenario 12 or [Отмена] at scheduling step in scenario 11
- `sent_count + failed_count ≤ recipient_count`
- Coupon template fields are all-or-nothing: either all three (`coupon_value`, `coupon_validity_days`, `coupon_max_payment_pct`) are set, or all are null

## Relations

- belongs_to: Staff (created_by)
- has_many: BroadcastRecipient

## Open questions

- [ ] `source_message_id`: also need to store originating `chat_id` for forward API call?
- [ ] Transient retry attempts: counted in `failed_count` only after permanent failure, not per retry?
