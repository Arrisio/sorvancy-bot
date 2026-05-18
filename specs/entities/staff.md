# Entity: Staff

## Purpose
Bot operator account for store personnel — either seller or business owner — with access to staff-side bot functions.

## Fields

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | int | PK, auto | Internal ID |
| max_user_id | bigint | unique, not null | From Max messenger |
| username | varchar(255) | nullable | From Max; taken from contact card or message attributes |
| phone | varchar(20) | nullable | From contact card |
| first_name | varchar(255) | nullable | From contact card |
| last_name | varchar(255) | nullable | From contact card |
| is_owner | boolean | not null, default false | True = business owner with elevated permissions |
| customer_mode | boolean | not null, default false | When true: bot routes this user through customer branch, ignoring Staff status. For testing/debug only. |
| created_at | timestamptz | not null, default now() | Registration time |

## Invariants

- At least one Staff row with `is_owner = true` exists at all times (seeded owner)
- Multiple Staff rows may have `is_owner = true` simultaneously (substitute owners allowed)
- Staff row with `max_user_id = config.OWNER_ID` always has `is_owner = true`; flag cannot be revoked by any actor
- First Staff row seeded at DB init from `config.OWNER_ID` (env var); that row has `is_owner = true`
- `max_user_id` unique — one Staff account per Max user
- `customer_mode` toggled only by superuser via `/mode` command (scenario 14); not settable by sellers themselves
- `customer_mode = true` affects routing only; Staff permissions (`is_owner`) remain unchanged

## Relations

- (none defined yet)

## Open questions

- [x] Seed data: first owner's `max_user_id` supplied via `config.OWNER_ID` env var; `init_db.py` creates Staff row on first run.
- [x] Can `is_owner` be transferred? Yes — Owner assigns/revokes `is_owner` for any Staff via scenario 09; OWNER_ID row protected.
- [ ] What specific bot functions are restricted to `is_owner` vs available to all Staff? (Needed to define authorization model)
- [ ] Phone: stored as received from contact card, or normalized to a standard format?
