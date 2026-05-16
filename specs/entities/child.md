# Entity: Child

## Purpose
Kid belonging to Customer. Collected during survey. Drives birthday and school-year marketing campaigns.

## Fields

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | int | PK, auto | Internal ID |
| customer_id | int | FK → customers.id, not null | ondelete=CASCADE |
| name | varchar(255) | not null | Display name; no length validation in current code |
| gender | varchar(10) | not null | 'male' or 'female'; DB CHECK constraint |
| birthdate | date | not null | Used for birthday campaign targeting |
| created_at | timestamptz | not null, default now() | |

## Invariants

- gender must be 'male' or 'female' (enforced by DB CHECK constraint `gender_check`)
- At least 1 Child per Customer after survey completion (enforced by survey flow logic)
- Children created atomically with survey data update in single transaction
- Deleted cascading when Customer removed

## Relations

- belongs_to: Customer

## Future use (newsletters — not yet implemented)

- birthdate → birthday campaign (send day before child's birthday)
- birthdate → school year inference for back-to-school campaigns (August)
- gender → gender-targeted product promotions

## Open questions

- [ ] No validation that child birthdate is in the past or within reasonable range (0–18 years). Add?
- [ ] No max child count per customer. Limit needed?
- [ ] Duplicate children names not prevented. OK?
