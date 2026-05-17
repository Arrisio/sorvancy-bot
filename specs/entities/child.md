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
- Child record created when gender is confirmed in survey (step 6) with name + gender; birthdate updated at step 7
- name stored in session between steps 5 and 6 (not in DB) until gender is available
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
