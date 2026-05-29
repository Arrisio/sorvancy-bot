# Entity: FinancialConfig

## Purpose
Singleton configuration row storing owner-editable financial parameters used across coupon issuance and customer registration.

## Fields

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | int | PK, always 1 | Singleton — one row only |
| registration_discount_pct | int | not null, default 10 | Discount % assigned to Customer at registration |
| survey_coupon_value | int | not null, default 300 | Value (₽) of coupon issued on survey completion |
| survey_coupon_valid_days | int | not null, default 30 | Validity window (days) of survey coupon from issuance |
| survey_coupon_min_purchase | int | not null, default 0 | Minimum purchase total (₽) to apply survey coupon; 0 = no minimum |
| birthday_coupon_value | int | not null, default 300 | Value (₽) of coupon issued on child birthday reminder |
| birthday_coupon_valid_days | int | not null, default 7 | Validity window (days) of birthday coupon from issuance |
| birthday_coupon_min_purchase | int | not null, default 0 | Minimum purchase total (₽) to apply birthday coupon; 0 = no minimum |

## Invariants

- Exactly one row (id = 1); application reads and writes only this row
- `registration_discount_pct` in [1, 100]
- All `*_value` fields > 0 (whole rubles)
- All `*_valid_days` fields > 0
- All `*_min_purchase` fields ≥ 0
- All coupon issuance scenarios read from this row at the moment of issuance — changed values apply to future coupons only, not retroactively

## Relations
None.

## Open questions

- ~~`birthday_coupon_max_pct` default: 30%. RESOLVED — field replaced by `birthday_coupon_min_purchase`.~~
- [ ] Seed strategy: implementor writes migration script that inserts FinancialConfig row with defaults (registration_discount_pct=10, survey_coupon_value=300, survey_coupon_valid_days=30, survey_coupon_min_purchase=0, birthday_coupon_value=300, birthday_coupon_valid_days=7, birthday_coupon_min_purchase=0). Env vars `DISCOUNT_PERCENT`, `BIRTHDAY_COUPON_VALUE`, `BIRTHDAY_COUPON_VALID_DAYS` become obsolete after migration — remove from `config.py` and `.env`.
- [x] `registration_discount_pct` range: [1, 100]. RESOLVED.
