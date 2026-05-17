# Entity: Child

## Purpose
Kid belonging to Customer. Collected during survey. Drives birthday and school-year marketing campaigns.

## Fields

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | int | PK, auto | Internal ID |
| customer_id | int | FK → customers.id, not null | ondelete=CASCADE |
| name | varchar(255) | not null | Display name |
| gender | varchar(10) | not null | 'male' or 'female'; DB CHECK constraint; required, no skip |
| birthdate | date | nullable | Optional; null if skipped; used for birthday campaign targeting |
| created_at | timestamptz | not null, default now() | |

## Invariants

- gender must be 'male' or 'female' (enforced by DB CHECK constraint `gender_check`)
- Child record created only at survey step 10 (single DB transaction) — not at step 6 or 7; all child data lives in `draft.children` MemoryContext until then
- name, gender, birthdate all stored in draft between steps 5–7; no partial DB writes mid-survey
- 0 children per Customer is valid when «Купить для себя» path taken
- Deleted cascading when Customer removed

## Relations

- belongs_to: Customer

## Future use (newsletters — not yet implemented)

- birthdate → birthday campaign (send day before child's birthday)
- birthdate → school year inference for back-to-school campaigns (August)
- gender → gender-targeted product promotions

## Open questions

- [ ] Duplicate children names not prevented. OK?
