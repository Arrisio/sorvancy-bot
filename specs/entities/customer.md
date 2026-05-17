# Entity: Customer

## Purpose
Registered store buyer. Created minimally on first interaction; enriched via optional survey.

## Fields

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | int | PK, auto | Internal ID |
| max_user_id | bigint | unique, not null | From Max messenger |
| max_username | varchar(255) | nullable | From Max; not user-editable |
| first_name | varchar(255) | nullable | Collected in survey Q1 (required in flow) |
| last_name | varchar(255) | nullable | Collected in survey Q2 (optional; null if skipped) |
| phone | varchar(20) | nullable | Collected in survey contact step (optional; null if not shared) |
| birthdate | date | nullable | Collected in survey Q3 (optional; null if skipped) |
| survey_completed | boolean | not null, default false | True when «Купить для себя» taken, OR ≥1 child has birthdate NOT NULL at survey finish |
| discount_percent | int | not null, default 10 | Set from `config.DISCOUNT_PERCENT` at creation |
| registered_at | timestamptz | not null, default now() | Phase 1 completion time |
| opt_out_marketing | boolean | not null, default false | Customer opted out of personal offers; excludes from all Broadcast recipient lists |

## Invariants

- One Customer per max_user_id (unique constraint in DB)
- Created on "Зарегистрироваться" button click, before any survey data collected
- discount_percent set from env config at creation; not recalculated
- opt_out_marketing = true → Customer excluded from all Broadcast recipient lists; flag toggled by Customer from own profile
- first_name, last_name, birthdate, phone: null until survey step populates them

## Survey completion signal

Explicit boolean flag `survey_completed`. Set to true at end of scenario 02 if: «Купить для себя» path was taken, OR ≥1 child has `birthdate NOT NULL`. False otherwise. Coupon issued only on False → True transition.

## Relations

- has_many: Child (ondelete=CASCADE)

## Open questions

- [ ] Survey message says "скидка увеличена" after completion — discount_percent not actually increased in code. Intentional or bug? Decide and fix.
- [ ] `survey_completed` flag not yet in DB schema (code uses `first_name IS NOT NULL` as proxy). Migration needed.
- [ ] Re-taking survey: user can run again and overwrite first_name/last_name/birthdate, append more children. Desired behavior?
