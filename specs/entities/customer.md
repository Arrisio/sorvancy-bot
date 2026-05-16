# Entity: Customer

## Purpose
Registered store buyer. Created minimally on first interaction; enriched via optional survey.

## Fields

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | int | PK, auto | Internal ID |
| max_user_id | bigint | unique, not null | From Max messenger |
| max_username | varchar(255) | nullable | From Max; not user-editable |
| first_name | varchar(255) | nullable | Collected in survey (phase 2) |
| last_name | varchar(255) | nullable | Reserved; not yet collected |
| phone | varchar(20) | nullable | Reserved; not yet collected |
| birthdate | date | nullable | Collected in survey (phase 2) |
| discount_percent | int | not null, default 10 | Set from `config.DISCOUNT_PERCENT` at creation |
| registered_at | timestamptz | not null, default now() | Phase 1 completion time |

## Invariants

- One Customer per max_user_id (unique constraint in DB)
- Created on "Зарегистрироваться" button click, before any survey data collected
- discount_percent set from env config at creation; not recalculated
- first_name, birthdate: null until survey completed
- last_name, phone: reserved columns, not populated in current MVP

## Survey completion signal

No explicit boolean flag. Survey considered complete when `first_name IS NOT NULL`.

## Relations

- has_many: Child (ondelete=CASCADE)

## Open questions

- [ ] Survey message says "скидка увеличена" after completion — discount_percent not actually increased in code. Intentional or bug? Decide and fix.
- [ ] Phone collection: RequestContactButton present but marked `[ТЕСТ]`. When to activate?
- [ ] last_name: collect in future survey iteration?
- [ ] Re-taking survey: user can run survey again and overwrite first_name/birthdate. Desired?
