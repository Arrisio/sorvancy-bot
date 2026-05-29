# Entity: Coupon

## Purpose
Single-use discount coupon issued to a customer as a benefit; lets customer pay part of a purchase with coupon value, subject to minimum purchase amount and expiry date.

## Fields

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | bigint | PK, auto | Internal ID |
| customer_id | bigint | not null, FK → customers(id) | Coupon owner |
| type | text | not null | Issuance reason: `anket` \| `seller` \| `birthday` \| `broadcast` |
| display_name | text | not null, max 40 chars | Label shown on coupon buttons and in coupon lists. Set at issuance; not editable after creation. |
| value | integer | not null | Whole rubles deductible from purchase |
| min_purchase_amount | integer | not null, default 0 | Minimum purchase total (₽) required to apply coupon; 0 = no minimum |
| valid_until | timestamptz | not null | Coupon expires at this moment |
| used_at | timestamptz | nullable | Set when coupon is applied; null while unused |
| status | text | not null, default `active` | `active` \| `used` \| `expired` \| `revoked` |

## Invariants

- `status = used` ↔ `used_at IS NOT NULL`
- `status = active` → `used_at IS NULL` AND `valid_until > now()`
- Coupon applied to purchase: amount deducted ≤ `value` AND `purchase_total ≥ min_purchase_amount`
- Expired coupon (`valid_until ≤ now()`) must not be accepted even if status not yet flipped
- `value > 0`, `min_purchase_amount ≥ 0`
- `display_name` length 1–40 chars; set at creation; immutable thereafter
- Scheduled job flips `status → expired` where `valid_until ≤ now()` AND `status = active`
- Customer may hold multiple active coupons simultaneously
- Multiple coupons may be applied to one purchase (stacking allowed)
- Coupon issued automatically when Customer.survey_completed transitions False → True (`type = anket`)
- Coupon issued manually by seller (`type = seller`)
- Coupon issued to each successfully reached recipient of a coupon broadcast (`type = broadcast`); `valid_until = delivery_time + validity_days`

## Display name defaults

Auto-generated defaults per type (date format `ДД.ММ.ГГ`, 2-digit year for button compactness):

| Type | Default display_name | Rationale |
|------|---------------------|-----------|
| `anket` | `Бонус {value} ₽ до {ДД.ММ.ГГ}` | "Бонус" signals reward, reinforces behavior loop; customer recalls why they have it → higher redemption |
| `birthday` | `ДР: {value} ₽ до {ДД.ММ.ГГ}` | "ДР:" instantly identifies birthday origin; separates from other coupons in list |
| `seller` | `{value} ₽ до {ДД.ММ.ГГ}` | Generic transactional; operator may override (scenario 21, last step) |
| `broadcast` | `{value} ₽ до {ДД.ММ.ГГ}` | Generic promotional; operator may override (scenario 21, last step) |

## Relations

- belongs_to: Customer

## Open questions

- ~~`anket` coupon parameters: value=300, min_purchase_amount=0 (default), valid_until=now()+1 month. RESOLVED.~~
- [ ] Stacking limit: all active coupons apply, or capped at N per purchase?
- [ ] `revoked` status: actor and interface TBD.
