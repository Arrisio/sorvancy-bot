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

- Exactly one Staff row with `is_owner = true` at all times
- First Staff row seeded at DB init; that row has `is_owner = true`
- `max_user_id` unique — one Staff account per Max user
- `customer_mode` toggled only by superuser via `/mode` command (scenario 14); not settable by sellers themselves
- `customer_mode = true` affects routing only; Staff permissions (`is_owner`) remain unchanged

## Relations

- (none defined yet)

## Open questions

- [ ] Seed data: how is first owner's `max_user_id` supplied? (env var, migration parameter, manual SQL?)
- [ ] Can `is_owner` be transferred to another Staff member, or is it permanently fixed at seed time?
- [ ] What specific bot functions are restricted to `is_owner` vs available to all Staff? (Needed to define authorization model)
- [ ] Phone: stored as received from contact card, or normalized to a standard format?
