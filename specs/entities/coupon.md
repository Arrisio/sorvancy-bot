# Entity: Coupon

## Purpose
Single-use discount coupon issued to a customer as a benefit; lets customer pay part of a purchase with coupon value, subject to a per-coupon cap and expiry date.

## Fields

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | bigint | PK, auto | Internal ID |
| customer_id | bigint | not null, FK → customers(id) | Coupon owner |
| type | text | not null | Issuance reason, e.g. `survey_completed` |
| value | integer | not null | Whole rubles deductible from purchase |
| max_payment_pct | integer | not null | Max % of purchase total that coupon may cover (1–100) |
| valid_until | timestamptz | not null | Coupon expires at this moment |
| used_at | timestamptz | nullable | Set when coupon is applied; null while unused |
| status | text | not null, default `active` | `active` \| `used` \| `expired` \| `revoked` |

## Invariants

- `status = used` ↔ `used_at IS NOT NULL`
- `status = active` → `used_at IS NULL` AND `valid_until > now()`
- Coupon applied to purchase: amount deducted ≤ `value` AND amount deducted ≤ `purchase_total * max_payment_pct / 100`
- Expired coupon (`valid_until ≤ now()`) must not be accepted even if status not yet flipped
- `value > 0`, `max_payment_pct` in [1, 100]
- Scheduled job flips `status → expired` where `valid_until ≤ now()` AND `status = active`
- Customer may hold multiple active coupons simultaneously
- Multiple coupons may be applied to one purchase (stacking allowed)
- Coupon issued automatically when Customer.survey_completed transitions False → True (`type = anket`)
- Coupon issued manually by seller (`type = seller`)
- Coupon issued to each successfully reached recipient of a coupon broadcast (`type = broadcast`); `valid_until = delivery_time + validity_days`

## Relations

- belongs_to: Customer

## Open questions

- ~~`anket` coupon parameters: value=300, max_payment_pct=30, valid_until=now()+1 month. RESOLVED.~~
- [ ] Stacking limit: all active coupons apply, or capped at N per purchase?
- [ ] `revoked` status: actor and interface TBD.
